"""
Cron-функция отправки напоминаний клиентам о предстоящих созвонах.
Запускается каждые 5 минут. Отправляет письма за 1 час и за 10 минут до начала.
"""
import os
import json
import smtplib
import psycopg2
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}

MSK_OFFSET = timedelta(hours=3)


def resp(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': {**CORS_HEADERS, 'Content-Type': 'application/json'},
        'body': json.dumps(body, ensure_ascii=False),
    }


def _send_email(to_email: str, subject: str, html: str):
    smtp_email = os.environ.get('SMTP_EMAIL', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')
    if not smtp_email or not smtp_password or not to_email:
        return
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f'АСМ Расписание <{smtp_email}>'
    msg['To'] = to_email
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, to_email, msg.as_string())


def _base_template(content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ margin:0; padding:0; background:#f1f5f9; font-family:'Segoe UI',system-ui,sans-serif; color:#1e293b; }}
  .wrap {{ max-width:520px; margin:40px auto; padding:0 16px; }}
  .card {{ background:#ffffff; border:1px solid #e2e8f0; border-radius:16px; padding:32px; box-shadow:0 4px 24px rgba(0,0,0,0.08); }}
  .logo {{ font-size:20px; font-weight:700; color:#0f766e; margin-bottom:24px; }}
  h2 {{ margin:0 0 16px; font-size:20px; color:#0f172a; font-weight:700; }}
  .row {{ display:flex; gap:8px; margin-bottom:10px; font-size:14px; }}
  .label {{ color:#64748b; min-width:120px; }}
  .value {{ color:#0f172a; font-weight:600; }}
  .badge {{ display:inline-block; padding:8px 18px; border-radius:999px; font-size:13px; font-weight:700; margin:16px 0; color:#ffffff; }}
  .btn {{ display:inline-block; margin-top:16px; padding:12px 28px; border-radius:10px; font-weight:700; font-size:14px; text-decoration:none; }}
  .btn-teal {{ background:#0d9488; color:#ffffff; }}
  .divider {{ border:none; border-top:1px solid #e2e8f0; margin:20px 0; }}
  .footer {{ margin-top:24px; font-size:12px; color:#94a3b8; text-align:center; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <div class="logo">📅 Расписание экспертов АСМ</div>
    {content}
  </div>
  <div class="footer">Это автоматическое письмо, отвечать на него не нужно.&nbsp;&nbsp;©&nbsp;АСМ</div>
</div>
</body></html>"""


def _send_reminder(to_email: str, client_name: str, expert_name: str,
                   date: str, start_time: str, zoom_link: str, minutes_before: int):
    if not to_email:
        return
    if minutes_before == 60:
        badge_text = '⏰ До созвона 1 час'
        badge_color = '#d97706'
        tip = 'У вас есть час, чтобы проверить связь и подготовиться.'
        checklist = """
        <hr class="divider">
        <div style="font-size:13px;color:#64748b;font-weight:600;margin-bottom:8px;">✅ Что проверить заранее:</div>
        <ul style="font-size:13px;color:#334155;padding-left:20px;margin:0;line-height:2">
          <li>Откройте Zoom и войдите в аккаунт</li>
          <li>Проверьте микрофон и камеру</li>
          <li>Убедитесь в стабильном интернет-соединении</li>
          <li>Найдите тихое место без посторонних шумов</li>
        </ul>"""
        time_label = '1 час'
    else:
        badge_text = '🔔 До созвона 10 минут!'
        badge_color = '#dc2626'
        tip = 'Пора подключаться! Нажмите кнопку ниже, чтобы войти в Zoom.'
        checklist = ''
        time_label = '10 минут'

    content = f"""
    <h2>Напоминание о созвоне</h2>
    <p style="color:#475569;font-size:14px;margin-bottom:20px">Здравствуйте, {client_name}! {tip}</p>
    <div class="row"><span class="label">Эксперт:</span><span class="value">{expert_name}</span></div>
    <div class="row"><span class="label">Дата:</span><span class="value">{date}</span></div>
    <div class="row"><span class="label">Время:</span><span class="value">{start_time}</span></div>
    <div class="badge" style="background:{badge_color}">{badge_text}</div>
    {checklist}
    <hr class="divider">
    <a href="{zoom_link}" class="btn btn-teal" style="font-size:16px;padding:14px 32px">🔗 Войти в Zoom</a>
    <p style="color:#94a3b8;font-size:12px;margin-top:16px">Ссылка действительна только для вашего созвона.</p>
    """
    subject = f'⏰ Напоминание: созвон с {expert_name} через {time_label} — {date} {start_time}'
    _send_email(to_email, subject, _base_template(content))


def handler(event: dict, context) -> dict:
    """Проверяет предстоящие подтверждённые записи и отправляет напоминания клиентам."""
    if event.get('httpMethod') == 'OPTIONS':
        return resp(200, {})

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    now_msk = datetime.now(timezone.utc).replace(tzinfo=None) + MSK_OFFSET

    sent_1h = 0
    sent_10m = 0
    errors = []

    cur.execute("""
        SELECT
            b.id, b.client_email, b.client_name, b.zoom_link,
            b.reminder_1h_sent, b.reminder_10m_sent,
            s.date, s.start_time,
            u.name AS expert_name
        FROM bookings b
        JOIN slots s ON s.id = b.slot_id
        JOIN users u ON u.id = s.expert_id
        WHERE b.call_status IN ('pending', 'confirmed')
          AND b.client_email IS NOT NULL
          AND b.zoom_link IS NOT NULL
          AND (b.reminder_1h_sent = FALSE OR b.reminder_10m_sent = FALSE)
    """)
    rows = cur.fetchall()

    for row in rows:
        (booking_id, client_email, client_name, zoom_link,
         reminder_1h_sent, reminder_10m_sent,
         slot_date, slot_start, expert_name) = row

        try:
            slot_dt = datetime.strptime(f"{slot_date} {slot_start}", "%Y-%m-%d %H:%M")
        except Exception as e:
            errors.append(f"parse error {booking_id}: {e}")
            continue

        minutes_until = (slot_dt - now_msk).total_seconds() / 60

        if not reminder_1h_sent and 55 <= minutes_until <= 65:
            try:
                _send_reminder(client_email, client_name or '', expert_name or '',
                               str(slot_date), str(slot_start), zoom_link, 60)
                cur.execute("UPDATE bookings SET reminder_1h_sent = TRUE WHERE id = %s", (booking_id,))
                sent_1h += 1
            except Exception as e:
                errors.append(f"1h email {booking_id}: {e}")

        if not reminder_10m_sent and 7 <= minutes_until <= 13:
            try:
                _send_reminder(client_email, client_name or '', expert_name or '',
                               str(slot_date), str(slot_start), zoom_link, 10)
                cur.execute("UPDATE bookings SET reminder_10m_sent = TRUE WHERE id = %s", (booking_id,))
                sent_10m += 1
            except Exception as e:
                errors.append(f"10m email {booking_id}: {e}")

    conn.commit()
    conn.close()

    print(f"Reminders sent: 1h={sent_1h}, 10m={sent_10m}, checked={len(rows)}, errors={errors}")
    return resp(200, {
        'sent_1h': sent_1h,
        'sent_10m': sent_10m,
        'checked': len(rows),
        'errors': errors,
    })
