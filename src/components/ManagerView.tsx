import { useState, useEffect } from 'react';
import Icon from '@/components/ui/icon';
import StatusBadge from './StatusBadge';
import CommentCell from './CommentCell';
import { User, Slot, Booking } from '@/types';
import { apiSlots, apiBookings } from '@/lib/api';

interface Props { user: User; }

function sortByDateTime<T extends { date: string; start_time: string }>(arr: T[]): T[] {
  return [...arr].sort((a, b) =>
    new Date(`${a.date} ${a.start_time}`).getTime() - new Date(`${b.date} ${b.start_time}`).getTime()
  );
}

export default function ManagerView({ user }: Props) {
  const [freeSlots, setFreeSlots] = useState<Slot[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<'slots' | 'bookings'>('slots');

  const [bookModal, setBookModal] = useState<{ slot: Slot } | null>(null);
  const [clientName, setClientName] = useState('');
  const [clientPhone, setClientPhone] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [clientTelegram, setClientTelegram] = useState('');
  const [clientComment, setClientComment] = useState('');
  const [bookLoading, setBookLoading] = useState(false);

  const [rescheduleModal, setRescheduleModal] = useState<{ bookingId: string } | null>(null);
  const [rescDate, setRescDate] = useState('');
  const [rescStart, setRescStart] = useState('');
  const [rescEnd, setRescEnd] = useState('');
  const [rescLoading, setRescLoading] = useState(false);

  const fetchData = async (showLoader = false) => {
    if (showLoader) setLoading(true);
    try {
      const [s, b] = await Promise.all([
        apiSlots('/api/slots?action=free').then(r => r.json()),
        apiBookings(`/api/bookings?role=manager&user_id=${user.id}`).then(r => r.json()),
      ]);
      setFreeSlots(sortByDateTime(Array.isArray(s) ? s : []));
      setBookings(sortByDateTime(Array.isArray(b) ? b : []));
    } finally {
      if (showLoader) setLoading(false);
    }
  };

  const load = () => fetchData(true);

  useEffect(() => {
    fetchData(true);
  }, []);

  const handleBook = async () => {
    if (!bookModal || !clientName.trim()) return;
    setBookLoading(true);
    try {
      const res = await apiBookings('/api/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slot_id: bookModal.slot.id,
          manager_id: user.id,
          client_name: clientName,
          client_phone: clientPhone,
          client_email: clientEmail,
          client_telegram: clientTelegram,
          client_comment: clientComment,
        }),
      });
      if (res.ok) {
        setBookModal(null);
        setClientName(''); setClientPhone(''); setClientEmail(''); setClientTelegram(''); setClientComment('');
        load();
      } else {
        alert('Ошибка записи. Возможно, слот уже занят.');
      }
    } finally {
      setBookLoading(false);
    }
  };

  const handleReschedule = async () => {
    if (!rescheduleModal || !rescDate || !rescStart || !rescEnd) return;
    setRescLoading(true);
    try {
      const res = await apiBookings('/api/bookings?action=reschedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ booking_id: rescheduleModal.bookingId, manager_id: user.id, new_date: rescDate, new_start_time: rescStart, new_end_time: rescEnd }),
      });
      if (res.ok) {
        setRescheduleModal(null); setRescDate(''); setRescStart(''); setRescEnd('');
        load();
      } else alert('Ошибка переназначения');
    } finally {
      setRescLoading(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="flex gap-2 mb-5 border-b border-white/10 pb-3 items-center">
        {([['slots', 'Свободные слоты', 'Calendar'], ['bookings', 'Мои записи', 'ClipboardList']] as const).map(([t, label, icon]) => (
          <button key={t} onClick={() => setTab(t)} className={`tab-item flex items-center gap-2 ${tab === t ? 'active' : ''}`}>
            <Icon name={icon as 'Home'} size={15} />
            {label}
            {t === 'slots' && freeSlots.length > 0 && (
              <span className="text-xs bg-teal-400/20 text-teal-300 px-2 py-0.5 rounded-full">{freeSlots.length}</span>
            )}
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
          {freeSlots.length === 0 ? (
            <div className="text-slate-500 text-center py-10">Нет свободных слотов</div>
          ) : (
            <div className="overflow-x-auto overflow-y-auto max-h-[calc(100vh-260px)] rounded-xl border border-white/5">
              <table className="data-table">
                <thead className="sticky top-0 z-10"><tr><th>Эксперт</th><th>Дата</th><th>Время</th><th></th></tr></thead>
                <tbody>
                  {freeSlots.map(slot => (
                    <tr key={slot.id}>
                      <td>
                        {slot.expert_portfolio
                          ? <a href={slot.expert_portfolio} target="_blank" rel="noreferrer" className="text-teal-400 hover:underline font-semibold">{slot.expert_name}</a>
                          : <strong>{slot.expert_name}</strong>
                        }
                      </td>
                      <td>{slot.date}</td>
                      <td className="text-slate-300">{slot.start_time} — {slot.end_time}</td>
                      <td>
                        <button className="btn-primary text-xs py-1.5 px-3" onClick={() => setBookModal({ slot })}>
                          Записать клиента
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {!loading && tab === 'bookings' && (
        <>
          {bookings.length === 0 ? (
            <div className="text-slate-500 text-center py-10">Нет записей</div>
          ) : (
            <div className="overflow-x-auto overflow-y-auto max-h-[calc(100vh-260px)] rounded-xl border border-white/5">
              <table className="data-table">
                <thead className="sticky top-0 z-10"><tr>
                  <th>Клиент</th><th>Телефон</th><th>Email</th><th>Telegram</th><th>Эксперт</th>
                  <th>Дата/Время</th><th>Статус</th><th>Комментарий</th><th>Zoom</th><th></th>
                </tr></thead>
                <tbody>
                  {bookings.map(b => (
                    <tr key={b.id}>
                      <td><strong>{b.client_name}</strong></td>
                      <td className="text-slate-400">{b.client_phone || '—'}</td>
                      <td className="text-slate-400">{b.client_email || '—'}</td>
                      <td className="text-slate-400">{b.client_telegram ? <a href={`https://t.me/${b.client_telegram.replace('@','')}`} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline">{b.client_telegram}</a> : '—'}</td>
                      <td>
                        {b.expert_portfolio
                          ? <a href={b.expert_portfolio} target="_blank" rel="noreferrer" className="text-teal-400 hover:underline font-semibold">{b.expert_name}</a>
                          : b.expert_name}
                      </td>
                      <td className="whitespace-nowrap">{b.date} {b.start_time}</td>
                      <td><StatusBadge status={b.call_status} /></td>
                      <td><CommentCell text={b.call_comment || '—'} /></td>
                      <td>
                        {b.zoom_link ? <a href={b.zoom_link} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline text-xs">🔗 Zoom</a> : '—'}
                      </td>
                      <td>
                        {b.call_status === 'reschedule_request' && (
                          <button
                            className="btn-primary btn-info text-xs py-1 px-2 whitespace-nowrap"
                            onClick={() => { setRescheduleModal({ bookingId: b.id }); setRescDate(''); setRescStart(''); setRescEnd(''); }}
                          >
                            🔄 Перезаписать
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Reschedule modal */}
      {rescheduleModal && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="animate-fade-in bg-slate-800 border border-slate-600 rounded-2xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-1">Перенести запись</h3>
            <p className="text-slate-400 text-sm mb-4">Укажите новую дату и время</p>
            <div className="space-y-3 mb-5">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Новая дата</label>
                <input type="date" className="form-input w-full" value={rescDate} onChange={e => setRescDate(e.target.value)} />
              </div>
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-xs text-slate-500 block mb-1">Начало</label>
                  <input type="time" className="form-input w-full" value={rescStart} onChange={e => setRescStart(e.target.value)} />
                </div>
                <div className="flex-1">
                  <label className="text-xs text-slate-500 block mb-1">Конец</label>
                  <input type="time" className="form-input w-full" value={rescEnd} onChange={e => setRescEnd(e.target.value)} />
                </div>
              </div>
            </div>
            <div className="flex gap-3 justify-end">
              <button className="btn-primary btn-secondary" onClick={() => setRescheduleModal(null)}>Отмена</button>
              <button className="btn-primary" onClick={handleReschedule} disabled={rescLoading || !rescDate || !rescStart || !rescEnd}>
                {rescLoading ? 'Переносим...' : 'Перенести'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Book modal */}
      {bookModal && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="animate-fade-in bg-slate-800 border border-slate-600 rounded-2xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-1">Запись клиента</h3>
            <p className="text-slate-400 text-sm mb-4">
              {bookModal.slot.expert_name} · {bookModal.slot.date} · {bookModal.slot.start_time}–{bookModal.slot.end_time}
            </p>
            <div className="space-y-3 mb-5">
              <input className="form-input w-full" placeholder="ФИО клиента *" value={clientName} onChange={e => setClientName(e.target.value)} />
              <input className="form-input w-full" placeholder="Телефон" value={clientPhone} onChange={e => setClientPhone(e.target.value)} />
              <input type="email" className="form-input w-full" placeholder="Email клиента" value={clientEmail} onChange={e => setClientEmail(e.target.value)} />
              <input className="form-input w-full" placeholder="Telegram (@username)" value={clientTelegram} onChange={e => setClientTelegram(e.target.value)} />
              <div>
                <label className="text-xs text-slate-500 block mb-1">Комментарий о клиенте для эксперта</label>
                <textarea
                  className="form-input w-full resize-none"
                  rows={3}
                  placeholder="Кратко опишите запрос клиента, его ситуацию или пожелания..."
                  value={clientComment}
                  onChange={e => setClientComment(e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-3 justify-end">
              <button className="btn-primary btn-secondary" onClick={() => setBookModal(null)}>Отмена</button>
              <button className="btn-primary" onClick={handleBook} disabled={bookLoading || !clientName.trim()}>
                {bookLoading ? 'Записываем...' : 'Записать'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}