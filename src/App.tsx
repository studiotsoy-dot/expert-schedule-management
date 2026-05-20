import { useState, useEffect } from 'react';
import Icon from '@/components/ui/icon';
import AuthPanel from '@/components/AuthPanel';
import ManagerView from '@/components/ManagerView';
import ExpertView from '@/components/ExpertView';
import AdminView from '@/components/AdminView';
import { User, UserRole, ADMIN_EMAIL } from '@/types';
import { apiUsers } from '@/lib/api';

const STORAGE_KEY = 'asm_scheduler_user';

const ROLE_LABELS: Record<UserRole, string> = {
  manager: '📋 Менеджер',
  expert: '🎯 Эксперт',
  admin: '👑 Администратор',
};

export default function App() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try { setUser(JSON.parse(saved)); } catch { /* ignore */ }
    }
  }, []);

  const handleLogin = async (name: string, email: string, role: UserRole) => {
    if (role === 'admin' && email !== ADMIN_EMAIL) {
      throw new Error('Роль Администратора доступна только для studiotsoy@gmail.com');
    }
    const res = await apiUsers('/api/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, role }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Ошибка регистрации');
    }
    const userData: User = await res.json();
    setUser(userData);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(userData));
  };

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
  };

  if (!user) {
    return <AuthPanel onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="glass-card px-5 py-4 mb-5 flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-400 to-sky-400 flex items-center justify-center flex-shrink-0">
              <Icon name="CalendarDays" size={20} className="text-slate-900" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-bold gradient-text leading-tight truncate">
                Расписание экспертов АСМ
              </h1>
              <p className="text-slate-400 text-xs">Система управления</p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="text-right hidden sm:block">
              <div className="text-sm font-semibold text-slate-200">{user.name}</div>
              <div className="text-xs text-teal-400">{ROLE_LABELS[user.role]}</div>
            </div>
            <div className="w-9 h-9 rounded-full bg-teal-400/20 border border-teal-400/30 flex items-center justify-center text-teal-300 font-bold text-sm">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <button
              onClick={handleLogout}
              className="btn-primary btn-secondary flex items-center gap-1.5 text-sm py-2 px-3"
            >
              <Icon name="LogOut" size={14} />
              <span className="hidden sm:inline">Выйти</span>
            </button>
          </div>
        </div>

        {/* Dashboard */}
        <div className="glass-card-sm p-5">
          {user.role === 'manager' && <ManagerView user={user} />}
          {user.role === 'expert' && <ExpertView user={user} />}
          {user.role === 'admin' && <AdminView user={user} />}
        </div>

        {/* Footer */}
        <div className="text-center mt-6 pb-2">
          <a
            href="https://t.me/StudioTSV"
            target="_blank"
            rel="noreferrer"
            className="text-slate-600 hover:text-teal-400 transition-colors text-xs"
          >
            Разработано STUDIO TSOY
          </a>
        </div>
      </div>
    </div>
  );
}