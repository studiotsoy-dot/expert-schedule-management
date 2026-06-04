import { useState, useEffect } from 'react';
import * as XLSX from 'xlsx';
import Icon from '@/components/ui/icon';
import StatusBadge from './StatusBadge';
import CommentCell from './CommentCell';
import ClientCommentCell from './ClientCommentCell';
import { User, Slot, Booking } from '@/types';
import { apiUsers, apiSlots, apiBookings } from '@/lib/api';

interface Props { user: User; }

function sortByDateTime<T extends { date: string; start_time: string }>(arr: T[]): T[] {
  return [...arr].sort((a, b) =>
    new Date(`${a.date} ${a.start_time}`).getTime() - new Date(`${b.date} ${b.start_time}`).getTime()
  );
}

function escapeHtml(str: string) {
  return str.replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m] || m));
}

export default function AdminView({ user }: Props) {
  const [tab, setTab] = useState<'slots' | 'bookings' | 'users'>('slots');
  const [slots, setSlots] = useState<Slot[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [expertFilter, setExpertFilter] = useState('all');
  const [editPortfolios, setEditPortfolios] = useState<Record<string, string>>({});
  const [editRoles, setEditRoles] = useState<Record<string, string>>({});
  const [editEmails, setEditEmails] = useState<Record<string, string>>({});

  const fetchAll = async (showLoader = false) => {
    if (showLoader) setLoading(true);
    try {
      const [s, b, u] = await Promise.all([
        apiSlots('/api/slots?action=admin').then(r => r.json()),
        apiBookings(`/api/bookings?role=admin&user_id=${user.id}`).then(r => r.json()),
        apiUsers('/api/users').then(r => r.json()),
      ]);
      setSlots(sortByDateTime(Array.isArray(s) ? s : []));
      setBookings(sortByDateTime(Array.isArray(b) ? b : []));
      const usersArr = Array.isArray(u) ? u : [];
      setUsers(usersArr);
      const portfolioMap: Record<string, string> = {};
      const roleMap: Record<string, string> = {};
      const emailMap: Record<string, string> = {};
      usersArr.forEach((usr: User) => {
        portfolioMap[usr.id] = usr.portfolio_url || '';
        roleMap[usr.id] = usr.role;
        emailMap[usr.id] = usr.email || '';
      });
      setEditPortfolios(portfolioMap);
      setEditRoles(roleMap);
      setEditEmails(emailMap);
    } finally {
      if (showLoader) setLoading(false);
    }
  };

  const loadAll = () => fetchAll(true);

  useEffect(() => {
    fetchAll(true);
  }, []);

  const experts = users.filter(u => u.role === 'expert');
  const filteredSlots = expertFilter === 'all' ? slots : slots.filter(s => s.expert_id === expertFilter);

  const updateUser = async (userId: string) => {
    const newRole = editRoles[userId];
    const portfolioUrl = editPortfolios[userId] || '';
    const newEmail = editEmails[userId] || '';
    if (!confirm(`Сохранить изменения для пользователя?`)) return;
    const payload: Record<string, string> = { user_id: userId, role: newRole, portfolio_url: portfolioUrl };
    const originalEmail = users.find(u => u.id === userId)?.email || '';
    if (newEmail && newEmail !== originalEmail) payload.email = newEmail;
    const res = await apiUsers('/api/users', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.ok) { alert('Обновлено!'); loadAll(); }
    else { const e = await res.json(); alert(e.detail || 'Ошибка'); }
  };

  const toggleBlock = async (userId: string, unblock: boolean) => {
    if (!confirm(`${unblock ? 'Разблокировать' : 'Заблокировать'} пользователя?`)) return;
    const res = await apiUsers('/api/users', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, is_active: unblock }),
    });
    if (res.ok) loadAll(); else alert('Ошибка');
  };

  const deleteUser = async (userId: string) => {
    if (!confirm('Удалить пользователя? Все его слоты будут удалены.')) return;
    const res = await apiUsers(`/api/users?user_id=${userId}`, { method: 'DELETE' });
    if (res.ok) loadAll();
    else { const e = await res.json(); alert(e.detail || 'Ошибка'); }
  };

  const deleteSlot = async (slotId: string) => {
    if (!confirm('Удалить слот? Если есть запись клиента — она тоже будет удалена.')) return;
    const res = await apiSlots(`/api/slots?slot_id=${slotId}&admin=true`, { method: 'DELETE' });
    if (res.ok) loadAll();
    else { const e = await res.json(); alert(e.detail || 'Ошибка'); }
  };

  const deleteBooking = async (bookingId: string) => {
    if (!confirm('Удалить запись клиента? Слот станет свободным.')) return;
    const res = await apiBookings(`/api/bookings?booking_id=${bookingId}`, { method: 'DELETE' });
    if (res.ok) loadAll();
    else { const e = await res.json(); alert(e.detail || 'Ошибка'); }
  };

  const exportToExcel = () => {
    const STATUS_MAP: Record<string, string> = {
      free: 'Свободен', booked: 'Забронирован', confirmed: 'Подтверждён',
      pending: 'Ожидает', success: 'Успешно', cancelled_by_client: 'Отменён клиентом',
      cancelled_by_expert: 'Отменён экспертом', failed: 'Не состоялся', reschedule_request: 'Перенос',
    };

    const bookingsSheet = bookings.map(b => ({
      'Клиент': b.client_name,
      'Email клиента': b.client_email || '',
      'Телефон клиента': b.client_phone || '',
      'Telegram': b.client_telegram || '',
      'Эксперт': b.expert_name || '',
      'Дата': b.date || '',
      'Время': b.start_time ? `${b.start_time} — ${b.end_time}` : '',
      'Менеджер': b.manager_name || '',
      'Статус созвона': STATUS_MAP[b.call_status] || b.call_status,
      'О клиенте (менеджер)': b.client_comment || '',
      'Комментарий эксперта': b.call_comment || '',
      'Zoom': b.zoom_link || '',
    }));

    const slotsSheet = slots.map(s => ({
      'Эксперт': s.expert_name || '',
      'Email эксперта': s.expert_email || '',
      'Дата': s.date,
      'Начало': s.start_time,
      'Конец': s.end_time,
      'Статус': STATUS_MAP[s.status] || s.status,
      'Клиент': s.booking?.client_name || '',
      'Телефон': s.booking?.client_phone || '',
    }));

    const usersSheet = users.map(u => ({
      'Имя': u.name,
      'Email': u.email,
      'Роль': u.role === 'admin' ? 'Администратор' : u.role === 'expert' ? 'Эксперт' : 'Менеджер',
      'Статус': u.is_active !== false ? 'Активен' : 'Заблокирован',
      'Визитка': u.portfolio_url || '',
      'Дата регистрации': u.created_at ? u.created_at.slice(0, 10) : '',
    }));

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(bookingsSheet), 'Записи');
    XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(slotsSheet), 'Слоты');
    XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(usersSheet), 'Пользователи');

    const date = new Date().toISOString().slice(0, 10);
    XLSX.writeFile(wb, `ASM_export_${date}.xlsx`);
  };

  return (
    <div className="animate-fade-in">
      <div className="flex gap-2 mb-5 border-b border-white/10 pb-3 flex-wrap items-center">
        {([['slots', 'Слоты экспертов', 'CalendarDays'], ['bookings', 'Все записи', 'ClipboardList'], ['users', 'Пользователи', 'Users']] as const).map(([t, label, icon]) => (
          <button key={t} onClick={() => setTab(t)} className={`tab-item flex items-center gap-2 ${tab === t ? 'active' : ''}`}>
            <Icon name={icon as 'Home'} size={15} />
            {label}
            {t === 'users' && users.length > 0 && (
              <span className="text-xs bg-white/10 text-slate-300 px-2 py-0.5 rounded-full">{users.length}</span>
            )}
          </button>
        ))}
        <div className="ml-auto flex gap-2">
          <button onClick={loadAll} className="btn-primary flex items-center gap-2 text-sm py-2 px-4">
            <Icon name="RefreshCw" size={14} />
            Обновить
          </button>
          <button onClick={exportToExcel} className="btn-primary flex items-center gap-2 text-sm py-2 px-4">
            <Icon name="Download" size={15} />
            Экспорт в Excel
          </button>
        </div>
      </div>

      {loading && <div className="text-slate-400 text-sm py-8 text-center">Загружаем...</div>}

      {/* SLOTS */}
      {!loading && tab === 'slots' && (
        <>
          <div className="flex gap-3 items-center mb-4 flex-wrap">
            <Icon name="Filter" size={14} className="text-slate-400" />
            <select className="form-input text-sm" value={expertFilter} onChange={e => setExpertFilter(e.target.value)}>
              <option value="all">Все эксперты</option>
              {experts.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
            </select>
          </div>
          <div className="overflow-x-auto overflow-y-auto max-h-[calc(100vh-280px)] rounded-xl border border-white/5">
            <table className="data-table">
              <thead className="sticky top-0 z-10"><tr>
                <th>Эксперт</th><th>Дата</th><th>Время</th><th>Статус</th>
                <th>Клиент</th><th>Телефон</th><th>Email</th><th>Telegram</th>
                <th>О клиенте</th><th>Статус созвона</th><th>Комментарий</th><th>Менеджер</th><th>Zoom</th><th></th>
              </tr></thead>
              <tbody>
                {filteredSlots.length === 0 && <tr><td colSpan={14} className="text-slate-500 text-center py-8">Нет слотов</td></tr>}
                {filteredSlots.map(slot => (
                  <tr key={slot.id}>
                    <td>
                      {slot.expert_portfolio
                        ? <a href={slot.expert_portfolio} target="_blank" rel="noreferrer" className="text-teal-400 hover:underline font-semibold">{slot.expert_name}</a>
                        : <strong>{slot.expert_name}</strong>}
                      <div className="text-slate-500 text-xs">{slot.expert_email}</div>
                    </td>
                    <td>{slot.date}</td>
                    <td className="whitespace-nowrap">{slot.start_time} — {slot.end_time}</td>
                    <td><StatusBadge status={slot.status} /></td>
                    {slot.booking ? (
                      <>
                        <td>{slot.booking.client_name}</td>
                        <td className="text-slate-400">{slot.booking.client_phone || '—'}</td>
                        <td className="text-slate-400">{slot.booking.client_email || '—'}</td>
                        <td className="text-slate-400">{slot.booking.client_telegram ? <a href={`https://t.me/${slot.booking.client_telegram.replace('@','')}`} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline">{slot.booking.client_telegram}</a> : '—'}</td>
                        <td>
                          <ClientCommentCell
                            text={slot.booking.client_comment || ''}
                            clientName={slot.booking.client_name}
                            clientPhone={slot.booking.client_phone}
                            clientEmail={slot.booking.client_email}
                            clientTelegram={slot.booking.client_telegram}
                            date={slot.booking.date}
                            startTime={slot.booking.start_time}
                          />
                        </td>
                        <td><StatusBadge status={slot.booking.call_status} /></td>
                        <td><CommentCell text={slot.booking.call_comment || '—'} /></td>
                        <td className="text-slate-400">{slot.booking.manager_name || '—'}</td>
                        <td>{slot.booking.zoom_link ? <a href={slot.booking.zoom_link} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline text-xs">🔗 Zoom</a> : '—'}</td>
                      </>
                    ) : (
                      <td colSpan={9} className="text-slate-600 text-center text-xs">— свободен —</td>
                    )}
                    <td>
                      <button className="btn-primary btn-danger text-xs py-1 px-2" onClick={() => deleteSlot(slot.id)}>🗑</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* BOOKINGS */}
      {!loading && tab === 'bookings' && (
        <div className="overflow-x-auto overflow-y-auto max-h-[calc(100vh-260px)] rounded-xl border border-white/5">
          <table className="data-table">
            <thead className="sticky top-0 z-10"><tr>
              <th>Клиент</th><th>Email</th><th>Телефон</th><th>Telegram</th><th>Эксперт</th>
              <th>Дата/Время</th><th>Менеджер</th><th>О клиенте</th><th>Статус</th><th>Комментарий</th><th>Zoom</th><th></th>
            </tr></thead>
            <tbody>
              {bookings.length === 0 && <tr><td colSpan={12} className="text-slate-500 text-center py-8">Нет записей</td></tr>}
              {bookings.map(b => (
                <tr key={b.id}>
                  <td><strong>{b.client_name}</strong></td>
                  <td className="text-slate-400">{b.client_email || '—'}</td>
                  <td className="text-slate-400">{b.client_phone || '—'}</td>
                  <td className="text-slate-400">{b.client_telegram ? <a href={`https://t.me/${b.client_telegram.replace('@','')}`} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline">{b.client_telegram}</a> : '—'}</td>
                  <td>
                    {b.expert_portfolio
                      ? <a href={b.expert_portfolio} target="_blank" rel="noreferrer" className="text-teal-400 hover:underline">{b.expert_name}</a>
                      : b.expert_name}
                  </td>
                  <td className="whitespace-nowrap">{b.date} {b.start_time}</td>
                  <td className="text-slate-400">{b.manager_name || '—'}</td>
                  <td>
                    <ClientCommentCell
                      text={b.client_comment || ''}
                      clientName={b.client_name}
                      clientPhone={b.client_phone}
                      clientEmail={b.client_email}
                      clientTelegram={b.client_telegram}
                      date={b.date}
                      startTime={b.start_time}
                    />
                  </td>
                  <td><StatusBadge status={b.call_status} /></td>
                  <td><CommentCell text={b.call_comment || '—'} /></td>
                  <td>{b.zoom_link ? <a href={b.zoom_link} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline text-xs">🔗 Zoom</a> : '—'}</td>
                  <td>
                    <button className="btn-primary btn-danger text-xs py-1 px-2" onClick={() => deleteBooking(b.id)}>🗑</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* USERS */}
      {!loading && tab === 'users' && (
        <>
          <div className="overflow-x-auto overflow-y-auto max-h-[calc(100vh-260px)] rounded-xl border border-white/5">
            <table className="data-table">
              <thead className="sticky top-0 z-10"><tr>
                <th>Имя</th><th>Email</th><th>Роль</th><th>Статус</th><th>Визитка (URL)</th><th>Действия</th><th>Удалить</th>
              </tr></thead>
              <tbody>
                {users.map(u => {
                  const isActive = u.is_active !== false;
                  return (
                    <tr key={u.id}>
                      <td><strong>{escapeHtml(u.name)}</strong></td>
                      <td>
                        <input
                          className="form-input text-xs py-1 w-44"
                          value={editEmails[u.id] ?? u.email}
                          onChange={e => setEditEmails(m => ({ ...m, [u.id]: e.target.value }))}
                          placeholder="email@example.com"
                        />
                      </td>
                      <td>
                        <select
                          className="form-input text-xs py-1"
                          value={editRoles[u.id] || u.role}
                          onChange={e => setEditRoles(r => ({ ...r, [u.id]: e.target.value }))}
                          disabled={u.id === user.id}
                        >
                          <option value="manager">Менеджер</option>
                          <option value="expert">Эксперт</option>
                          <option value="admin">Админ</option>
                        </select>
                      </td>
                      <td>
                        <span className={`text-xs font-semibold ${isActive ? 'text-emerald-400' : 'text-red-400'}`}>
                          {isActive ? 'Активен' : 'Заблокирован'}
                        </span>
                      </td>
                      <td>
                        {(editRoles[u.id] || u.role) === 'expert' ? (
                          <input
                            className="form-input text-xs py-1 w-36"
                            placeholder="https://..."
                            value={editPortfolios[u.id] || ''}
                            onChange={e => setEditPortfolios(p => ({ ...p, [u.id]: e.target.value }))}
                          />
                        ) : <span className="text-slate-600 text-xs">—</span>}
                      </td>
                      <td>
                        <div className="flex gap-1.5">
                          <button className="btn-primary btn-secondary text-xs py-1 px-2" onClick={() => updateUser(u.id)}>💾</button>
                          <button
                            className={`btn-primary text-xs py-1 px-2 ${isActive ? 'btn-warning' : 'btn-success'}`}
                            onClick={() => toggleBlock(u.id, !isActive)}
                          >
                            {isActive ? '🔒' : '🔓'}
                          </button>
                        </div>
                      </td>
                      <td>
                        {u.id !== user.id ? (
                          <button className="btn-primary btn-danger text-xs py-1 px-2" onClick={() => deleteUser(u.id)}>🗑</button>
                        ) : (
                          <span className="text-xs bg-white/10 text-slate-400 px-2 py-0.5 rounded-full">Вы</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="text-slate-600 text-xs mt-3">⚠️ Нельзя удалить или изменить роль последнего администратора.</p>
        </>
      )}
    </div>
  );
}