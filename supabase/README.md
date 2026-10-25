# Supabase deployment

Supabase hosts authentication, PostgreSQL, and Edge Functions. Netlify hosts the
frontend. The current Python API is not executable in Supabase SQL Editor; its
remaining routes and data workflows must be ported to Edge Functions/SQL before
the complete application can run without an API host.

## Apply the auth profile schema

Install the Supabase CLI, then from the repository root run:

```powershell
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

This applies `migrations/20261025000100_auth_profiles.sql`. It creates a
`public.profiles` row when an Auth user is created. New users receive the
least-privileged `student` role by default. Passwords remain in Supabase Auth;
they are never stored in `profiles`.

## Create the first administrator

In Supabase **Authentication → Users**, create the administrator account and
confirm its email. In **SQL Editor**, replace the email below with that exact
account email and run:

```sql
update public.profiles
set role = 'admin'
where lower(email) = lower('admin@example.com');
```

Confirm the editor reports one updated row. Do not set a password in SQL.

## Deploy account invitations

The Edge Function `invite-user` lets an administrator invite students,
lecturers, and advisors. Configure its frontend URL, then deploy it:

```powershell
supabase secrets set FRONTEND_URL=https://YOUR-SITE.netlify.app
supabase functions deploy invite-user
```

Supabase supplies `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and
`SUPABASE_SERVICE_ROLE_KEY` to the function. Never put the service-role key in
Netlify or browser code. Set the Netlify build variables
`VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`, then redeploy the site.
Configure the Netlify URL under **Authentication → URL Configuration**, and
configure SMTP if invite emails must go to addresses outside the Supabase
project team.

## Remaining application migration

This is the auth/profile foundation, not the full API replacement. The existing
UI still calls the former Python API for dashboard data and workflows. Those
routes, database tables, imports, and prediction features need corresponding
Supabase Edge Functions/SQL migrations before all screens work with no API
server.
