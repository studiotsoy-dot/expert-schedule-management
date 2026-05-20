"""
API для управления слотами экспертов: создание, редактирование, удаление,
получение свободных слотов и всех слотов для администратора.
"""
import json
import os
import uuid
import psycopg2

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}


def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def resp(status, body):
    return {
        'statusCode': status,
        'headers': {**CORS_HEADERS, 'Content-Type': 'application/json'},
        'body': json.dumps(body, ensure_ascii=False),
    }


def row_to_slot(row):
    return {
        'id': row[0], 'expert_id': row[1], 'date': row[2],
        'start_time': row[3], 'end_time': row[4], 'status': row[5],
    }


def handler(event: dict, context) -> dict:
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    params = event.get('queryStringParameters') or {}

    # Извлекаем slot_id из пути (последний сегмент, если не служебный)
    path_parts = [p for p in path.strip('/').split('/') if p]
    path_slot_id = None
    if path_parts:
        last = path_parts[-1]
        if last not in ('slots', 'api', 'all', 'free', 'admin'):
            path_slot_id = last

    # action из query или из пути
    action = params.get('action', '')
    if not action:
        if 'admin' in path_parts or 'all' in path_parts:
            action = 'admin'
        elif 'free' in path_parts:
            action = 'free'

    conn = get_conn()
    cur = conn.cursor()

    # GET ?action=admin — все слоты для администратора
    if method == 'GET' and action == 'admin':
        cur.execute("SELECT id, expert_id, date, start_time, end_time, status FROM slots ORDER BY date, start_time")
        slots = cur.fetchall()
        result = []
        for s in slots:
            slot_dict = row_to_slot(s)
            cur.execute("SELECT name, email, portfolio_url FROM users WHERE id = %s", (s[1],))
            expert = cur.fetchone()
            if not expert:
                continue
            slot_dict['expert_name'] = expert[0]
            slot_dict['expert_email'] = expert[1]
            slot_dict['expert_portfolio'] = expert[2] or ''
            cur.execute(
                "SELECT client_name, client_phone, client_email, status, call_status, call_comment, zoom_link, manager_id FROM bookings WHERE slot_id = %s LIMIT 1",
                (s[0],)
            )
            booking = cur.fetchone()
            if booking:
                cur.execute("SELECT name FROM users WHERE id = %s", (booking[7],))
                mgr = cur.fetchone()
                slot_dict['booking'] = {
                    'client_name': booking[0],
                    'client_phone': booking[1] or '',
                    'client_email': booking[2] or '',
                    'status': booking[3],
                    'call_status': booking[4] or 'pending',
                    'call_comment': booking[5] or '',
                    'zoom_link': booking[6] or '',
                    'manager_name': mgr[0] if mgr else '',
                }
            result.append(slot_dict)
        conn.close()
        return resp(200, result)

    # GET ?action=free — свободные слоты для менеджера
    if method == 'GET' and action == 'free':
        cur.execute("SELECT id, expert_id, date, start_time, end_time, status FROM slots WHERE status = 'free' ORDER BY date, start_time")
        slots = cur.fetchall()
        result = []
        for s in slots:
            cur.execute("SELECT name, portfolio_url FROM users WHERE id = %s AND is_active = 1", (s[1],))
            expert = cur.fetchone()
            if not expert:
                continue
            slot_dict = row_to_slot(s)
            slot_dict['expert_name'] = expert[0]
            slot_dict['expert_portfolio'] = expert[1] or ''
            result.append(slot_dict)
        conn.close()
        return resp(200, result)

    # GET ?expert_id=... — слоты конкретного эксперта
    if method == 'GET':
        expert_id = params.get('expert_id')
        if expert_id:
            cur.execute("SELECT id, expert_id, date, start_time, end_time, status FROM slots WHERE expert_id = %s ORDER BY date, start_time", (expert_id,))
        else:
            cur.execute("SELECT id, expert_id, date, start_time, end_time, status FROM slots ORDER BY date, start_time")
        rows = cur.fetchall()
        conn.close()
        return resp(200, [row_to_slot(r) for r in rows])

    # POST / — создать слот
    if method == 'POST':
        body = json.loads(event.get('body') or '{}')
        slot_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO slots (id, expert_id, date, start_time, end_time, status) VALUES (%s,%s,%s,%s,%s,'free') RETURNING id, expert_id, date, start_time, end_time, status",
            (slot_id, body['expert_id'], body['date'], body['start_time'], body['end_time'])
        )
        row = cur.fetchone()
        conn.commit()
        conn.close()
        return resp(200, row_to_slot(row))

    # PUT /{slot_id} — обновить слот
    if method == 'PUT' and path_slot_id:
        slot_id = path_slot_id
        body = json.loads(event.get('body') or '{}')
        cur.execute("SELECT expert_id, status FROM slots WHERE id = %s", (slot_id,))
        existing = cur.fetchone()
        if not existing:
            conn.close()
            return resp(404, {'detail': 'Слот не найден'})
        if existing[0] != body.get('expert_id'):
            conn.close()
            return resp(403, {'detail': 'Нет прав'})
        if existing[1] != 'free':
            conn.close()
            return resp(400, {'detail': 'Нельзя редактировать занятый слот'})
        cur.execute(
            "UPDATE slots SET date=%s, start_time=%s, end_time=%s WHERE id=%s RETURNING id, expert_id, date, start_time, end_time, status",
            (body['date'], body['start_time'], body['end_time'], slot_id)
        )
        row = cur.fetchone()
        conn.commit()
        conn.close()
        return resp(200, row_to_slot(row))

    # DELETE /{slot_id}?expert_id=...
    if method == 'DELETE' and path_slot_id:
        slot_id = path_slot_id
        expert_id = params.get('expert_id', '')
        cur.execute("SELECT expert_id, status FROM slots WHERE id = %s", (slot_id,))
        existing = cur.fetchone()
        if not existing:
            conn.close()
            return resp(404, {'detail': 'Слот не найден'})
        if existing[0] != expert_id:
            conn.close()
            return resp(403, {'detail': 'Нет прав'})
        if existing[1] != 'free':
            conn.close()
            return resp(400, {'detail': 'Нельзя удалить занятый слот'})
        cur.execute("DELETE FROM slots WHERE id = %s", (slot_id,))
        conn.commit()
        conn.close()
        return resp(200, {'status': 'deleted'})

    conn.close()
    return resp(405, {'detail': 'Method not allowed'})
