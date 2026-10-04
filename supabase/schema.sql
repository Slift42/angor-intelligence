-- =====================================================================================================
-- Angor Intelligence – comptes utilisateurs, validation par un administrateur, préférences, safety checks
-- Base : Supabase (PostgreSQL + Auth). À exécuter une fois dans Supabase → SQL Editor → New query → Run.
-- Principe de sécurité : chaque table est protégée par des règles « Row Level Security » (RLS) :
--   * un utilisateur ne lit et ne modifie que ses propres données ;
--   * un compte n'accède à rien tant qu'un administrateur ne l'a pas validé (status = 'approved') ;
--   * le rôle et le statut ne se changent que par la fonction admin_set_status (administrateurs seulement).
-- RGPD : données minimales (nom, organisation, e-mail, téléphone facultatif, position seulement si
-- l'utilisateur l'active), suppression du compte par l'utilisateur lui-même (delete_my_account),
-- preuve horodatée de l'acceptation des CGU et de la politique de confidentialité (legal_acceptances),
-- effacement automatique selon les durées annoncées dans docs/confidentialite.html (private.housekeeping, chaque nuit).
-- Le script peut être relancé sans risque après chaque nouvelle version (il ne supprime aucune donnée existante).
-- Sécurité (v0.19.1, conseiller de sécurité Supabase) : les fonctions à privilèges (« security definer ») sont
-- retirées de l'API publique quand c'est possible (schéma « private », non exposé), ne sont jamais exécutables sans
-- connexion (rôle anon), et toutes fixent leur search_path. Deux restent appelables par un utilisateur connecté, à
-- dessein : admin_set_status (vérifie elle-même que l'appelant est administrateur) et delete_my_account (ne supprime
-- que le compte de l'appelant) – le conseiller les signale en avertissement, c'est attendu.
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
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, email, full_name, organization)
  values (new.id, new.email, new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'organization')
  on conflict (id) do nothing;
  -- conditions acceptées dans le formulaire d'inscription : {"accepted": {"cgu": "1.0", "confidentialite": "1.0"}}
  if to_regclass('public.legal_acceptances') is not null and jsonb_typeof(new.raw_user_meta_data -> 'accepted') = 'object' then
    insert into public.legal_acceptances (user_id, doc, version)
    select new.id, k, left(v, 20) from jsonb_each_text(new.raw_user_meta_data -> 'accepted') as a(k, v)
     where k in ('cgu', 'confidentialite', 'cgv', 'dpa')
    on conflict do nothing;
  end if;
  return new;
end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();
-- fonction de déclencheur : personne n'a à l'appeler directement par l'API
revoke execute on function public.handle_new_user() from public, anon, authenticated;

create or replace function public.touch_updated_at() returns trigger language plpgsql set search_path = '' as $$
begin new.updated_at := now(); return new; end $$;
drop trigger if exists profiles_touch on public.profiles;
create trigger profiles_touch before update on public.profiles for each row execute function public.touch_updated_at();

-- fonctions d'aide des règles d'accès : dans le schéma « private », non exposé par l'API (security definer : elles
-- lisent profiles sans déclencher les règles RLS en boucle)
create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;
create or replace function private.is_admin() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.profiles where id = auth.uid() and role = 'admin' and status = 'approved')
$$;
create or replace function private.is_approved() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.profiles where id = auth.uid() and status = 'approved')
$$;
revoke execute on function private.is_admin(), private.is_approved() from public, anon;
grant execute on function private.is_admin(), private.is_approved() to authenticated;
-- versions publiques sans privilège, utilisées par les fonctions Edge (safety-push, trigger-collect)
create or replace function public.is_admin() returns boolean
language sql stable security invoker set search_path = '' as $$ select private.is_admin() $$;
create or replace function public.is_approved() returns boolean
language sql stable security invoker set search_path = '' as $$ select private.is_approved() $$;
revoke execute on function public.is_admin(), public.is_approved() from public, anon;
grant execute on function public.is_admin(), public.is_approved() to authenticated;

alter table public.profiles enable row level security;
drop policy if exists profiles_select on public.profiles;
create policy profiles_select on public.profiles for select using (id = auth.uid() or private.is_admin());
drop policy if exists profiles_update_self on public.profiles;
create policy profiles_update_self on public.profiles for update using (id = auth.uid()) with check (id = auth.uid());
-- un utilisateur ne modifie que ses champs personnels (jamais role, status, email, approved_*)
revoke update on public.profiles from authenticated, anon;
grant select on public.profiles to authenticated;
grant update (full_name, organization, job_title, phone, prefs, sites, corridors, consent_location, location)
  on public.profiles to authenticated;

-- administration : valider, refuser, suspendre, nommer administrateur
create or replace function public.admin_set_status(p_user uuid, p_status text, p_role text default null)
returns public.profiles language plpgsql security definer set search_path = '' as $$
declare r public.profiles;
begin
  if not private.is_admin() then raise exception 'réservé aux administrateurs'; end if;
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
revoke execute on function public.admin_set_status(uuid, text, text) from public, anon;
grant execute on function public.admin_set_status(uuid, text, text) to authenticated;

-- droit à l'effacement : l'utilisateur supprime lui-même son compte et toutes ses données
create or replace function public.delete_my_account() returns void
language plpgsql security definer set search_path = '' as $$
begin
  delete from auth.users where id = auth.uid();
end $$;
revoke execute on function public.delete_my_account() from public, anon;
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
create policy checks_select on public.safety_checks for select using (private.is_approved());
drop policy if exists checks_admin on public.safety_checks;
create policy checks_admin on public.safety_checks for all using (private.is_admin()) with check (private.is_admin());
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
create policy resp_select on public.safety_responses for select using (user_id = auth.uid() or private.is_admin());
drop policy if exists resp_insert on public.safety_responses;
create policy resp_insert on public.safety_responses for insert with check (user_id = auth.uid() and private.is_approved());
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
create policy push_own on public.push_subscriptions for all using (user_id = auth.uid()) with check (user_id = auth.uid() and private.is_approved());
grant select, insert, update, delete on public.push_subscriptions to authenticated;

-- ------------------------------------------------------------------ preuves d'acceptation (CGU, confidentialité, CGV)
-- Une ligne par document et par version acceptée, horodatée. Lecture : l'utilisateur (les siennes) et les administrateurs.
-- Écriture : uniquement par la fonction accept_legal (l'utilisateur ne peut ni antidater ni effacer une preuve).
create table if not exists public.legal_acceptances (
  user_id     uuid not null references public.profiles (id) on delete cascade,
  doc         text not null check (doc in ('cgu', 'confidentialite', 'cgv', 'dpa')),
  version     text not null,
  accepted_at timestamptz not null default now(),
  primary key (user_id, doc, version)
);
alter table public.legal_acceptances enable row level security;
drop policy if exists legal_select on public.legal_acceptances;
create policy legal_select on public.legal_acceptances for select using (user_id = auth.uid() or private.is_admin());
-- l'utilisateur n'insère que ses propres lignes, sans pouvoir fixer la date (accepted_at = now()), ni modifier ou effacer
drop policy if exists legal_insert on public.legal_acceptances;
create policy legal_insert on public.legal_acceptances for insert with check (user_id = auth.uid());
revoke insert, update, delete on public.legal_acceptances from public, authenticated, anon;
grant select on public.legal_acceptances to authenticated;
grant insert (user_id, doc, version) on public.legal_acceptances to authenticated;

create or replace function public.accept_legal(p_doc text, p_version text) returns void
language plpgsql security invoker set search_path = '' as $$
begin
  if auth.uid() is null then raise exception 'connexion requise'; end if;
  if p_doc not in ('cgu', 'confidentialite', 'cgv', 'dpa') then raise exception 'document inconnu'; end if;
  insert into public.legal_acceptances (user_id, doc, version) values (auth.uid(), p_doc, left(p_version, 20))
  on conflict do nothing;
end $$;
revoke execute on function public.accept_legal(text, text) from public, anon;
grant execute on function public.accept_legal(text, text) to authenticated;

-- ------------------------------------------------------------------ effacement automatique (durées de conservation)
-- Applique les durées de docs/confidentialite.html. Exécutée chaque nuit par la base elle-même (extension pg_cron,
-- disponible sur toutes les offres Supabase) ; hors API (schéma private).
drop function if exists public.housekeeping();
create or replace function private.housekeeping() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare n_checks int; n_loc int; n_pending int;
begin
  -- safety checks (et leurs réponses) : 12 mois
  delete from public.safety_checks where created_at < now() - interval '12 months';
  get diagnostics n_checks = row_count;
  -- dernière position : 30 jours sans mise à jour
  update public.profiles set location = null
   where location is not null
     and case when coalesce(location ->> 'at', '') ~ '^\d{4}-\d{2}-\d{2}'
              then (location ->> 'at')::timestamptz < now() - interval '30 days' else true end;
  get diagnostics n_loc = row_count;
  -- demandes jamais validées (en attente ou refusées) : 6 mois
  delete from auth.users u using public.profiles p
   where p.id = u.id and p.status in ('pending', 'rejected') and p.role = 'user' and p.created_at < now() - interval '6 months';
  get diagnostics n_pending = row_count;
  return jsonb_build_object('checks', n_checks, 'locations', n_loc, 'pending_accounts', n_pending, 'at', now());
end $$;
revoke execute on function private.housekeeping() from public, anon, authenticated;
do $$
begin
  if exists (select 1 from pg_available_extensions where name = 'pg_cron') then
    create extension if not exists pg_cron with schema pg_catalog;
    perform cron.schedule('angor-housekeeping', '17 3 * * *', 'select private.housekeeping()');
  else
    raise notice 'pg_cron absent : lancez « select private.housekeeping(); » de temps en temps';
  end if;
exception when others then
  raise notice 'Planification de l''entretien impossible (%) : Database → Extensions → activer pg_cron, puis relancer ce script', sqlerrm;
end $$;

-- signe de vie appelé par le robot de collecte toutes les 30 minutes : empêche la mise en pause du projet gratuit
-- (7 jours sans activité). Sans privilège, ne lit ni n'écrit aucune donnée.
create or replace function public.ping() returns timestamptz
language sql stable security invoker set search_path = '' as $$ select now() $$;
grant execute on function public.ping() to anon, authenticated;

-- ------------------------------------------------------------------ premier administrateur
-- Après avoir créé votre compte depuis angor.fr/compte.html, exécutez UNE fois (avec votre e-mail) :
--   update public.profiles set role = 'admin', status = 'approved', approved_at = now()
--    where email = 'votre-adresse@exemple.fr';
