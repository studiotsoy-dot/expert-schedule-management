"""
API для управления слотами экспертов. v5
"""
import json
import os
import uuid
import psycopg2

CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}


def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def resp(status, body):
    return {'statusCode': status, 'headers': {**CORS, 'Content-Type': 'application/json'}, 'body': json.dumps(body, ensure_ascii=False)}


def row_to_slot(row):
    return {'id': row[0], 'expert_id': row[1], 'date': row[2], 'start_time': row[3], 'end_time': row[4], 'status': row[5]}


def handler(event: dict, context) -> dict:
    """Управление слотами: CRUD для экспертов, просмотр для менеджеров и администратора."""
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS, 'body': ''}

    method = event.get('httpMethod', 'GET')
    params = event.get('queryStringParameters') or {}
    action = params.get('action', '')

    conn = get_conn()
    cur = conn.cursor()
    try:
        if method == 'GET' and action == 'admin':
            cur.execute("""
                SELECT s.id, s.expert_id, s.date, s.start_time, s.end_time, s.status,
                       e.name, e.email, e.portfolio_url,
                       b.client_name, b.client_phone, b.client_email,
                       b.status, b.call_status, b.call_comment, b.zoom_link,
                       m.name, b.client_telegram, b.client_comment
                FROM slots s
                JOIN users e ON e.id = s.expert_id
                LEFT JOIN bookings b ON b.slot_id = s.id
                LEFT JOIN users m ON m.id = b.manager_id
                ORDER BY s.date, s.start_time
            """)
            result = []
            for r in cur.fetchall():
                slot = {'id': r[0], 'expert_id': r[1], 'date': r[2], 'start_time': r[3], 'end_time': r[4], 'status': r[5],
                        'expert_name': r[6], 'expert_email': r[7], 'expert_portfolio': r[8] or ''}
                if r[9]:
                    slot['booking'] = {'client_name': r[9], 'client_phone': r[10] or '', 'client_email': r[11] or '',
                                       'status': r[12], 'call_status': r[13] or 'pending', 'call_comment': r[14] or '',
                                       'zoom_link': r[15] or '', 'manager_name': r[16] or '',
                                       'client_telegram': r[17] or '', 'client_comment': r[18] or ''}
                result.append(slot)
            return resp(200, result)

        if method == 'GET' and action == 'free':
            cur.execute("""
                SELECT s.id, s.expert_id, s.date, s.start_time, s.end_time, s.status, e.name, e.portfolio_url
                FROM slots s
                JOIN users e ON e.id = s.expert_id AND e.is_active = 1
                WHERE s.status = 'free'
                ORDER BY s.date, s.start_time
            """)
            return resp(200, [{'id': r[0], 'expert_id': r[1], 'date': r[2], 'start_time': r[3], 'end_time': r[4],
                               'status': r[5], 'expert_name': r[6], 'expert_portfolio': r[7] or ''} for r in cur.fetchall()])

        if method == 'GET':
            expert_id = params.get('expert_id')
            if expert_id:
                cur.execute("SELECT id, expert_id, date, start_time, end_time, status FROM slots WHERE expert_id = %s ORDER BY date, start_time", (expert_id,))
            else:
                cur.execute("SELECT id, expert_id, date, start_time, end_time, status FROM slots ORDER BY date, start_time")
            return resp(200, [row_to_slot(r) for r in cur.fetchall()])

        if method == 'POST':
            body = json.loads(event.get('body') or '{}')
            slot_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO slots (id, expert_id, date, start_time, end_time, status) VALUES (%s,%s,%s,%s,%s,'free') RETURNING id, expert_id, date, start_time, end_time, status",
                (slot_id, body['expert_id'], body['date'], body['start_time'], body['end_time'])
            )
            row = cur.fetchone()
            conn.commit()
            return resp(200, row_to_slot(row))

        if method == 'PUT':
            body = json.loads(event.get('body') or '{}')
            slot_id = params.get('slot_id') or body.get('slot_id')
            expert_id = body.get('expert_id')
            if not slot_id:
                return resp(400, {'detail': 'slot_id обязателен'})
            cur.execute("SELECT expert_id, status FROM slots WHERE id = %s", (slot_id,))
            existing = cur.fetchone()
            if not existing:
                return resp(404, {'detail': 'Слот не найден'})
            if existing[0] != expert_id:
                return resp(403, {'detail': 'Нет прав'})
            if existing[1] != 'free':
                return resp(400, {'detail': 'Нельзя редактировать занятый слот'})
            cur.execute(
                "UPDATE slots SET date=%s, start_time=%s, end_time=%s WHERE id=%s RETURNING id, expert_id, date, start_time, end_time, status",
                (body['date'], body['start_time'], body['end_time'], slot_id)
            )
            row = cur.fetchone()
            conn.commit()
            return resp(200, row_to_slot(row))

        if method == 'DELETE':
            slot_id = params.get('slot_id')
            expert_id = params.get('expert_id', '')
            is_admin = params.get('admin') == 'true'
            if not slot_id:
                return resp(400, {'detail': 'slot_id обязателен'})
            cur.execute("SELECT expert_id, status FROM slots WHERE id = %s", (slot_id,))
            existing = cur.fetchone()
            if not existing:
                return resp(404, {'detail': 'Слот не найден'})
            if not is_admin:
                if existing[0] != expert_id:
                    return resp(403, {'detail': 'Нет прав'})
                if existing[1] != 'free':
                    return resp(400, {'detail': 'Нельзя удалить занятый слот'})
            cur.execute("DELETE FROM bookings WHERE slot_id = %s", (slot_id,))
            cur.execute("DELETE FROM slots WHERE id = %s", (slot_id,))
            conn.commit()
            return resp(200, {'status': 'deleted'})

        return resp(405, {'detail': 'Method not allowed'})
    finally:
        conn.close()
