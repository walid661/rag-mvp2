-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- 1. Create user_profiles table
create table public.user_profiles (
  user_id uuid not null references auth.users on delete cascade primary key,
  level text check (level in ('beginner', 'intermediate', 'advanced')),
  goal text,
  equipment jsonb,
  days_per_week int,
  limitations text,
  created_at timestamptz default now()
);

-- Enable RLS for user_profiles
alter table public.user_profiles enable row level security;

-- Policies for user_profiles
create policy "Users can view their own profile"
on public.user_profiles for select
using (auth.uid() = user_id);

create policy "Users can insert their own profile"
on public.user_profiles for insert
with check (auth.uid() = user_id);

create policy "Users can update their own profile"
on public.user_profiles for update
using (auth.uid() = user_id);

-- 2. Create saved_programs table
create table public.saved_programs (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid not null references auth.users on delete cascade,
  title text,
  program_data jsonb,
  status text check (status in ('active', 'completed', 'archived')) default 'active',
  created_at timestamptz default now()
);

-- Enable RLS for saved_programs
alter table public.saved_programs enable row level security;

-- Policies for saved_programs
create policy "Users can view their own programs"
on public.saved_programs for select
using (auth.uid() = user_id);

create policy "Users can insert their own programs"
on public.saved_programs for insert
with check (auth.uid() = user_id);

create policy "Users can update their own programs"
on public.saved_programs for update
using (auth.uid() = user_id);

create policy "Users can delete their own programs"
on public.saved_programs for delete
using (auth.uid() = user_id);
