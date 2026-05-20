"""
API для бронирований: создание записи клиента, смена статуса созвона,
переназначение времени, получение списков по роли.
Отправляет email-уведомления клиенту при каждом ключевом событии.
"""
import json
import os
import uuid
from datetime import datetime
import psycopg2

from email_utils import send_booking_created, send_status_changed, send_rescheduled, send_expert_new_booking, send_expert_rescheduled

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}

CALL_STATUSES = [
    'pending', 'confirmed', 'success', 'cancelled_by_client',
    'cancelled_by_expert', 'failed', 'reschedule_request'
]

STATUS_NAMES = {
    'pending': '⏳ Ожидает подтверждения',
    'confirmed': '✅ Подтверждён',
    'success': '🎉 Созвон успешный',
    'cancelled_by_client': '❌ Отменён клиентом',
    'cancelled_by_expert': '⚠️ Отменён экспертом',
    'failed': '💔 Созвон не успешный',
    'reschedule_request': '🔄 Клиент просил перенести',
}


def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def resp(status, body):
    return {
        'statusCode': status,
        'headers': {**CORS_HEADERS, 'Content-Type': 'application/json'},
        'body': json.dumps(body, ensure_ascii=False),
    }


def generate_zoom_link():
    return f"https://zoom.us/j/{str(uuid.uuid4())[:8]}"


def enrich_bookings(cur, bookings_rows):
    """Обогащает записи данными слота, эксперта и менеджера."""
    result = []
    for b in bookings_rows:
        booking_id, slot_id, manager_id, client_name, client_phone, client_email, status, call_status, call_comment, zoom_link, created_at = b
        cur.execute("SELECT date, start_time, end_time, expert_id FROM slots WHERE id = %s", (slot_id,))
        slot = cur.fetchone()
        if not slot:
            continue
        date, start_time, end_time, expert_id = slot
        cur.execute("SELECT name, portfolio_url FROM users WHERE id = %s", (expert_id,))
        expert = cur.fetchone()
        cur.execute("SELECT name FROM users WHERE id = %s", (manager_id,))
        manager = cur.fetchone()
        result.append({
            'id': booking_id,
            'client_name': client_name,
            'client_phone': client_phone or '',
            'client_email': client_email or '',
            'status': status,
            'call_status': call_status or 'pending',
            'call_comment': call_comment or '',
            'zoom_link': zoom_link or '',
            'created_at': created_at or '',
            'date': date,
            'start_time': start_time,
            'end_time': end_time,
            'expert_id': expert_id,
            'expert_name': expert[0] if expert else '',
            'expert_portfolio': (expert[1] or '') if expert else '',
            'manager_name': manager[0] if manager else '',
        })
    return result


def handler(event: dict, context) -> dict:
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    params = event.get('queryStringParameters') or {}

    conn = get_conn()
    cur = conn.cursor()

    # GET /api/bookings/statuses
    if method == 'GET' and path.endswith('/statuses'):
        conn.close()
        return resp(200, {'statuses': CALL_STATUSES, 'names': STATUS_NAMES})

    # GET /api/bookings?role=...&user_id=...
    if method == 'GET':
        if not params.get('role'):
            conn.close()
            return resp(200, [])
        role = params.get('role', '')
        user_id = params.get('user_id', '')
        cols = "id, slot_id, manager_id, client_name, client_phone, client_email, status, call_status, call_comment, zoom_link, created_at"
        if role == 'admin':
            cur.execute(f"SELECT {cols} FROM bookings")
        elif role == 'manager':
            cur.execute(f"SELECT {cols} FROM bookings WHERE manager_id = %s", (user_id,))
        elif role == 'expert':
            cur.execute("SELECT id FROM slots WHERE expert_id = %s", (user_id,))
            slot_ids = [r[0] for r in cur.fetchall()]
            if not slot_ids:
                conn.close()
                return resp(200, [])
            placeholders = ','.join(['%s'] * len(slot_ids))
            cur.execute(f"SELECT {cols} FROM bookings WHERE slot_id IN ({placeholders})", slot_ids)
        else:
            conn.close()
            return resp(400, {'detail': 'Укажите role'})
        rows = cur.fetchall()
        result = enrich_bookings(cur, rows)
        conn.close()
        return resp(200, result)

    # POST /api/bookings — создание записи
    if method == 'POST' and (path.rstrip('/').endswith('/bookings') or path in ('/', '')):
        body = json.loads(event.get('body') or '{}')
        slot_id = body.get('slot_id')
        cur.execute("SELECT status FROM slots WHERE id = %s", (slot_id,))
        slot = cur.fetchone()
        if not slot or slot[0] != 'free':
            conn.close()
            return resp(400, {'detail': 'Слот уже занят'})

        # Получаем данные слота и эксперта для письма
        cur.execute("SELECT date, start_time, end_time, expert_id FROM slots WHERE id = %s", (slot_id,))
        slot_data = cur.fetchone()
        date, start_time, end_time, expert_id = slot_data
        cur.execute("SELECT name, email FROM users WHERE id = %s", (expert_id,))
        expert_row = cur.fetchone()
        expert_name = expert_row[0] if expert_row else ''
        expert_email = expert_row[1] if expert_row else ''
        cur.execute("SELECT name FROM users WHERE id = %s", (body['manager_id'],))
        manager_row = cur.fetchone()
        manager_name = manager_row[0] if manager_row else ''

        booking_id = str(uuid.uuid4())
        zoom_link = generate_zoom_link()
        now = datetime.now().isoformat()
        client_email = body.get('client_email', '')
        client_name = body['client_name']

        cur.execute(
            "INSERT INTO bookings (id, slot_id, manager_id, client_name, client_phone, client_email, status, call_status, call_comment, zoom_link, created_at) VALUES (%s,%s,%s,%s,%s,%s,'pending','pending','',%s,%s)",
            (booking_id, slot_id, body['manager_id'], client_name,
             body.get('client_phone', ''), client_email, zoom_link, now)
        )
        cur.execute("UPDATE slots SET status = 'booked' WHERE id = %s", (slot_id,))
        conn.commit()
        conn.close()

        # Отправляем emails (после коммита, ошибка письма не ломает ответ)
        try:
            send_booking_created(
                to_email=client_email,
                client_name=client_name,
                expert_name=expert_name,
                date=date,
                start_time=start_time,
                end_time=end_time,
                zoom_link=zoom_link,
            )
        except Exception as e:
            print(f"Email error (client booking created): {e}")

        try:
            send_expert_new_booking(
                to_email=expert_email,
                expert_name=expert_name,
                client_name=client_name,
                client_phone=body.get('client_phone', ''),
                client_email=client_email,
                date=date,
                start_time=start_time,
                end_time=end_time,
                manager_name=manager_name,
                zoom_link=zoom_link,
            )
        except Exception as e:
            print(f"Email error (expert new booking): {e}")

        return resp(200, {'id': booking_id, 'zoom_link': zoom_link, 'status': 'pending'})

    # POST /api/bookings/confirm
    if method == 'POST' and path.endswith('/confirm'):
        body = json.loads(event.get('body') or '{}')
        booking_id = body.get('booking_id')
        expert_id = body.get('expert_id')
        cur.execute("SELECT slot_id FROM bookings WHERE id = %s", (booking_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return resp(404, {'detail': 'Бронирование не найдено'})
        slot_id = row[0]
        cur.execute("SELECT expert_id FROM slots WHERE id = %s", (slot_id,))
        slot = cur.fetchone()
        if not slot or slot[0] != expert_id:
            conn.close()
            return resp(403, {'detail': 'Нет прав'})
        cur.execute("UPDATE bookings SET status='confirmed', call_status='confirmed' WHERE id = %s", (booking_id,))
        conn.commit()

        # Данные для письма
        cur.execute("SELECT client_email, client_name, zoom_link FROM bookings WHERE id = %s", (booking_id,))
        b_row = cur.fetchone()
        cur.execute("SELECT date, start_time FROM slots WHERE id = %s", (slot_id,))
        s_row = cur.fetchone()
        cur.execute("SELECT name FROM users WHERE id = %s", (expert_id,))
        e_row = cur.fetchone()
        conn.close()

        try:
            send_status_changed(
                to_email=b_row[0],
                client_name=b_row[1],
                expert_name=e_row[0] if e_row else '',
                date=s_row[0],
                start_time=s_row[1],
                new_status='confirmed',
                comment='',
                zoom_link=b_row[2],
            )
        except Exception as e:
            print(f"Email error (confirm): {e}")

        return resp(200, {'status': 'confirmed'})

    # POST /api/bookings/update-status
    if method == 'POST' and path.endswith('/update-status'):
        body = json.loads(event.get('body') or '{}')
        booking_id = body.get('booking_id')
        expert_id = body.get('expert_id')
        new_status = body.get('status')
        comment = body.get('comment', '')
        if new_status not in CALL_STATUSES:
            conn.close()
            return resp(400, {'detail': 'Неверный статус'})
        cur.execute("SELECT slot_id FROM bookings WHERE id = %s", (booking_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return resp(404, {'detail': 'Бронирование не найдено'})
        slot_id = row[0]
        cur.execute("SELECT expert_id FROM slots WHERE id = %s", (slot_id,))
        slot = cur.fetchone()
        if not slot or slot[0] != expert_id:
            conn.close()
            return resp(403, {'detail': 'Нет прав'})
        cur.execute("UPDATE bookings SET call_status=%s, call_comment=%s WHERE id=%s", (new_status, comment, booking_id))
        if new_status == 'confirmed':
            cur.execute("UPDATE slots SET status='confirmed' WHERE id=%s", (slot_id,))
        conn.commit()

        # Данные для письма
        cur.execute("SELECT client_email, client_name, zoom_link FROM bookings WHERE id = %s", (booking_id,))
        b_row = cur.fetchone()
        cur.execute("SELECT date, start_time FROM slots WHERE id = %s", (slot_id,))
        s_row = cur.fetchone()
        cur.execute("SELECT name FROM users WHERE id = %s", (expert_id,))
        e_row = cur.fetchone()
        conn.close()

        try:
            send_status_changed(
                to_email=b_row[0],
                client_name=b_row[1],
                expert_name=e_row[0] if e_row else '',
                date=s_row[0],
                start_time=s_row[1],
                new_status=new_status,
                comment=comment,
                zoom_link=b_row[2],
            )
        except Exception as e:
            print(f"Email error (update-status): {e}")

        return resp(200, {'status': new_status, 'comment': comment})

    # POST /api/bookings/reschedule
    if method == 'POST' and path.endswith('/reschedule'):
        body = json.loads(event.get('body') or '{}')
        booking_id = body.get('booking_id')
        cur.execute("SELECT slot_id, client_email, client_name, zoom_link FROM bookings WHERE id = %s", (booking_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return resp(404, {'detail': 'Бронирование не найдено'})
        old_slot_id, client_email, client_name, zoom_link = row
        cur.execute("SELECT expert_id, date, start_time FROM slots WHERE id = %s", (old_slot_id,))
        old_slot = cur.fetchone()
        expert_id, old_date, old_start = old_slot[0], old_slot[1], old_slot[2]
        cur.execute("SELECT name, email FROM users WHERE id = %s", (expert_id,))
        expert_row = cur.fetchone()
        expert_name = expert_row[0] if expert_row else ''
        expert_email = expert_row[1] if expert_row else ''
        cur.execute("SELECT name FROM users WHERE id = %s", (body.get('manager_id'),))
        manager_row = cur.fetchone()
        manager_name = manager_row[0] if manager_row else ''

        new_slot_id = str(uuid.uuid4())
        new_date = body['new_date']
        new_start = body['new_start_time']
        new_end = body['new_end_time']

        cur.execute(
            "INSERT INTO slots (id, expert_id, date, start_time, end_time, status) VALUES (%s,%s,%s,%s,%s,'booked')",
            (new_slot_id, expert_id, new_date, new_start, new_end)
        )
        cur.execute("UPDATE bookings SET slot_id=%s, call_status='pending', status='pending' WHERE id=%s", (new_slot_id, booking_id))
        cur.execute("UPDATE slots SET status='free' WHERE id=%s", (old_slot_id,))
        conn.commit()
        conn.close()

        try:
            send_rescheduled(
                to_email=client_email,
                client_name=client_name,
                expert_name=expert_name,
                new_date=new_date,
                new_start_time=new_start,
                zoom_link=zoom_link,
            )
        except Exception as e:
            print(f"Email error (client reschedule): {e}")

        try:
            send_expert_rescheduled(
                to_email=expert_email,
                expert_name=expert_name,
                client_name=client_name,
                old_date=old_date,
                old_start=old_start,
                new_date=new_date,
                new_start_time=new_start,
                new_end_time=new_end,
                manager_name=manager_name,
                zoom_link=zoom_link,
            )
        except Exception as e:
            print(f"Email error (expert reschedule): {e}")

        return resp(200, {'new_slot_id': new_slot_id, 'date': new_date, 'start_time': new_start})

    conn.close()
    return resp(405, {'detail': 'Method not allowed'})