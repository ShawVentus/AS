-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Users Table (Simple public users for MVP, distinct from auth.users)
create table if not exists users (
    id text default uuid_generate_v4()::text primary key,
    email text unique not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Papers Table
create table if not exists papers (
    id text primary key,
    title text not null,
    authors text[] not null,
    date text not null,
    category text not null,
    tldr text,
    suggestion text,
    tags text[],
    details jsonb default '{}'::jsonb,
    links jsonb default '{}'::jsonb,
    "citationCount" integer default 0,
    year integer,
    "isLiked" boolean,
    "whyThisPaper" text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Reports Table
create table if not exists reports (
    id text primary key,
    user_id text references users(id), -- Added user_id
    title text not null,
    date text not null,
    summary text,
    content jsonb default '[]'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- User Profiles Table (Simplified for single user demo, or keyed by user_id)
create table if not exists profiles (
    user_id text primary key,
    info jsonb default '{}'::jsonb,
    focus jsonb default '{}'::jsonb,
    context jsonb default '{}'::jsonb,
    memory jsonb default '{}'::jsonb,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Interactions Table (Optional, for analytics)
create table if not exists interactions (
    id uuid default uuid_generate_v4() primary key,
    user_id text not null,
    paper_id text references papers(id),
    action text not null, -- 'like', 'dislike', 'read'
    meta jsonb default '{}'::jsonb, -- reason, tags
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS Policies
-- Papers
alter table papers enable row level security;
drop policy if exists "Public papers are viewable by everyone" on papers;
create policy "Public papers are viewable by everyone" on papers for select using (true);
drop policy if exists "Public papers are insertable by service role" on papers;
create policy "Public papers are insertable by service role" on papers for insert with check (true);
drop policy if exists "Public papers are updatable by service role" on papers;
create policy "Public papers are updatable by service role" on papers for update using (true);

-- Reports
alter table reports enable row level security;
drop policy if exists "Public reports are viewable by everyone" on reports;
create policy "Public reports are viewable by everyone" on reports for select using (true);
drop policy if exists "Public reports are insertable by service role" on reports;
create policy "Public reports are insertable by service role" on reports for insert with check (true);

-- Profiles
alter table profiles enable row level security;
drop policy if exists "Users can view own profile" on profiles;
create policy "Users can view own profile" on profiles for select using (auth.uid()::text = user_id);
drop policy if exists "Users can update own profile" on profiles;
create policy "Users can update own profile" on profiles for update using (auth.uid()::text = user_id);
-- For dev simplicity, allow all for now if auth is not fully set up
drop policy if exists "Allow all access for dev" on profiles;
create policy "Allow all access for dev" on profiles for all using (true);

-- Users
alter table users enable row level security;
drop policy if exists "Allow all access for users dev" on users;
create policy "Allow all access for users dev" on users for all using (true);
