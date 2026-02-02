-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Table: blacklist
create table blacklist (
  phone_number text primary key,
  reason text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Table: users
create table users (
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

-- Table: requests
create table requests (
  id uuid primary key default uuid_generate_v4(),
  requester_id bigint references users(telegram_id) not null,
  blood_type text,
  location text,
  urgency text check (urgency in ('High', 'Normal')),
  is_active boolean default true,
  donors_found int default 0,
  telegram_message_id bigint,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Indexes for performance
create index idx_requests_is_active on requests(is_active);
create index idx_users_phone_number on users(phone_number);
create index idx_users_blood_type on users(blood_type);
