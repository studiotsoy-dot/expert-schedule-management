"""
API для управления пользователями системы расписания экспертов.
Поддерживает регистрацию, получение, обновление и удаление. v4
"""
import json
import os
import uuid
from datetime import datetime
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


def row_to_user(row):
    return {
        'id': row[0],
        'name': row[1],
        'email': row[2],
        'role': row[3],
        'portfolio_url': row[4] or '',
        'is_active': bool(row[5]),
        'created_at': row[6] or '',
    }


def handler(event: dict, context) -> dict:
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')

    params = event.get('queryStringParameters') or {}

    conn = get_conn()
    cur = conn.cursor()

    # DELETE ?user_id=...
    if method == 'DELETE':
        user_id = params.get('user_id') or (event.get('body') and json.loads(event.get('body') or '{}')).get('user_id')
        if not user_id:
            conn.close()
            return resp(400, {'detail': 'user_id обязателен'})

        cur.execute("SELECT id FROM users WHERE role = 'admin' AND is_active = 1")
        admins = cur.fetchall()
        cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return resp(404, {'detail': 'Пользователь не найден'})
        if row[0] == 'admin' and len(admins) <= 1:
            conn.close()
            return resp(403, {'detail': 'Нельзя удалить последнего администратора'})
        if row[0] == 'expert':
            cur.execute("DELETE FROM slots WHERE expert_id = %s", (user_id,))
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()
        return resp(200, {'status': 'deleted'})

    # GET /
    if method == 'GET':
        cur.execute("SELECT id, name, email, role, portfolio_url, is_active, created_at FROM users ORDER BY created_at")
        rows = cur.fetchall()
        conn.close()
        return resp(200, [row_to_user(r) for r in rows])

    # POST / — регистрация / вход
    if method == 'POST':
        body = json.loads(event.get('body') or '{}')
        name = body.get('name', '').strip()
        email = body.get('email', '').strip().lower()
        role = body.get('role', 'manager')
        portfolio_url = body.get('portfolio_url', '')

        if not name or not email:
            conn.close()
            return resp(400, {'detail': 'Укажите имя и email'})

        cur.execute("SELECT id, name, email, role, portfolio_url, is_active, created_at FROM users WHERE email = %s", (email,))
        existing = cur.fetchone()
        if existing:
            user = row_to_user(existing)
            if not user['is_active']:
                conn.close()
                return resp(403, {'detail': 'Ваш аккаунт заблокирован'})
            if user['role'] != role:
                conn.close()
                return resp(403, {'detail': 'Эта почта уже зарегистрирована с другой ролью'})
            conn.close()
            return resp(200, user)

        user_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        cur.execute(
            "INSERT INTO users (id, name, email, role, portfolio_url, is_active, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (user_id, name, email, role, portfolio_url, 1, now)
        )
        conn.commit()
        new_user = {'id': user_id, 'name': name, 'email': email, 'role': role, 'portfolio_url': portfolio_url, 'is_active': True, 'created_at': now}
        conn.close()
        return resp(200, new_user)

    # PUT / — обновление роли/статуса/визитки
    if method == 'PUT':
        body = json.loads(event.get('body') or '{}')
        user_id = body.get('user_id')
        if not user_id:
            conn.close()
            return resp(400, {'detail': 'user_id обязателен'})

        updates = []
        values = []
        if body.get('name') is not None:
            updates.append("name = %s"); values.append(body['name'])
        if body.get('role') is not None:
            updates.append("role = %s"); values.append(body['role'])
        if body.get('is_active') is not None:
            updates.append("is_active = %s"); values.append(1 if body['is_active'] else 0)
        if body.get('portfolio_url') is not None:
            updates.append("portfolio_url = %s"); values.append(body['portfolio_url'])

        if not updates:
            conn.close()
            return resp(400, {'detail': 'Нет данных для обновления'})

        values.append(user_id)
        cur.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s RETURNING id, name, email, role, portfolio_url, is_active, created_at", values)
        row = cur.fetchone()
        if not row:
            conn.close()
            return resp(404, {'detail': 'Пользователь не найден'})
        conn.commit()
        conn.close()
        return resp(200, row_to_user(row))

    conn.close()
    return resp(405, {'detail': 'Method not allowed'})