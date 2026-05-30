import { useState, useEffect } from 'react';
import Icon from '@/components/ui/icon';
import StatusBadge from './StatusBadge';
import StatusModal from './StatusModal';
import ClientCommentCell from './ClientCommentCell';
import CommentCell from './CommentCell';
import { User, Slot, Booking, CallStatus } from '@/types';
import { apiSlots, apiBookings } from '@/lib/api';

interface Props { user: User; }

function sortByDateTime<T extends { date: string; start_time: string }>(arr: T[]): T[] {
  return [...arr].sort((a, b) =>
    new Date(`${a.date} ${a.start_time}`).getTime() - new Date(`${b.date} ${b.start_time}`).getTime()
  );
}

const STATUSES: { value: CallStatus; label: string }[] = [
  { value: 'pending', label: '⏳ Ожидает' },
  { value: 'confirmed', label: '✅ Подтверждён' },
  { value: 'success', label: '🎉 Успешный' },
  { value: 'cancelled_by_client', label: '❌ Отменён клиентом' },
  { value: 'cancelled_by_expert', label: '⚠️ Отменён экспертом' },
  { value: 'failed', label: '💔 Неуспешный' },
  { value: 'reschedule_request', label: '🔄 Просьба перенести' },
];

export default function ExpertView({ user }: Props) {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [tab, setTab] = useState<'slots' | 'bookings'>('slots');
  const [loading, setLoading] = useState(false);

  const [newDate, setNewDate] = useState('');
  const [newStart, setNewStart] = useState('');
  const [newEnd, setNewEnd] = useState('');

  const [statusModal, setStatusModal] = useState<{ bookingId: string; status: CallStatus } | null>(null);

  const fetchData = async (showLoader = false) => {
    if (showLoader) setLoading(true);
    try {
      const [s, b] = await Promise.all([
        apiSlots(`/api/slots?expert_id=${user.id}`).then(r => r.json()),
        apiBookings(`/api/bookings?role=expert&user_id=${user.id}`).then(r => r.json()),
      ]);
      setSlots(sortByDateTime(Array.isArray(s) ? s : []));
      setBookings(sortByDateTime(Array.isArray(b) ? b : []));
    } finally {
      if (showLoader) setLoading(false);
    }
  };

  const load = () => fetchData(true);

  useEffect(() => {
    fetchData(true);
  }, []);

  const createSlot = async () => {
    if (!newDate || !newStart || !newEnd) { alert('Заполните дату и время'); return; }
    const res = await apiSlots('/api/slots', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expert_id: user.id, date: newDate, start_time: newStart, end_time: newEnd }),
    });
    if (res.ok) { setNewDate(''); setNewStart(''); setNewEnd(''); load(); }
    else alert('Ошибка создания слота');
  };

  const editSlot = async (slot: Slot) => {
    const d = prompt('Новая дата (ГГГГ-ММ-ДД):', slot.date); if (!d) return;
    const s = prompt('Начало (ЧЧ:ММ):', slot.start_time); if (!s) return;
    const e = prompt('Конец (ЧЧ:ММ):', slot.end_time); if (!e) return;
    const res = await apiSlots(`/api/slots?slot_id=${slot.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expert_id: user.id, date: d, start_time: s, end_time: e }),
    });
    if (res.ok) load(); else alert('Ошибка обновления');
  };

  const deleteSlot = async (slotId: string) => {
    if (!confirm('Удалить этот слот?')) return;
    const res = await apiSlots(`/api/slots?slot_id=${slotId}&expert_id=${user.id}`, { method: 'DELETE' });
    if (res.ok) load(); else alert('Ошибка удаления');
  };

  const confirmStatusChange = async (comment: string) => {
    if (!statusModal) return;
    const res = await apiBookings('/api/bookings?action=update-status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ booking_id: statusModal.bookingId, expert_id: user.id, status: statusModal.status, comment }),
    });
    setStatusModal(null);
    if (res.ok) load(); else alert('Ошибка обновления статуса');
  };

  return (
    <div className="animate-fade-in">
      <div className="flex gap-2 mb-5 border-b border-white/10 pb-3 items-center">
        {([['slots', 'Мои слоты', 'Clock'], ['bookings', 'Записи клиентов', 'Users']] as const).map(([t, label, icon]) => (
          <button key={t} onClick={() => setTab(t)} className={`tab-item flex items-center gap-2 ${tab === t ? 'active' : ''}`}>
            <Icon name={icon as 'Home'} size={15} />
            {label}
          </button>
        ))}
        <button onClick={load} className="ml-auto btn-primary flex items-center gap-2 text-sm py-2 px-4">
          <Icon name="RefreshCw" size={14} />
          Обновить
        </button>
      </div>

      {loading && <div className="text-slate-400 text-sm py-8 text-center">Загружаем...</div>}

      {!loading && tab === 'slots' && (
        <>
          <div className="glass-card-sm p-4 mb-4">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-3 font-semibold">Добавить слот</p>
            <div className="flex flex-wrap gap-2 items-end">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Дата</label>
                <input type="date" className="form-input" value={newDate} onChange={e => setNewDate(e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Начало</label>
                <input type="time" className="form-input" value={newStart} onChange={e => setNewStart(e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Конец</label>
                <input type="time" className="form-input" value={newEnd} onChange={e => setNewEnd(e.target.value)} />
              </div>
              <button className="btn-primary flex items-center gap-1.5" onClick={createSlot}>
                <Icon name="Plus" size={15} /> Добавить
              </button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-white/5">
            <table className="data-table">
              <thead><tr><th>Дата</th><th>Время</th><th>Статус</th><th>Действия</th></tr></thead>
              <tbody>
                {slots.length === 0 && <tr><td colSpan={4} className="text-slate-500 text-center py-8">Нет слотов</td></tr>}
                {slots.map(slot => (
                  <tr key={slot.id}>
                    <td>{slot.date}</td>
                    <td className="text-slate-300">{slot.start_time} — {slot.end_time}</td>
                    <td><StatusBadge status={slot.status} /></td>
                    <td>
                      {slot.status === 'free' ? (
                        <div className="flex gap-2">
                          <button className="btn-primary btn-warning text-xs py-1 px-2.5" onClick={() => editSlot(slot)}>✏️ Ред.</button>
                          <button className="btn-primary btn-danger text-xs py-1 px-2.5" onClick={() => deleteSlot(slot.id)}>🗑</button>
                        </div>
                      ) : <span className="text-slate-600 text-xs">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!loading && tab === 'bookings' && (
        <div className="overflow-x-auto rounded-xl border border-white/5">
          <table className="data-table">
            <thead><tr>
              <th>Клиент</th><th>Телефон</th><th>Email</th><th>Дата/Время</th>
              <th>Менеджер</th><th>Статус</th><th>О клиенте</th><th>Комментарий</th><th>Изменить статус</th>
            </tr></thead>
            <tbody>
              {bookings.length === 0 && <tr><td colSpan={9} className="text-slate-500 text-center py-8">Нет записей</td></tr>}
              {bookings.map(b => (
                <tr key={b.id}>
                  <td><strong>{b.client_name}</strong></td>
                  <td className="text-slate-400">{b.client_phone || '—'}</td>
                  <td className="text-slate-400">{b.client_email || '—'}</td>
                  <td className="whitespace-nowrap">{b.date} {b.start_time}</td>
                  <td className="text-slate-400">{b.manager_name || '—'}</td>
                  <td><StatusBadge status={b.call_status} /></td>
                  <td>
                    <ClientCommentCell
                      text={b.client_comment || ''}
                      clientName={b.client_name}
                      clientPhone={b.client_phone}
                      clientEmail={b.client_email}
                      date={b.date}
                      startTime={b.start_time}
                    />
                  </td>
                  <td><CommentCell text={b.call_comment || '—'} /></td>
                  <td>
                    <select
                      className="form-input text-xs py-1"
                      value={b.call_status}
                      onChange={e => setStatusModal({ bookingId: b.id, status: e.target.value as CallStatus })}
                    >
                      {STATUSES.map(s => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {statusModal && (
        <StatusModal
          status={statusModal.status}
          onConfirm={confirmStatusChange}
          onCancel={() => setStatusModal(null)}
        />
      )}
    </div>
  );
}