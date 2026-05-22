export type UserRole = 'manager' | 'expert' | 'admin';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  is_active?: boolean;
  portfolio_url?: string;
}

export type CallStatus =
  | 'pending'
  | 'confirmed'
  | 'success'
  | 'cancelled_by_client'
  | 'cancelled_by_expert'
  | 'failed'
  | 'reschedule_request';

export type SlotStatus = 'free' | 'booked';

export interface Slot {
  id: string;
  expert_id: string;
  expert_name: string;
  expert_email?: string;
  expert_portfolio?: string;
  date: string;
  start_time: string;
  end_time: string;
  status: SlotStatus;
  booking?: Booking;
}

export interface Booking {
  id: string;
  slot_id: string;
  manager_id: string;
  manager_name?: string;
  expert_id?: string;
  expert_name?: string;
  expert_email?: string;
  expert_portfolio?: string;
  client_name: string;
  client_phone?: string;
  client_email?: string;
  date: string;
  start_time: string;
  end_time?: string;
  zoom_link?: string;
  call_status: CallStatus;
  call_comment?: string;
  client_comment?: string;
}

export const STATUS_LABELS: Record<string, string> = {
  free: 'Свободен',
  booked: 'Занят',
  pending: 'Ожидает',
  confirmed: 'Подтверждён',
  success: 'Успешный',
  cancelled_by_client: 'Отменён клиентом',
  cancelled_by_expert: 'Отменён экспертом',
  failed: 'Неуспешный',
  reschedule_request: 'Просьба перенести',
};

export const STATUS_COLORS: Record<string, string> = {
  free: 'bg-blue-500 text-white',
  booked: 'bg-violet-500 text-white',
  pending: 'bg-amber-500 text-slate-900',
  confirmed: 'bg-emerald-500 text-white',
  success: 'bg-cyan-500 text-white',
  cancelled_by_client: 'bg-red-500 text-white',
  cancelled_by_expert: 'bg-orange-500 text-white',
  failed: 'bg-purple-600 text-white',
  reschedule_request: 'bg-pink-500 text-white',
};

export const ADMIN_EMAIL = 'studiotsoy@gmail.com';