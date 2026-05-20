import { useState, useRef, useEffect } from 'react';

interface Props {
  text: string;
}

export default function CommentCell({ text }: Props) {
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

  if (!text || text === '—') return <span className="text-slate-600">—</span>;

  return (
    <div className="relative inline-block" ref={ref}>
      <span
        className="text-slate-400 max-w-[140px] truncate block cursor-pointer hover:text-teal-300 transition-colors underline decoration-dotted"
        onClick={() => setOpen(v => !v)}
        title="Нажмите чтобы прочитать полностью"
      >
        {text}
      </span>
      {open && (
        <div className="absolute z-50 left-0 top-full mt-1 w-72 bg-slate-800 border border-white/15 rounded-xl shadow-2xl p-4 text-sm text-slate-200 leading-relaxed break-words">
          <div className="text-xs text-slate-500 mb-2 font-semibold uppercase tracking-wider">Комментарий</div>
          <div className="whitespace-pre-wrap select-all">{text}</div>
          <button
            className="mt-3 text-xs text-teal-400 hover:text-teal-300 transition-colors"
            onClick={() => { navigator.clipboard?.writeText(text); setOpen(false); }}
          >
            📋 Скопировать
          </button>
        </div>
      )}
    </div>
  );
}
