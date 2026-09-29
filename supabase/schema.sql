-- =====================================================================================================
-- Angor Intelligence – comptes utilisateurs, validation par un administrateur, préférences, safety checks
-- Base : Supabase (PostgreSQL + Auth). À exécuter une fois dans Supabase → SQL Editor → New query → Run.
-- Principe de sécurité : chaque table est protégée par des règles « Row Level Security » (RLS) :
--   * un utilisateur ne lit et ne modifie que ses propres données ;
--   * un compte n'accède à rien tant qu'un administrateur ne l'a pas validé (status = 'approved') ;
--   * le rôle et le statut ne se changent que par la fonction admin_set_status (administrateurs seulement).
-- RGPD : données minimales (nom, organisation, e-mail, téléphone facultatif, position seulement si
-- l'utilisateur l'active), suppression du compte par l'utilisateur lui-même (delete_my_account).
-- =====================================================================================================

create extension if not exists pgcrypto;

-- ------------------------------------------------------------------ profils
create table if not exists public.profiles (
  id               uuid primary key references auth.users (id) on delete cascade,
  email            text not null,
  full_name        text,
  organization     text,
  job_title        text,
  phone            text,
  role             text not null default 'user'    check (role in ('user', 'admin')),
  status           text not null default 'pending' check (status in ('pending', 'approved', 'rejected', 'suspended')),
  prefs            jsonb not null default '{}'::jsonb,   -- langue, thème, pays suivis, pays de résidence, alertes…
  sites            jsonb not null default '[]'::jsonb,   -- sites surveillés
  corridors        jsonb not null default '[]'::jsonb,   -- trajets surveillés
  consent_location boolean not null default false,       -- partage volontaire de la position (safety check)
  location         jsonb,                                  -- {"lat":..,"lon":..,"iso":"FR","at":"2026-…"}
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  approved_at      timestamptz,
  approved_by      uuid
);

-- profil créé automatiquement à l'inscription (nom et organisation saisis dans le formulaire)
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, full_name, organization)
  values (new.id, new.email, new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'organization')
  on conflict (id) do nothing;
  return new;
end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

create or replace function public.touch_updated_at() returns trigger language plpgsql as $$
begin new.updated_at := now(); return new; end $$;
drop trigger if exists profiles_touch on public.profiles;
create trigger profiles_touch before update on public.profiles for each row execute function public.touch_updated_at();

-- fonctions d'aide (security definer : elles lisent profiles sans déclencher les règles RLS en boucle)
create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = auth.uid() and role = 'admin' and status = 'approved')
$$;
create or replace function public.is_approved() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = auth.uid() and status = 'approved')
$$;

alter table public.profiles enable row level security;
drop policy if exists profiles_select on public.profiles;
create policy profiles_select on public.profiles for select using (id = auth.uid() or public.is_admin());
drop policy if exists profiles_update_self on public.profiles;
create policy profiles_update_self on public.profiles for update using (id = auth.uid()) with check (id = auth.uid());
-- un utilisateur ne modifie que ses champs personnels (jamais role, status, email, approved_*)
revoke update on public.profiles from authenticated, anon;
grant select on public.profiles to authenticated;
grant update (full_name, organization, job_title, phone, prefs, sites, corridors, consent_location, location)
  on public.profiles to authenticated;

-- administration : valider, refuser, suspendre, nommer administrateur
create or replace function public.admin_set_status(p_user uuid, p_status text, p_role text default null)
returns public.profiles language plpgsql security definer set search_path = public as $$
declare r public.profiles;
begin
  if not public.is_admin() then raise exception 'réservé aux administrateurs'; end if;
  if p_status not in ('pending', 'approved', 'rejected', 'suspended') then raise exception 'statut inconnu'; end if;
  if p_role is not null and p_role not in ('user', 'admin') then raise exception 'rôle inconnu'; end if;
  if p_user = auth.uid() and (p_status <> 'approved' or p_role = 'user') then
    raise exception 'un administrateur ne peut pas se retirer ses propres droits';
  end if;
  update public.profiles set status = p_status, role = coalesce(p_role, role),
         approved_at = case when p_status = 'approved' then now() else approved_at end,
         approved_by = case when p_status = 'approved' then auth.uid() else approved_by end
   where id = p_user returning * into r;
  return r;
end $$;
grant execute on function public.admin_set_status(uuid, text, text) to authenticated;

-- droit à l'effacement : l'utilisateur supprime lui-même son compte et toutes ses données
create or replace function public.delete_my_account() returns void
language plpgsql security definer set search_path = public, auth as $$
begin
  delete from auth.users where id = auth.uid();
end $$;
grant execute on function public.delete_my_account() to authenticated;

-- ------------------------------------------------------------------ safety checks
create table if not exists public.safety_checks (
  id           uuid primary key default gen_random_uuid(),
  created_by   uuid references public.profiles (id) on delete set null,
  title        text not null,
  message      text,
  -- zone ciblée : {"type":"all"} | {"type":"country","iso":"ML"} | {"type":"circle","lat":..,"lon":..,"radius_km":50,"label":"Bamako"}
  area         jsonb not null default '{"type":"all"}'::jsonb,
  organization text,                     -- facultatif : seulement les utilisateurs de cette organisation
  event_id     text,                     -- incident Angor à l'origine (facultatif)
  status       text not null default 'open' check (status in ('open', 'closed')),
  created_at   timestamptz not null default now(),
  expires_at   timestamptz not null default now() + interval '24 hours'
);
alter table public.safety_checks enable row level security;
drop policy if exists checks_select on public.safety_checks;
create policy checks_select on public.safety_checks for select using (public.is_approved());
drop policy if exists checks_admin on public.safety_checks;
create policy checks_admin on public.safety_checks for all using (public.is_admin()) with check (public.is_admin());
grant select, insert, update, delete on public.safety_checks to authenticated;

create table if not exists public.safety_responses (
  check_id    uuid not null references public.safety_checks (id) on delete cascade,
  user_id     uuid not null references public.profiles (id) on delete cascade,
  status      text not null check (status in ('safe', 'help', 'not_concerned')),
  note        text,
  lat         double precision,          -- seulement si l'utilisateur a accepté de partager sa position
  lon         double precision,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  primary key (check_id, user_id)
);
alter table public.safety_responses enable row level security;
drop policy if exists resp_select on public.safety_responses;
create policy resp_select on public.safety_responses for select using (user_id = auth.uid() or public.is_admin());
drop policy if exists resp_insert on public.safety_responses;
create policy resp_insert on public.safety_responses for insert with check (user_id = auth.uid() and public.is_approved());
drop policy if exists resp_update on public.safety_responses;
create policy resp_update on public.safety_responses for update using (user_id = auth.uid()) with check (user_id = auth.uid());
grant select, insert, update on public.safety_responses to authenticated;
drop trigger if exists responses_touch on public.safety_responses;
create trigger responses_touch before update on public.safety_responses for each row execute function public.touch_updated_at();

-- ------------------------------------------------------------------ notifications (Web Push)
create table if not exists public.push_subscriptions (
  endpoint    text primary key,
  user_id     uuid not null references public.profiles (id) on delete cascade,
  p256dh      text not null,
  auth        text not null,
  user_agent  text,
  created_at  timestamptz not null default now()
);
alter table public.push_subscriptions enable row level security;
drop policy if exists push_own on public.push_subscriptions;
create policy push_own on public.push_subscriptions for all using (user_id = auth.uid()) with check (user_id = auth.uid() and public.is_approved());
grant select, insert, update, delete on public.push_subscriptions to authenticated;

-- ------------------------------------------------------------------ premier administrateur
-- Après avoir créé votre compte depuis angor.fr/compte.html, exécutez UNE fois (avec votre e-mail) :
--   update public.profiles set role = 'admin', status = 'approved', approved_at = now()
--    where email = 'votre-adresse@exemple.fr';
