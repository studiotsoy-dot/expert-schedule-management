CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(20) NOT NULL DEFAULT 'manager',
    portfolio_url TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS slots (
    id VARCHAR(36) PRIMARY KEY,
    expert_id VARCHAR(36) NOT NULL,
    date VARCHAR(20) NOT NULL,
    start_time VARCHAR(10) NOT NULL,
    end_time VARCHAR(10) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'free'
);

CREATE TABLE IF NOT EXISTS bookings (
    id VARCHAR(36) PRIMARY KEY,
    slot_id VARCHAR(36) NOT NULL,
    manager_id VARCHAR(36) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    client_phone VARCHAR(50) DEFAULT '',
    client_email VARCHAR(255) DEFAULT '',
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    call_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    call_comment TEXT DEFAULT '',
    zoom_link TEXT DEFAULT '',
    created_at VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_slots_expert_id ON slots(expert_id);
CREATE INDEX IF NOT EXISTS idx_slots_date ON slots(date);
CREATE INDEX IF NOT EXISTS idx_bookings_slot_id ON bookings(slot_id);
CREATE INDEX IF NOT EXISTS idx_bookings_manager_id ON bookings(manager_id);
