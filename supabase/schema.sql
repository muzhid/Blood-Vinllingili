-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Table: villingili_blacklist
create table villingili_blacklist (
  phone_number text primary key,
  reason text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Table: villingili_users
create table villingili_users (
  telegram_id bigint primary key,
  full_name text not null,
  phone_number text unique not null,
  alternate_phones text, -- Comma-separated string
  blood_type text,
  sex text,
  id_card_number text,
  address text,
  role text default 'user' check (role in ('user', 'admin', 'super_admin')),
  status text default 'active' check (status in ('active', 'pending', 'banned')),
  last_donation_date date,
  username text,
  pending_request_id uuid,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Table: villingili_requests
create table villingili_requests (
  id uuid primary key default uuid_generate_v4(),
  requester_id bigint references villingili_users(telegram_id) not null,
  blood_type text,
  location text,
  urgency text check (urgency in ('High', 'Normal')),
  is_active boolean default true,
  donors_found int default 0,
  telegram_message_id bigint,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Indexes for performance
create index idx_villingili_requests_is_active on villingili_requests(is_active);
create index idx_villingili_users_phone_number on villingili_users(phone_number);
create index idx_villingili_users_blood_type on villingili_users(blood_type);
