"""
API для бронирований: создание записи, смена статуса, перенос, email-уведомления. v3
"""
import json
import os
import uuid
from datetime import datetime
import psycopg2

from email_utils import send_booking_created, send_status_changed, send_rescheduled, send_expert_new_booking, send_expert_rescheduled, send_manager_status_changed

CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}

CALL_STATUSES = ['pending', 'confirmed', 'success', 'cancelled_by_client', 'cancelled_by_expert', 'failed', 'reschedule_request']

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
    return {'statusCode': status, 'headers': {**CORS, 'Content-Type': 'application/json'}, 'body': json.dumps(body, ensure_ascii=False)}


def generate_zoom_link():
    return f"https://zoom.us/j/{str(uuid.uuid4())[:8]}"


def fetch_bookings_enriched(cur, where_sql, params=()):
    cur.execute(f"""
        SELECT b.id, b.slot_id, b.manager_id,
               b.client_name, b.client_phone, b.client_email,
               b.status, b.call_status, b.call_comment, b.zoom_link, b.created_at,
               s.date, s.start_time, s.end_time, s.expert_id,
               e.name, e.portfolio_url, m.name, b.client_comment, b.client_telegram
        FROM bookings b
        JOIN slots s ON s.id = b.slot_id
        JOIN users e ON e.id = s.expert_id
        LEFT JOIN users m ON m.id = b.manager_id
        {where_sql}
    """, params)
    return [{'id': r[0], 'client_name': r[3], 'client_phone': r[4] or '', 'client_email': r[5] or '',
             'status': r[6], 'call_status': r[7] or 'pending', 'call_comment': r[8] or '',
             'zoom_link': r[9] or '', 'created_at': r[10] or '', 'date': r[11],
             'start_time': r[12], 'end_time': r[13], 'expert_id': r[14],
             'expert_name': r[15] or '', 'expert_portfolio': r[16] or '',
             'manager_name': r[17] or '', 'client_comment': r[18] or '', 'client_telegram': r[19] or ''}
            for r in cur.fetchall()]


def _email(fn, **kwargs):
    try:
        fn(**kwargs)
    except Exception as e:
        print(f"Email error {fn.__name__}: {e}")


def handler(event: dict, context) -> dict:
    """Управление бронированиями: создание, статусы, перенос, email-уведомления."""
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS, 'body': ''}

    method = event.get('httpMethod', 'GET')
    params = event.get('queryStringParameters') or {}
    action = params.get('action', '')

    conn = get_conn()
    cur = conn.cursor()
    try:
        if method == 'GET' and action == 'statuses':
            return resp(200, {'statuses': CALL_STATUSES, 'names': STATUS_NAMES})

        if method == 'GET':
            role = params.get('role', '')
            user_id = params.get('user_id', '')
            if not role:
                return resp(200, [])
            if role == 'admin':
                result = fetch_bookings_enriched(cur, '')
            elif role == 'manager':
                result = fetch_bookings_enriched(cur, 'WHERE b.manager_id = %s', (user_id,))
            elif role == 'expert':
                result = fetch_bookings_enriched(cur, 'WHERE s.expert_id = %s', (user_id,))
            else:
                return resp(400, {'detail': 'Укажите role'})
            return resp(200, result)

        if method == 'POST' and action in ('', 'book'):
            body = json.loads(event.get('body') or '{}')
            slot_id = body.get('slot_id')

            # Получаем слот + эксперта одним запросом
            cur.execute("""
                SELECT s.status, s.date, s.start_time, s.end_time,
                       e.id, e.name, e.email
                FROM slots s
                JOIN users e ON e.id = s.expert_id
                WHERE s.id = %s
            """, (slot_id,))
            slot_row = cur.fetchone()
            if not slot_row or slot_row[0] != 'free':
                return resp(400, {'detail': 'Слот уже занят'})
            _, date, start_time, end_time, expert_id, expert_name, expert_email = slot_row

            cur.execute("SELECT name FROM users WHERE id = %s", (body['manager_id'],))
            manager_row = cur.fetchone()
            manager_name = manager_row[0] if manager_row else ''

            booking_id = str(uuid.uuid4())
            zoom_link = generate_zoom_link()
            now = datetime.now().isoformat()
            client_name = body['client_name']
            client_email = body.get('client_email', '')
            client_comment = body.get('client_comment', '')
            client_telegram = body.get('client_telegram', '')

            cur.execute(
                "INSERT INTO bookings (id, slot_id, manager_id, client_name, client_phone, client_email, status, call_status, call_comment, zoom_link, created_at, client_comment, client_telegram) VALUES (%s,%s,%s,%s,%s,%s,'pending','pending','',%s,%s,%s,%s)",
                (booking_id, slot_id, body['manager_id'], client_name, body.get('client_phone', ''), client_email, zoom_link, now, client_comment, client_telegram)
            )
            cur.execute("UPDATE slots SET status = 'booked' WHERE id = %s", (slot_id,))
            conn.commit()

            _email(send_expert_new_booking, to_email=expert_email, expert_name=expert_name,
                   client_name=client_name, client_phone=body.get('client_phone', ''),
                   client_email=client_email, date=date, start_time=start_time, end_time=end_time,
                   manager_name=manager_name, zoom_link=zoom_link, client_comment=client_comment)

            return resp(200, {'id': booking_id, 'zoom_link': zoom_link, 'status': 'pending'})

        if method == 'POST' and action == 'confirm':
            body = json.loads(event.get('body') or '{}')
            booking_id = body.get('booking_id')
            expert_id = body.get('expert_id')

            cur.execute("""
                SELECT b.slot_id, b.client_email, b.client_name, b.zoom_link,
                       s.expert_id, s.date, s.start_time, e.name
                FROM bookings b
                JOIN slots s ON s.id = b.slot_id
                JOIN users e ON e.id = s.expert_id
                WHERE b.id = %s
            """, (booking_id,))
            row = cur.fetchone()
            if not row:
                return resp(404, {'detail': 'Бронирование не найдено'})
            slot_id, client_email, client_name, zoom_link, slot_expert_id, date, start_time, expert_name = row
            if slot_expert_id != expert_id:
                return resp(403, {'detail': 'Нет прав'})

            cur.execute("UPDATE bookings SET status='confirmed', call_status='confirmed' WHERE id = %s", (booking_id,))
            conn.commit()

            _email(send_status_changed, to_email=client_email, client_name=client_name,
                   expert_name=expert_name, date=date, start_time=start_time,
                   new_status='confirmed', comment='', zoom_link=zoom_link)

            return resp(200, {'status': 'confirmed'})

        if method == 'POST' and action == 'update-status':
            body = json.loads(event.get('body') or '{}')
            booking_id = body.get('booking_id')
            expert_id = body.get('expert_id')
            new_status = body.get('status')
            comment = body.get('comment', '')
            if new_status not in CALL_STATUSES:
                return resp(400, {'detail': 'Неверный статус'})

            cur.execute("""
                SELECT b.slot_id, b.client_email, b.client_name, b.zoom_link, b.manager_id,
                       s.expert_id, s.date, s.start_time, e.name
                FROM bookings b
                JOIN slots s ON s.id = b.slot_id
                JOIN users e ON e.id = s.expert_id
                WHERE b.id = %s
            """, (booking_id,))
            row = cur.fetchone()
            if not row:
                return resp(404, {'detail': 'Бронирование не найдено'})
            slot_id, client_email, client_name, zoom_link, manager_id, slot_expert_id, date, start_time, expert_name = row
            if slot_expert_id != expert_id:
                return resp(403, {'detail': 'Нет прав'})

            cur.execute("UPDATE bookings SET call_status=%s, call_comment=%s WHERE id=%s", (new_status, comment, booking_id))
            if new_status == 'confirmed':
                cur.execute("UPDATE slots SET status='confirmed' WHERE id=%s", (slot_id,))
            conn.commit()

            manager_email, manager_name = None, None
            if manager_id:
                cur.execute("SELECT email, name FROM users WHERE id = %s", (manager_id,))
                m = cur.fetchone()
                if m:
                    manager_email, manager_name = m[0], m[1]

            CLIENT_NOTIFY = ('confirmed', 'cancelled_by_client', 'cancelled_by_expert')
            if new_status in CLIENT_NOTIFY:
                _email(send_status_changed, to_email=client_email, client_name=client_name,
                       expert_name=expert_name, date=date, start_time=start_time,
                       new_status=new_status, comment=comment, zoom_link=zoom_link)
            if manager_email:
                _email(send_manager_status_changed, to_email=manager_email, manager_name=manager_name or '',
                       client_name=client_name, expert_name=expert_name, date=str(date),
                       start_time=str(start_time), new_status=new_status, comment=comment)

            return resp(200, {'status': new_status, 'comment': comment})

        if method == 'POST' and action == 'reschedule':
            body = json.loads(event.get('body') or '{}')
            booking_id = body.get('booking_id')

            cur.execute("""
                SELECT b.slot_id, b.client_email, b.client_name, b.zoom_link,
                       s.expert_id, s.date, s.start_time, e.name, e.email
                FROM bookings b
                JOIN slots s ON s.id = b.slot_id
                JOIN users e ON e.id = s.expert_id
                WHERE b.id = %s
            """, (booking_id,))
            row = cur.fetchone()
            if not row:
                return resp(404, {'detail': 'Бронирование не найдено'})
            old_slot_id, client_email, client_name, zoom_link, expert_id, old_date, old_start, expert_name, expert_email = row

            cur.execute("SELECT name FROM users WHERE id = %s", (body.get('manager_id'),))
            manager_row = cur.fetchone()
            manager_name = manager_row[0] if manager_row else ''

            new_slot_id = str(uuid.uuid4())
            new_date, new_start, new_end = body['new_date'], body['new_start_time'], body['new_end_time']

            cur.execute("INSERT INTO slots (id, expert_id, date, start_time, end_time, status) VALUES (%s,%s,%s,%s,%s,'booked')",
                        (new_slot_id, expert_id, new_date, new_start, new_end))
            cur.execute("UPDATE bookings SET slot_id=%s, call_status='pending', status='pending' WHERE id=%s", (new_slot_id, booking_id))
            cur.execute("UPDATE slots SET status='free' WHERE id=%s", (old_slot_id,))
            conn.commit()

            _email(send_rescheduled, to_email=client_email, client_name=client_name,
                   expert_name=expert_name, new_date=new_date, new_start_time=new_start, zoom_link=zoom_link)
            _email(send_expert_rescheduled, to_email=expert_email, expert_name=expert_name,
                   client_name=client_name, old_date=old_date, old_start=old_start,
                   new_date=new_date, new_start_time=new_start, new_end_time=new_end,
                   manager_name=manager_name, zoom_link=zoom_link)

            return resp(200, {'new_slot_id': new_slot_id, 'date': new_date, 'start_time': new_start})

        if method == 'PUT':
            body = json.loads(event.get('body') or '{}')
            booking_id = body.get('booking_id')
            if not booking_id:
                return resp(400, {'detail': 'booking_id обязателен'})
            cur.execute("SELECT id FROM bookings WHERE id = %s", (booking_id,))
            if not cur.fetchone():
                return resp(404, {'detail': 'Бронирование не найдено'})
            updates, values = [], []
            for field in ('client_name', 'client_phone', 'client_email', 'client_telegram'):
                if field in body:
                    updates.append(f"{field} = %s"); values.append(body[field])
            if not updates:
                return resp(400, {'detail': 'Нет данных для обновления'})
            values.append(booking_id)
            cur.execute(f"UPDATE bookings SET {', '.join(updates)} WHERE id = %s", values)
            conn.commit()
            return resp(200, {'status': 'updated'})

        if method == 'DELETE':
            booking_id = params.get('booking_id')
            if not booking_id:
                return resp(400, {'detail': 'booking_id обязателен'})
            cur.execute("SELECT slot_id FROM bookings WHERE id = %s", (booking_id,))
            row = cur.fetchone()
            if not row:
                return resp(404, {'detail': 'Бронирование не найдено'})
            cur.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
            cur.execute("UPDATE slots SET status = 'free' WHERE id = %s", (row[0],))
            conn.commit()
            return resp(200, {'status': 'deleted'})

        return resp(405, {'detail': 'Method not allowed'})
    finally:
        conn.close()
