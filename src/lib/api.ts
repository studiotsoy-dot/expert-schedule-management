const USERS_URL = 'https://functions.poehali.dev/ddf803a8-6082-4488-af70-09d8797c2545';
const SLOTS_URL = 'https://functions.poehali.dev/1d7aaabb-f9ae-43c0-b748-cc9e4e540f33';
const BOOKINGS_URL = 'https://functions.poehali.dev/cee499ed-5139-4cf0-9978-e4d793c73aa3';

export async function apiUsers(path: string, options?: RequestInit) {
  const suffix = path.replace(/^\/api\/users/, '') || '/';
  return fetch(`${USERS_URL}${suffix}`, options);
}

export async function apiSlots(path: string, options?: RequestInit) {
  const suffix = path.replace(/^\/api\/slots/, '') || '/';
  return fetch(`${SLOTS_URL}${suffix}`, options);
}

export async function apiBookings(path: string, options?: RequestInit) {
  const suffix = path.replace(/^\/api\/bookings/, '') || '/';
  return fetch(`${BOOKINGS_URL}${suffix}`, options);
}
