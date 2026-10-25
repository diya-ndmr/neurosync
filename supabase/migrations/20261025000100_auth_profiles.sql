create table if not exists public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    email text not null unique,
    full_name text not null,
    role text not null default 'student'
        check (role in ('student', 'lecturer', 'advisor', 'admin')),
    created_at timestamptz not null default now()
);

create or replace function public.create_profile_for_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.profiles (id, email, full_name)
    values (
        new.id,
        lower(new.email),
        coalesce(
            nullif(trim(new.raw_user_meta_data ->> 'full_name'), ''),
            split_part(new.email, '@', 1)
        )
    )
    on conflict (id) do update
        set email = excluded.email;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created_profile on auth.users;
create trigger on_auth_user_created_profile
    after insert or update of email on auth.users
    for each row execute function public.create_profile_for_auth_user();

insert into public.profiles (id, email, full_name)
select
    u.id,
    lower(u.email),
    coalesce(
        nullif(trim(u.raw_user_meta_data ->> 'full_name'), ''),
        split_part(u.email, '@', 1)
    )
from auth.users as u
where u.email is not null
on conflict (id) do update
    set email = excluded.email;

create or replace function public.current_user_role()
returns text
language sql
stable
security definer
set search_path = ''
as $$
    select p.role
    from public.profiles as p
    where p.id = (select auth.uid())
$$;

alter table public.profiles enable row level security;
revoke all on public.profiles from anon, authenticated;
grant select on public.profiles to authenticated;
grant execute on function public.current_user_role() to authenticated;

drop policy if exists "Users can read their own profile" on public.profiles;
create policy "Users can read their own profile"
    on public.profiles
    for select
    to authenticated
    using (
        id = (select auth.uid())
        or (select public.current_user_role()) = 'admin'
    );

revoke all on function public.create_profile_for_auth_user() from public, anon, authenticated;
