
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL DEFAULT 'manager',
    portfolio_url TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS slots (
    id TEXT PRIMARY KEY,
    expert_id TEXT NOT NULL,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'free'
);

CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    slot_id TEXT NOT NULL,
    manager_id TEXT NOT NULL,
    client_name TEXT NOT NULL,
    client_phone TEXT DEFAULT '',
    client_email TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    call_status TEXT NOT NULL DEFAULT 'pending',
    call_comment TEXT DEFAULT '',
    zoom_link TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);
