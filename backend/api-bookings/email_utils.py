"""
Утилиты для отправки email-уведомлений клиентам через Gmail SMTP.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

STATUS_LABELS = {
    'pending': 'Ожидает подтверждения',
    'confirmed': 'Подтверждён',
    'success': 'Созвон прошёл успешно',
    'cancelled_by_client': 'Отменён клиентом',
    'cancelled_by_expert': 'Отменён экспертом',
    'failed': 'Созвон не состоялся',
    'reschedule_request': 'Запрос на перенос времени',
}

STATUS_COLORS = {
    'pending': '#f59e0b',
    'confirmed': '#10b981',
    'success': '#06b6d4',
    'cancelled_by_client': '#ef4444',
    'cancelled_by_expert': '#f97316',
    'failed': '#7c3aed',
    'reschedule_request': '#ec4899',
}


def _send(to_email: str, subject: str, html: str):
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


def _base_template(title: str, content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ margin:0; padding:0; background:#0f172a; font-family:'Segoe UI',system-ui,sans-serif; color:#f1f5f9; }}
  .wrap {{ max-width:520px; margin:40px auto; padding:0 16px; }}
  .card {{ background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); border-radius:20px; padding:32px; }}
  .logo {{ font-size:22px; font-weight:700; background:linear-gradient(135deg,#2dd4bf,#38bdf8); -webkit-background-clip:text; background-clip:text; color:transparent; margin-bottom:24px; }}
  h2 {{ margin:0 0 16px; font-size:20px; color:#f1f5f9; }}
  .row {{ display:flex; gap:8px; margin-bottom:10px; font-size:14px; }}
  .label {{ color:#94a3b8; min-width:120px; }}
  .value {{ color:#f1f5f9; font-weight:500; }}
  .badge {{ display:inline-block; padding:4px 14px; border-radius:999px; font-size:13px; font-weight:700; margin:16px 0; }}
  .zoom-btn {{ display:inline-block; margin-top:20px; padding:12px 28px; background:#2dd4bf; color:#0f172a; border-radius:10px; font-weight:700; font-size:14px; text-decoration:none; }}
  .comment-box {{ background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:12px 16px; font-size:13px; color:#cbd5e1; margin-top:12px; }}
  .footer {{ margin-top:24px; font-size:12px; color:#475569; text-align:center; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <div class="logo">📅 Расписание экспертов АСМ</div>
    {content}
  </div>
  <div class="footer">Это автоматическое письмо, отвечать на него не нужно.<br>© АСМ</div>
</div>
</body></html>"""


def send_booking_created(to_email: str, client_name: str, expert_name: str,
                          date: str, start_time: str, end_time: str, zoom_link: str):
    """Письмо клиенту при создании записи."""
    if not to_email:
        return
    content = f"""
    <h2>Вы записаны на созвон!</h2>
    <p style="color:#94a3b8;font-size:14px;margin-bottom:20px">Здравствуйте, {client_name}! Ваша запись успешно создана.</p>
    <div class="row"><span class="label">Эксперт:</span><span class="value">{expert_name}</span></div>
    <div class="row"><span class="label">Дата:</span><span class="value">{date}</span></div>
    <div class="row"><span class="label">Время:</span><span class="value">{start_time} – {end_time}</span></div>
    <div class="badge" style="background:#10b981;color:white">✅ Запись создана</div>
    <br>
    <a href="{zoom_link}" class="zoom-btn">🔗 Открыть Zoom</a>
    <p style="color:#64748b;font-size:12px;margin-top:16px">Сохраните эту ссылку — она понадобится для созвона.</p>
    """
    _send(to_email, f'Запись на созвон с {expert_name} — {date}', _base_template('Запись создана', content))


def send_status_changed(to_email: str, client_name: str, expert_name: str,
                         date: str, start_time: str, new_status: str,
                         comment: str, zoom_link: str):
    """Письмо клиенту при смене статуса созвона."""
    if not to_email:
        return
    label = STATUS_LABELS.get(new_status, new_status)
    color = STATUS_COLORS.get(new_status, '#94a3b8')

    comment_block = ''
    if comment and comment.strip():
        comment_block = f'<div class="comment-box">💬 <strong>Комментарий:</strong><br>{comment}</div>'

    zoom_block = ''
    if zoom_link and new_status not in ('cancelled_by_client', 'cancelled_by_expert', 'failed'):
        zoom_block = f'<br><a href="{zoom_link}" class="zoom-btn">🔗 Открыть Zoom</a>'

    content = f"""
    <h2>Статус вашей записи изменился</h2>
    <p style="color:#94a3b8;font-size:14px;margin-bottom:20px">Здравствуйте, {client_name}!</p>
    <div class="row"><span class="label">Эксперт:</span><span class="value">{expert_name}</span></div>
    <div class="row"><span class="label">Дата:</span><span class="value">{date}</span></div>
    <div class="row"><span class="label">Время:</span><span class="value">{start_time}</span></div>
    <div class="badge" style="background:{color};color:{'#0f172a' if new_status == 'pending' else 'white'}">{label}</div>
    {comment_block}
    {zoom_block}
    """
    _send(to_email, f'Статус записи: {label} — {date}', _base_template('Изменение статуса', content))


def send_expert_new_booking(to_email: str, expert_name: str, client_name: str,
                             client_phone: str, client_email: str,
                             date: str, start_time: str, end_time: str,
                             manager_name: str, zoom_link: str):
    """Письмо эксперту при новой записи клиента к нему."""
    if not to_email:
        return
    phone_row = f'<div class="row"><span class="label">Телефон:</span><span class="value">{client_phone}</span></div>' if client_phone else ''
    email_row = f'<div class="row"><span class="label">Email:</span><span class="value">{client_email}</span></div>' if client_email else ''
    content = f"""
    <h2>Новая запись клиента!</h2>
    <p style="color:#94a3b8;font-size:14px;margin-bottom:20px">Здравствуйте, {expert_name}! К вам записался новый клиент.</p>
    <div class="row"><span class="label">Клиент:</span><span class="value"><strong>{client_name}</strong></span></div>
    {phone_row}
    {email_row}
    <div style="height:12px"></div>
    <div class="row"><span class="label">Дата:</span><span class="value">{date}</span></div>
    <div class="row"><span class="label">Время:</span><span class="value">{start_time} – {end_time}</span></div>
    <div class="row"><span class="label">Менеджер:</span><span class="value">{manager_name}</span></div>
    <div class="badge" style="background:#f59e0b;color:#1a1a2e">⏳ Ожидает подтверждения</div>
    <br>
    <a href="{zoom_link}" class="zoom-btn">🔗 Открыть Zoom</a>
    <p style="color:#64748b;font-size:12px;margin-top:16px">Войдите в систему, чтобы подтвердить или изменить статус записи.</p>
    """
    _send(to_email, f'Новая запись: {client_name} — {date} {start_time}', _base_template('Новая запись', content))


def send_rescheduled(to_email: str, client_name: str, expert_name: str,
                      new_date: str, new_start_time: str, zoom_link: str):
    """Письмо клиенту при переносе записи."""
    if not to_email:
        return
    content = f"""
    <h2>Ваша запись перенесена</h2>
    <p style="color:#94a3b8;font-size:14px;margin-bottom:20px">Здравствуйте, {client_name}! Менеджер перенёс время вашего созвона.</p>
    <div class="row"><span class="label">Эксперт:</span><span class="value">{expert_name}</span></div>
    <div class="row"><span class="label">Новая дата:</span><span class="value">{new_date}</span></div>
    <div class="row"><span class="label">Новое время:</span><span class="value">{new_start_time}</span></div>
    <div class="badge" style="background:#3b82f6;color:white">🔄 Перенесено</div>
    <br>
    <a href="{zoom_link}" class="zoom-btn">🔗 Открыть Zoom</a>
    """
    _send(to_email, f'Запись перенесена — новое время {new_date} {new_start_time}', _base_template('Перенос записи', content))