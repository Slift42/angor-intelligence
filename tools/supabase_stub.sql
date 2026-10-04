-- Imitation minimale de Supabase (schéma auth, rôles anon/authenticated, auth.uid()) pour tester supabase/schema.sql
-- sur un PostgreSQL local, sans compte Supabase. Usage (voir doc/TESTS.md) :
--   psql -d test -f tools/supabase_stub.sql -f supabase/schema.sql
-- L'utilisateur « connecté » est simulé par : select set_config('request.jwt.claim.sub', '<uuid>', false);
create extension if not exists pgcrypto;
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
end $$;
create schema if not exists auth;
create table if not exists auth.users (
  id uuid primary key default gen_random_uuid(),
  email text,
  raw_user_meta_data jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  last_sign_in_at timestamptz
);
create or replace function auth.uid() returns uuid language sql stable as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;
grant usage on schema public, auth to anon, authenticated;
-- comme Supabase : toute nouvelle fonction du schéma public est exécutable par anon et authenticated
alter default privileges in schema public grant execute on functions to anon, authenticated;
grant execute on function auth.uid() to anon, authenticated;

-- Contrôle équivalent au conseiller de sécurité Supabase (à lancer après schema.sql) :
--   select p.proname, has_function_privilege('anon', p.oid, 'execute') as anon,
--          has_function_privilege('authenticated', p.oid, 'execute') as connecte, p.proconfig
--     from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--    where n.nspname = 'public' and (p.prosecdef or p.proconfig is null);
