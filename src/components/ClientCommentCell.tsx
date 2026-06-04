import { useState, useRef, useEffect } from 'react';
import Icon from '@/components/ui/icon';

interface Props {
  text: string;
  clientName?: string;
  clientPhone?: string;
  clientEmail?: string;
  clientTelegram?: string;
  date?: string;
  startTime?: string;
}

export default function ClientCommentCell({ text, clientName = '', clientPhone = '', clientEmail = '', clientTelegram = '', date = '', startTime = '' }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const download = () => {
    const content = [
      `Клиент: ${clientName}`,
      `Телефон: ${clientPhone || '—'}`,
      `Email: ${clientEmail || '—'}`,
      `Telegram: ${clientTelegram || '—'}`,
      `Дата: ${date} ${startTime}`,
      '',
      'Комментарий менеджера:',
      text,
    ].join('\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `client_${(clientName || 'comment').replace(/\s+/g, '_')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!text) return <span className="text-slate-600">—</span>;

  return (
    <div className="relative inline-block" ref={ref}>
      <span
        className="text-slate-400 max-w-[140px] truncate block cursor-pointer hover:text-amber-300 transition-colors underline decoration-dotted"
        onClick={() => setOpen(v => !v)}
        title="Нажмите чтобы прочитать полностью"
      >
        {text}
      </span>
      {open && (
        <div className="absolute z-50 left-0 top-full mt-1 w-80 bg-slate-800 border border-amber-400/20 rounded-xl shadow-2xl p-4 text-sm text-slate-200 leading-relaxed break-words">
          <div className="text-xs text-amber-400 mb-2 font-semibold uppercase tracking-wider">О клиенте</div>
          <div className="whitespace-pre-wrap select-all mb-4">{text}</div>
          <div className="flex gap-2">
            <button
              className="flex items-center gap-1.5 text-xs text-teal-400 hover:text-teal-300 transition-colors"
              onClick={download}
            >
              <Icon name="Download" size={13} /> Скачать
            </button>
            <button
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-300 transition-colors"
              onClick={() => { navigator.clipboard?.writeText(text); setOpen(false); }}
            >
              <Icon name="Copy" size={13} /> Скопировать
            </button>
          </div>
        </div>
      )}
    </div>
  );
}