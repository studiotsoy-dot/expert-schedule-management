"""
Утилиты для отправки email-уведомлений клиентам через Gmail SMTP.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

APP_URL = 'https://expert-schedule-management--preview.poehali.dev'

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
    'pending': '#d97706',
    'confirmed': '#059669',
    'success': '#0891b2',
    'cancelled_by_client': '#dc2626',
    'cancelled_by_expert': '#ea580c',
    'failed': '#7c3aed',
    'reschedule_request': '#db2777',
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
  .btn-amber {{ background:#d97706; color:#ffffff; }}
  .btn-app {{ background:#1e293b; color:#ffffff; }}
  .comment-box {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px 16px; font-size:13px; color:#334155; margin-top:16px; }}
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


def send_booking_created(to_email: str, client_name: str, expert_name: str,
                          date: str, start_time: str, end_time: str, zoom_link: str):
    """Письмо клиенту при создании записи. Без ссылок на систему и Zoom (запись ещё не подтверждена)."""
    if not to_email:
        return
    content = f"""
    <h2>Вы записаны на созвон!</h2>
    <p style="color:#475569;font-size:14px;margin-bottom:20px">Здравствуйте, {client_name}! Ваша запись успешно создана и ожидает подтверждения.</p>
    <div class="row"><span class="label">Эксперт:</span><span class="value">{expert_name}</span></div>
    <div class="row"><span class="label">Дата:</span><span class="value">{date}</span></div>
    <div class="row"><span class="label">Время:</span><span class="value">{start_time} – {end_time}</span></div>
    <div class="badge" style="background:#d97706">⏳ Ожидает подтверждения</div>
    <p style="color:#94a3b8;font-size:12px;margin-top:16px">Как только эксперт подтвердит запись, вы получите письмо со всеми деталями.</p>
    """
    _send(to_email, f'Запись на созвон с {expert_name} — {date}', _base_template(content))


def send_status_changed(to_email: str, client_name: str, expert_name: str,
                         date: str, start_time: str, new_status: str,
                         comment: str, zoom_link: str):
    """Письмо клиенту при смене статуса. Zoom и комментарий — только при confirmed."""
    if not to_email:
        return
    label = STATUS_LABELS.get(new_status, new_status)
    color = STATUS_COLORS.get(new_status, '#64748b')

    zoom_block = ''
    if new_status == 'confirmed' and zoom_link:
        zoom_block = f'<br><a href="{zoom_link}" class="btn btn-teal">🔗 Войти в Zoom</a><p style="color:#94a3b8;font-size:12px;margin-top:12px">Сохраните эту ссылку — она понадобится для созвона.</p>'

    comment_block = ''
    if new_status == 'confirmed' and comment:
        comment_block = f'<hr class="divider"><div style="font-size:13px;color:#64748b;margin-bottom:6px;font-weight:600;">💬 Комментарий эксперта:</div><div class="comment-box">{comment}</div>'

    content = f"""
    <h2>Статус вашей записи изменился</h2>
    <p style="color:#475569;font-size:14px;margin-bottom:20px">Здравствуйте, {client_name}!</p>
    <div class="row"><span class="label">Эксперт:</span><span class="value">{expert_name}</span></div>
    <div class="row"><span class="label">Дата:</span><span class="value">{date}</span></div>
    <div class="row"><span class="label">Время:</span><span class="value">{start_time}</span></div>
    <div class="badge" style="background:{color}">{label}</div>
    {comment_block}
    {zoom_block}
    """
    _send(to_email, f'Статус записи: {label} — {date}', _base_template(content))


def send_expert_new_booking(to_email: str, expert_name: str, client_name: str,
                             client_phone: str, client_email: str,
                             date: str, start_time: str, end_time: str,
                             manager_name: str, zoom_link: str, client_comment: str = ''):
    """Письмо эксперту при новой записи клиента к нему."""
    if not to_email:
        return
    phone_row = f'<div class="row"><span class="label">Телефон:</span><span class="value">{client_phone}</span></div>' if client_phone else ''
    email_row = f'<div class="row"><span class="label">Email:</span><span class="value">{client_email}</span></div>' if client_email else ''
    comment_block = f'<hr class="divider"><div style="font-size:13px;color:#64748b;margin-bottom:6px;font-weight:600;">📝 Комментарий менеджера о клиенте:</div><div class="comment-box">{client_comment}</div>' if client_comment else ''
    content = f"""
    <h2>Новая запись клиента!</h2>
    <p style="color:#475569;font-size:14px;margin-bottom:20px">Здравствуйте, {expert_name}! К вам записался новый клиент.</p>
    <div class="row"><span class="label">Клиент:</span><span class="value"><strong>{client_name}</strong></span></div>
    {phone_row}
    {email_row}
    <hr class="divider">
    <div class="row"><span class="label">Дата:</span><span class="value">{date}</span></div>
    <div class="row"><span class="label">Время:</span><span class="value">{start_time} – {end_time}</span></div>
    <div class="row"><span class="label">Менеджер:</span><span class="value">{manager_name}</span></div>
    {comment_block}
    <div class="badge" style="background:#d97706">⏳ Ожидает подтверждения</div>
    <br>
    <a href="{zoom_link}" class="btn btn-teal">🔗 Открыть Zoom</a>
    <hr class="divider">
    <a href="{APP_URL}" class="btn btn-app">🚀 Войти в систему</a>
    <p style="color:#94a3b8;font-size:12px;margin-top:12px">Войдите, чтобы подтвердить или изменить статус записи.</p>
    """
    _send(to_email, f'Новая запись: {client_name} — {date} {start_time}', _base_template(content))


def send_rescheduled(to_email: str, client_name: str, expert_name: str,
                      new_date: str, new_start_time: str, zoom_link: str):
    """Письмо клиенту при переносе записи. Без Zoom — запись требует повторного подтверждения."""
    if not to_email:
        return
    content = f"""
    <h2>Ваша запись перенесена</h2>
    <p style="color:#475569;font-size:14px;margin-bottom:20px">Здравствуйте, {client_name}! Время вашего созвона изменено и ожидает подтверждения.</p>
    <div class="row"><span class="label">Эксперт:</span><span class="value">{expert_name}</span></div>
    <div class="row"><span class="label">Новая дата:</span><span class="value">{new_date}</span></div>
    <div class="row"><span class="label">Новое время:</span><span class="value">{new_start_time}</span></div>
    <div class="badge" style="background:#3b82f6">🔄 Перенесено</div>
    <p style="color:#94a3b8;font-size:12px;margin-top:16px">Как только эксперт подтвердит новое время, вы получите письмо со ссылкой на Zoom.</p>
    """
    _send(to_email, f'Запись перенесена на {new_date}', _base_template(content))


def send_expert_rescheduled(to_email: str, expert_name: str, client_name: str,
                             old_date: str, old_start: str,
                             new_date: str, new_start_time: str, new_end_time: str,
                             manager_name: str, zoom_link: str):
    """Письмо эксперту при переносе его записи менеджером."""
    if not to_email:
        return
    content = f"""
    <h2>Запись клиента перенесена</h2>
    <p style="color:#475569;font-size:14px;margin-bottom:20px">Здравствуйте, {expert_name}! Менеджер {manager_name} перенёс время записи.</p>
    <div class="row"><span class="label">Клиент:</span><span class="value"><strong>{client_name}</strong></span></div>
    <hr class="divider">
    <div class="row"><span class="label">Было:</span><span class="value" style="color:#94a3b8;text-decoration:line-through">{old_date} {old_start}</span></div>
    <div class="row"><span class="label">Стало:</span><span class="value">{new_date} {new_start_time} – {new_end_time}</span></div>
    <div class="row"><span class="label">Менеджер:</span><span class="value">{manager_name}</span></div>
    <div class="badge" style="background:#3b82f6">🔄 Перенесено</div>
    <br>
    <a href="{zoom_link}" class="btn btn-teal">🔗 Открыть Zoom</a>
    <hr class="divider">
    <a href="{APP_URL}" class="btn btn-app">🚀 Войти в систему</a>
    """
    _send(to_email, f'Перенос записи: {client_name} — {new_date}', _base_template(content))


def send_manager_status_changed(to_email: str, manager_name: str, client_name: str,
                                 expert_name: str, date: str, start_time: str,
                                 new_status: str, comment: str):
    """Письмо менеджеру при смене статуса записи экспертом."""
    if not to_email:
        return
    label = STATUS_LABELS.get(new_status, new_status)
    color = STATUS_COLORS.get(new_status, '#64748b')
    comment_block = f'<hr class="divider"><div style="font-size:13px;color:#64748b;margin-bottom:6px;font-weight:600;">💬 Комментарий эксперта:</div><div class="comment-box">{comment}</div>' if comment else ''
    content = f"""
    <h2>Статус записи клиента изменён</h2>
    <p style="color:#475569;font-size:14px;margin-bottom:20px">Здравствуйте, {manager_name}! Эксперт обновил статус вашей записи.</p>
    <div class="row"><span class="label">Клиент:</span><span class="value"><strong>{client_name}</strong></span></div>
    <div class="row"><span class="label">Эксперт:</span><span class="value">{expert_name}</span></div>
    <hr class="divider">
    <div class="row"><span class="label">Дата:</span><span class="value">{date}</span></div>
    <div class="row"><span class="label">Время:</span><span class="value">{start_time}</span></div>
    <div class="badge" style="background:{color}">{label}</div>
    {comment_block}
    <hr class="divider">
    <a href="{APP_URL}" class="btn btn-app">🚀 Открыть систему</a>
    """
    _send(to_email, f'Статус записи [{client_name}]: {label}', _base_template(content))


def send_reminder(to_email: str, client_name: str, expert_name: str,
                  date: str, start_time: str, zoom_link: str, minutes_before: int):
    """Напоминание клиенту о предстоящем созвоне за 1 час или 10 минут."""
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
    else:
        badge_text = '🔔 До созвона 10 минут!'
        badge_color = '#dc2626'
        tip = 'Пора подключаться! Нажмите кнопку ниже, чтобы войти в Zoom.'
        checklist = ''

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
    subject = f'⏰ Напоминание: созвон с {expert_name} через {"1 час" if minutes_before == 60 else "10 минут"} — {date} {start_time}'
    _send(to_email, subject, _base_template(content))