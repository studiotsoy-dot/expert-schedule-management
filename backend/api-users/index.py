"""
API для управления пользователями системы расписания экспертов. v5
"""
import json
import os
import uuid
from datetime import datetime
import psycopg2

PROTECTED_EMAIL = 'studiotsoy@gmail.com'
CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}
USER_FIELDS = 'id, name, email, role, portfolio_url, is_active, created_at'


def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def resp(status, body):
    return {'statusCode': status, 'headers': {**CORS, 'Content-Type': 'application/json'}, 'body': json.dumps(body, ensure_ascii=False)}


def row_to_user(row):
    return {'id': row[0], 'name': row[1], 'email': row[2], 'role': row[3], 'portfolio_url': row[4] or '', 'is_active': bool(row[5]), 'created_at': row[6] or ''}


def handler(event: dict, context) -> dict:
    """Управление пользователями: CRUD + защита аккаунта разработчика."""
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS, 'body': ''}

    method = event.get('httpMethod', 'GET')
    params = event.get('queryStringParameters') or {}

    conn = get_conn()
    cur = conn.cursor()
    try:
        # GET ?email= или список всех
        if method == 'GET':
            email_param = params.get('email', '').strip().lower()
            if email_param:
                cur.execute(f"SELECT {USER_FIELDS} FROM users WHERE email = %s", (email_param,))
                row = cur.fetchone()
                if not row:
                    return resp(404, {'detail': 'Пользователь не найден'})
                return resp(200, row_to_user(row))
            cur.execute(f"SELECT {USER_FIELDS} FROM users ORDER BY created_at")
            return resp(200, [row_to_user(r) for r in cur.fetchall()])

        # POST — регистрация / вход
        if method == 'POST':
            body = json.loads(event.get('body') or '{}')
            name = body.get('name', '').strip()
            email = body.get('email', '').strip().lower()
            role = body.get('role', 'manager')
            portfolio_url = body.get('portfolio_url', '')
            if not name or not email:
                return resp(400, {'detail': 'Укажите имя и email'})

            cur.execute(f"SELECT {USER_FIELDS} FROM users WHERE email = %s", (email,))
            existing = cur.fetchone()
            if existing:
                user = row_to_user(existing)
                if not user['is_active']:
                    return resp(403, {'detail': 'Ваш аккаунт заблокирован'})
                return resp(200, user)

            user_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            cur.execute(
                "INSERT INTO users (id, name, email, role, portfolio_url, is_active, created_at) VALUES (%s,%s,%s,%s,%s,1,%s)",
                (user_id, name, email, role, portfolio_url, now)
            )
            conn.commit()
            return resp(200, {'id': user_id, 'name': name, 'email': email, 'role': role, 'portfolio_url': portfolio_url, 'is_active': True, 'created_at': now})

        # PUT — обновление
        if method == 'PUT':
            body = json.loads(event.get('body') or '{}')
            user_id = body.get('user_id')
            if not user_id:
                return resp(400, {'detail': 'user_id обязателен'})

            cur.execute("SELECT email FROM users WHERE id = %s", (user_id,))
            target = cur.fetchone()
            if not target:
                return resp(404, {'detail': 'Пользователь не найден'})
            if target[0] == PROTECTED_EMAIL:
                return resp(403, {'detail': 'Этот аккаунт защищён и не может быть изменён'})

            updates, values = [], []
            for field in ('name', 'role', 'portfolio_url'):
                if body.get(field) is not None:
                    updates.append(f"{field} = %s"); values.append(body[field])
            if body.get('is_active') is not None:
                updates.append("is_active = %s"); values.append(1 if body['is_active'] else 0)
            if body.get('email') is not None:
                new_email = body['email'].strip().lower()
                if not new_email or '@' not in new_email:
                    return resp(400, {'detail': 'Некорректный email'})
                cur.execute("SELECT id FROM users WHERE email = %s AND id != %s", (new_email, user_id))
                if cur.fetchone():
                    return resp(409, {'detail': 'Этот email уже занят другим пользователем'})
                updates.append("email = %s"); values.append(new_email)

            if not updates:
                return resp(400, {'detail': 'Нет данных для обновления'})

            values.append(user_id)
            cur.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s RETURNING {USER_FIELDS}", values)
            row = cur.fetchone()
            conn.commit()
            return resp(200, row_to_user(row))

        # DELETE
        if method == 'DELETE':
            user_id = params.get('user_id') or json.loads(event.get('body') or '{}').get('user_id')
            if not user_id:
                return resp(400, {'detail': 'user_id обязателен'})

            cur.execute("SELECT role, email FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if not row:
                return resp(404, {'detail': 'Пользователь не найден'})
            if row[1] == PROTECTED_EMAIL:
                return resp(403, {'detail': 'Этот аккаунт защищён и не может быть удалён'})
            if row[0] == 'admin':
                cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1")
                if cur.fetchone()[0] <= 1:
                    return resp(403, {'detail': 'Нельзя удалить последнего администратора'})
            if row[0] == 'expert':
                cur.execute("DELETE FROM slots WHERE expert_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            return resp(200, {'status': 'deleted'})

        return resp(405, {'detail': 'Method not allowed'})
    finally:
        conn.close()
