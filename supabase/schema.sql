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
-- type de compte (v0.20) : client (organisation ou particulier) ou prestataire de services aux voyageurs.
-- Choisi à l'inscription ; l'utilisateur ne peut pas le modifier (absent des colonnes modifiables), l'administrateur si.
alter table public.profiles add column if not exists account_type text not null default 'client';
alter table public.profiles drop constraint if exists profiles_account_type_check;
alter table public.profiles add constraint profiles_account_type_check check (account_type in ('client', 'provider'));

-- profil créé automatiquement à l'inscription (nom et organisation saisis dans le formulaire)
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, email, full_name, organization, account_type)
  values (new.id, new.email, new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'organization',
          case when new.raw_user_meta_data ->> 'account_type' = 'provider' then 'provider' else 'client' end)
  on conflict (id) do nothing;
  -- conditions acceptées dans le formulaire d'inscription : {"accepted": {"cgu": "1.0", "confidentialite": "1.0"}}
  if to_regclass('public.legal_acceptances') is not null and jsonb_typeof(new.raw_user_meta_data -> 'accepted') = 'object' then
    insert into public.legal_acceptances (user_id, doc, version)
    select new.id, k, left(v, 20) from jsonb_each_text(new.raw_user_meta_data -> 'accepted') as a(k, v)
     where k in ('cgu', 'confidentialite', 'cgv', 'dpa', 'annuaire')
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
create or replace function private.is_provider() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.profiles where id = auth.uid() and account_type = 'provider')
$$;
create or replace function private.is_client() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.profiles where id = auth.uid() and account_type = 'client' and status = 'approved')
$$;
revoke execute on function private.is_provider(), private.is_client() from public, anon;
grant execute on function private.is_provider(), private.is_client() to authenticated;
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
  doc         text not null,
  version     text not null,
  accepted_at timestamptz not null default now(),
  primary key (user_id, doc, version)
);
alter table public.legal_acceptances drop constraint if exists legal_acceptances_doc_check;
alter table public.legal_acceptances add constraint legal_acceptances_doc_check
  check (doc in ('cgu', 'confidentialite', 'cgv', 'dpa', 'annuaire'));
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
  if p_doc not in ('cgu', 'confidentialite', 'cgv', 'dpa', 'annuaire') then raise exception 'document inconnu'; end if;
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
  -- avis et demandes de devis des prestataires : 3 ans (tables v0.20, si elles existent)
  if to_regclass('public.provider_reviews') is not null then
    delete from public.provider_reviews where created_at < now() - interval '3 years';
    delete from public.provider_requests where created_at < now() - interval '3 years';
  end if;
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

-- ------------------------------------------------------------------ annuaire des prestataires (v0.20)
-- Fiche d'identification et de services remplie par le prestataire lui-même (compte de type « provider »).
-- Visibilité : brouillon = le prestataire seul ; « submitted » (soumise) et « verified » (vérifiée par Angor) = annuaire.
-- Le public (clé anon, utilisée par le robot pour l'annuaire de la carte) ne lit que le nom, les catégories, les pays,
-- le site web et le niveau de fiabilité ; contacts, tarifs, garanties et avis sont réservés aux comptes validés.
-- Aucun classement payant : niveau (A à D) et score (0 à 100) sont calculés par la base à partir de la qualité des
-- informations fournies (voir private.provider_score, et docs/providers-lib.js pour la même grille côté écran).
create table if not exists public.providers (
  id              uuid primary key default gen_random_uuid(),
  owner_id        uuid references public.profiles (id) on delete cascade,
  status          text not null default 'draft' check (status in ('draft', 'submitted', 'verified', 'suspended')),
  name            text not null check (length(name) between 2 and 120),
  legal_name      text,
  registration_no text,                 -- n° d'immatriculation (SIREN, Companies House…)
  hq_country      text,                 -- ISO2 du siège
  founded         int,
  description_fr  text check (length(description_fr) <= 4000),
  description_en  text check (length(description_en) <= 4000),
  categories      text[] not null default '{}',   -- codes de config/providers.json
  countries       text[] not null default '{}',   -- ISO2 couverts
  cities          text,
  website         text,
  linkedin        text,
  links           jsonb not null default '[]'::jsonb,  -- [{"label": "…", "url": "…"}]
  contacts        jsonb not null default '{}'::jsonb,  -- {"phone_247","email_ops","email_booking","phone_booking","languages":[],"response_time"}
  pricing         jsonb not null default '[]'::jsonb,  -- [{"category","label","price","currency","unit","conditions"}]
  guarantees      jsonb not null default '{}'::jsonb,  -- {"insurer","insurance_amount","insurance_expiry","licences":[],"certifications":[]}
  media           jsonb not null default '[]'::jsonb,  -- [{"type":"photo","path"} | {"type":"video","url"}, "caption"]
  public_listing  boolean not null default true,
  score           int not null default 0,
  tier            text not null default 'D',
  verified_at     timestamptz,
  verified_by     uuid,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create unique index if not exists providers_one_per_owner on public.providers (owner_id);

create table if not exists public.provider_documents (
  id          uuid primary key default gen_random_uuid(),
  provider_id uuid not null references public.providers (id) on delete cascade,
  kind        text not null,             -- voir la contrainte provider_documents_kind_check ci-dessous
  label       text,
  path        text not null,             -- fichier dans le compartiment privé « provider-docs »
  expires_on  date,
  status      text not null default 'pending' check (status in ('pending', 'validated', 'rejected')),
  note        text,                      -- remarque d'Angor (motif de refus…)
  uploaded_at timestamptz not null default now(),
  reviewed_at timestamptz
);

-- types de justificatifs (v0.21 : CV des équipes clés et attestation fiscale/sociale) – liste identique à DOC_KINDS
-- dans docs/providers-lib.js
alter table public.provider_documents drop constraint if exists provider_documents_kind_check;
alter table public.provider_documents add constraint provider_documents_kind_check
  check (kind in ('registration', 'licence', 'insurance', 'certification', 'cv', 'tax', 'other'));

-- Un justificatif compte s'il n'est pas refusé et pas expiré ; l'attestation d'assurance doit porter une date de fin.
create or replace function private.doc_active(d public.provider_documents) returns boolean
language sql stable set search_path = '' as $$
  select d.status <> 'rejected' and case when d.expires_on is not null then d.expires_on >= current_date else d.kind <> 'insurance' end
$$;
revoke execute on function private.doc_active(public.provider_documents) from public, anon, authenticated;

-- Grille de qualité (sur 100) – identique à docs/providers-lib.js (test : tests/test_providers.py)
-- POIDS: ident=10 desc=5 scope=5 contact=10 pricing=5 media=5 links=5 doc_reg=15 doc_lic=10 doc_ins=10 doc_cert=5 doc_cv=5 docs_ok=10
-- (v0.21 : les justificatifs pèsent 55 points sur 100 ; sans eux, une fiche plafonne à 45 et reste au niveau D)
create or replace function private.provider_score(p public.providers) returns int
language plpgsql stable security definer set search_path = '' as $$
declare s int := 0; kinds text[]; n_ok int; reg_ok boolean;
begin
  select coalesce(array_agg(distinct d.kind), '{}'),
         count(*) filter (where d.status = 'validated'),
         coalesce(bool_or(d.kind = 'registration' and d.status = 'validated'), false)
    into kinds, n_ok, reg_ok
    from public.provider_documents d where d.provider_id = p.id and private.doc_active(d);
  if coalesce(p.legal_name, '') <> '' and coalesce(p.registration_no, '') <> '' and coalesce(p.hq_country, '') <> '' then s := s + 10; end if;
  if greatest(length(coalesce(p.description_fr, '')), length(coalesce(p.description_en, ''))) >= 200 then s := s + 5; end if;
  if cardinality(p.categories) >= 1 and cardinality(p.countries) >= 1 then s := s + 5; end if;
  if coalesce(p.contacts ->> 'phone_247', '') <> ''
     and (coalesce(p.contacts ->> 'email_ops', '') <> '' or coalesce(p.contacts ->> 'email_booking', '') <> '') then s := s + 10; end if;
  if exists (select 1 from jsonb_array_elements(case when jsonb_typeof(p.pricing) = 'array' then p.pricing else '[]'::jsonb end) e
              where coalesce(e ->> 'price', '') <> '') then s := s + 5; end if;
  if jsonb_array_length(case when jsonb_typeof(p.media) = 'array' then p.media else '[]'::jsonb end) >= 1 then s := s + 5; end if;
  if coalesce(p.website, '') <> '' or coalesce(p.linkedin, '') <> '' then s := s + 5; end if;
  if 'registration' = any (kinds) then s := s + 15; end if;
  if 'licence' = any (kinds) then s := s + 10; end if;
  if 'insurance' = any (kinds) then s := s + 10; end if;
  if 'certification' = any (kinds) then s := s + 5; end if;
  if 'cv' = any (kinds) then s := s + 5; end if;
  if reg_ok and n_ok >= 2 then s := s + 10; end if;
  return s;
end $$;
revoke execute on function private.provider_score(public.providers) from public, anon, authenticated;

-- Avant chaque écriture : score et niveau recalculés ; le prestataire ne peut ni se vérifier lui-même, ni changer de
-- propriétaire ; seul un administrateur passe une fiche en « verified » ou « suspended ».
create or replace function private.providers_guard() returns trigger
language plpgsql security definer set search_path = '' as $$
declare adm boolean := private.is_admin();
begin
  if tg_op = 'UPDATE' and not adm then
    new.owner_id := old.owner_id; new.verified_at := old.verified_at; new.verified_by := old.verified_by;
    if new.status is distinct from old.status
       and not (old.status in ('draft', 'submitted') and new.status in ('draft', 'submitted')) then
      raise exception 'statut réservé à l''administration';
    end if;
  end if;
  if tg_op = 'INSERT' and not adm and new.status not in ('draft', 'submitted') then new.status := 'draft'; end if;
  -- justificatifs obligatoires : immatriculation envoyée pour soumettre, validée par Angor pour vérifier
  if new.status = 'submitted' and (tg_op = 'INSERT' or old.status is distinct from 'submitted')
     and not exists (select 1 from public.provider_documents d
                     where d.provider_id = new.id and d.kind = 'registration' and private.doc_active(d)) then
    raise exception 'Ajoutez d''abord votre extrait d''immatriculation (rubrique Justificatifs) pour soumettre la fiche.';
  end if;
  if new.status = 'verified' and (tg_op = 'INSERT' or old.status is distinct from 'verified')
     and not exists (select 1 from public.provider_documents d
                     where d.provider_id = new.id and d.kind = 'registration' and d.status = 'validated' and private.doc_active(d)) then
    raise exception 'Vérification impossible : validez d''abord l''extrait d''immatriculation du prestataire.';
  end if;
  if adm and new.status = 'verified' and (tg_op = 'INSERT' or old.status is distinct from 'verified') then
    new.verified_at := now(); new.verified_by := auth.uid();
  end if;
  new.score := private.provider_score(new);
  new.tier := case when new.status = 'verified' and new.score >= 80 then 'A'
                   when new.status = 'verified' then 'B'
                   when new.status = 'submitted' and new.score >= 60 then 'C'
                   else 'D' end;
  new.updated_at := now();
  return new;
end $$;
revoke execute on function private.providers_guard() from public, anon, authenticated;
drop trigger if exists providers_guard on public.providers;
create trigger providers_guard before insert or update on public.providers for each row execute function private.providers_guard();

-- un document ajouté, validé ou supprimé fait recalculer le score de la fiche
create or replace function private.provider_docs_touch() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  update public.providers set updated_at = now() where id = coalesce(new.provider_id, old.provider_id);
  return null;
end $$;
revoke execute on function private.provider_docs_touch() from public, anon, authenticated;
drop trigger if exists provider_docs_touch on public.provider_documents;
create trigger provider_docs_touch after insert or update or delete on public.provider_documents
  for each row execute function private.provider_docs_touch();
-- recalcul des scores existants (nouvelle grille v0.21) – sans effet si la table est vide
update public.providers set updated_at = now();

alter table public.providers enable row level security;
drop policy if exists providers_public on public.providers;
create policy providers_public on public.providers for select to anon
  using (status in ('submitted', 'verified') and public_listing);
drop policy if exists providers_select on public.providers;
create policy providers_select on public.providers for select to authenticated
  using (owner_id = auth.uid() or private.is_admin()
         or (private.is_approved() and status in ('submitted', 'verified') and public_listing));
drop policy if exists providers_insert on public.providers;
create policy providers_insert on public.providers for insert to authenticated
  with check ((owner_id = auth.uid() and private.is_provider()) or private.is_admin());
drop policy if exists providers_update on public.providers;
create policy providers_update on public.providers for update to authenticated
  using (owner_id = auth.uid() or private.is_admin()) with check (owner_id = auth.uid() or private.is_admin());
drop policy if exists providers_delete on public.providers;
create policy providers_delete on public.providers for delete to authenticated
  using (owner_id = auth.uid() or private.is_admin());
revoke all on public.providers from anon, authenticated;
grant select (id, name, categories, countries, hq_country, website, tier, score, status, public_listing, updated_at)
  on public.providers to anon;
grant select, insert, update, delete on public.providers to authenticated;

alter table public.provider_documents enable row level security;
drop policy if exists provdocs_select on public.provider_documents;
create policy provdocs_select on public.provider_documents for select to authenticated
  using (private.is_admin() or exists (select 1 from public.providers p where p.id = provider_id and p.owner_id = auth.uid()));
drop policy if exists provdocs_insert on public.provider_documents;
create policy provdocs_insert on public.provider_documents for insert to authenticated
  with check (status = 'pending' and exists (select 1 from public.providers p where p.id = provider_id and p.owner_id = auth.uid()));
drop policy if exists provdocs_update on public.provider_documents;
create policy provdocs_update on public.provider_documents for update to authenticated
  using (private.is_admin()) with check (private.is_admin());
drop policy if exists provdocs_delete on public.provider_documents;
create policy provdocs_delete on public.provider_documents for delete to authenticated
  using (private.is_admin() or exists (select 1 from public.providers p where p.id = provider_id and p.owner_id = auth.uid()));
revoke all on public.provider_documents from anon, authenticated;
grant select, insert, update, delete on public.provider_documents to authenticated;

-- Avis : laissés par les clients validés (pas par d'autres prestataires), un par client et par prestataire, publiés
-- avec le nom de l'organisation du client ; le prestataire peut répondre ; l'administration peut masquer un avis.
create table if not exists public.provider_reviews (
  id             uuid primary key default gen_random_uuid(),
  provider_id    uuid not null references public.providers (id) on delete cascade,
  author_id      uuid not null references public.profiles (id) on delete cascade,
  author_label   text,
  rating         smallint not null check (rating between 1 and 5),
  title          text check (length(title) <= 120),
  comment        text not null check (length(comment) between 10 and 2000),
  service_date   date,
  status         text not null default 'published' check (status in ('published', 'hidden')),
  provider_reply text check (length(provider_reply) <= 2000),
  reply_at       timestamptz,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (provider_id, author_id)
);
create or replace function private.reviews_guard() returns trigger
language plpgsql security definer set search_path = '' as $$
declare adm boolean := private.is_admin();
        is_owner boolean := exists (select 1 from public.providers p where p.id = new.provider_id and p.owner_id = auth.uid());
begin
  if tg_op = 'INSERT' then
    if is_owner then raise exception 'un prestataire ne peut pas s''évaluer lui-même'; end if;
    new.author_id := auth.uid(); new.status := 'published'; new.provider_reply := null; new.reply_at := null;
    new.author_label := coalesce(nullif((select organization from public.profiles where id = auth.uid()), ''), 'Client Angor');
  elsif not adm then
    if new.author_id = auth.uid() then          -- l'auteur modifie son avis, rien d'autre
      new.provider_reply := old.provider_reply; new.reply_at := old.reply_at; new.status := old.status;
      new.author_label := old.author_label; new.provider_id := old.provider_id;
    elsif is_owner then                          -- le prestataire répond, rien d'autre
      new.reply_at := case when new.provider_reply is distinct from old.provider_reply then now() else old.reply_at end;
      new.rating := old.rating; new.title := old.title; new.comment := old.comment; new.service_date := old.service_date;
      new.status := old.status; new.author_id := old.author_id; new.author_label := old.author_label; new.provider_id := old.provider_id;
    else
      raise exception 'modification non autorisée';
    end if;
  end if;
  new.updated_at := now();
  return new;
end $$;
revoke execute on function private.reviews_guard() from public, anon, authenticated;
drop trigger if exists reviews_guard on public.provider_reviews;
create trigger reviews_guard before insert or update on public.provider_reviews for each row execute function private.reviews_guard();

alter table public.provider_reviews enable row level security;
drop policy if exists reviews_select on public.provider_reviews;
create policy reviews_select on public.provider_reviews for select to authenticated
  using (private.is_admin() or author_id = auth.uid()
         or exists (select 1 from public.providers p where p.id = provider_id and p.owner_id = auth.uid())
         or (status = 'published' and private.is_approved()));
drop policy if exists reviews_insert on public.provider_reviews;
create policy reviews_insert on public.provider_reviews for insert to authenticated
  with check (private.is_client()
              and exists (select 1 from public.providers p where p.id = provider_id and p.status in ('submitted', 'verified')));
drop policy if exists reviews_update on public.provider_reviews;
create policy reviews_update on public.provider_reviews for update to authenticated
  using (private.is_admin() or author_id = auth.uid()
         or exists (select 1 from public.providers p where p.id = provider_id and p.owner_id = auth.uid()));
drop policy if exists reviews_delete on public.provider_reviews;
create policy reviews_delete on public.provider_reviews for delete to authenticated
  using (private.is_admin() or author_id = auth.uid());
revoke all on public.provider_reviews from anon, authenticated;
grant select, insert, update, delete on public.provider_reviews to authenticated;

-- Demandes de contact / de devis d'un client à un prestataire (la mise en relation ; le contrat se conclut entre eux)
create table if not exists public.provider_requests (
  id              uuid primary key default gen_random_uuid(),
  provider_id     uuid not null references public.providers (id) on delete cascade,
  requester_id    uuid references public.profiles (id) on delete set null,
  requester_label text,               -- organisation et e-mail du demandeur, pour que le prestataire puisse répondre
  category        text,
  country         text,
  period          text check (length(period) <= 200),
  message         text not null check (length(message) between 10 and 3000),
  status          text not null default 'new' check (status in ('new', 'read', 'answered', 'closed')),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create or replace function private.requests_guard() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if tg_op = 'INSERT' then
    new.requester_id := auth.uid(); new.status := 'new';
    new.requester_label := (select coalesce(nullif(organization, ''), full_name, '') || ' <' || email || '>'
                              from public.profiles where id = auth.uid());
  elsif not private.is_admin() then           -- seul le statut évolue après l'envoi
    new.provider_id := old.provider_id; new.requester_id := old.requester_id; new.requester_label := old.requester_label;
    new.category := old.category; new.country := old.country; new.period := old.period; new.message := old.message;
  end if;
  new.updated_at := now();
  return new;
end $$;
revoke execute on function private.requests_guard() from public, anon, authenticated;
drop trigger if exists requests_guard on public.provider_requests;
create trigger requests_guard before insert or update on public.provider_requests for each row execute function private.requests_guard();
alter table public.provider_requests enable row level security;
drop policy if exists requests_select on public.provider_requests;
create policy requests_select on public.provider_requests for select to authenticated
  using (private.is_admin() or requester_id = auth.uid()
         or exists (select 1 from public.providers p where p.id = provider_id and p.owner_id = auth.uid()));
drop policy if exists requests_insert on public.provider_requests;
create policy requests_insert on public.provider_requests for insert to authenticated
  with check (private.is_client()
              and exists (select 1 from public.providers p where p.id = provider_id and p.status in ('submitted', 'verified')));
drop policy if exists requests_update on public.provider_requests;
create policy requests_update on public.provider_requests for update to authenticated
  using (private.is_admin() or requester_id = auth.uid()
         or exists (select 1 from public.providers p where p.id = provider_id and p.owner_id = auth.uid()));
revoke all on public.provider_requests from anon, authenticated;
grant select, insert, update on public.provider_requests to authenticated;

-- Fichiers (Supabase Storage) : photos publiques (« provider-media », 5 Mo, JPEG/PNG/WebP) et documents privés
-- (« provider-docs », 10 Mo, PDF/JPEG/PNG : Kbis, licences, attestation d'assurance, certifications, CV – visibles du prestataire et
-- d'Angor seulement). Chaque fichier est rangé dans un dossier portant l'identifiant de la fiche : <id>/<fichier>.
-- Les vidéos se publient par lien (YouTube, Vimeo, site) pour ménager l'espace de stockage.
do $do$
begin
  if to_regclass('storage.objects') is null then
    raise notice 'Stockage Supabase absent (base de test) : compartiments non créés';
    return;
  end if;
  insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types) values
    ('provider-media', 'provider-media', true, 5242880, array['image/jpeg', 'image/png', 'image/webp']),
    ('provider-docs', 'provider-docs', false, 10485760, array['application/pdf', 'image/jpeg', 'image/png'])
  on conflict (id) do update set public = excluded.public, file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;
  execute 'drop policy if exists angor_provider_files_read on storage.objects';
  execute $p$create policy angor_provider_files_read on storage.objects for select to authenticated
    using (bucket_id in ('provider-media', 'provider-docs') and (private.is_admin() or exists (
      select 1 from public.providers p where p.id::text = (storage.foldername(name))[1] and p.owner_id = auth.uid())))$p$;
  execute 'drop policy if exists angor_provider_files_write on storage.objects';
  execute $p$create policy angor_provider_files_write on storage.objects for insert to authenticated
    with check (bucket_id in ('provider-media', 'provider-docs') and exists (
      select 1 from public.providers p where p.id::text = (storage.foldername(name))[1] and p.owner_id = auth.uid()))$p$;
  execute 'drop policy if exists angor_provider_files_update on storage.objects';
  execute $p$create policy angor_provider_files_update on storage.objects for update to authenticated
    using (bucket_id in ('provider-media', 'provider-docs') and exists (
      select 1 from public.providers p where p.id::text = (storage.foldername(name))[1] and p.owner_id = auth.uid()))$p$;
  execute 'drop policy if exists angor_provider_files_delete on storage.objects';
  execute $p$create policy angor_provider_files_delete on storage.objects for delete to authenticated
    using (bucket_id in ('provider-media', 'provider-docs') and (private.is_admin() or exists (
      select 1 from public.providers p where p.id::text = (storage.foldername(name))[1] and p.owner_id = auth.uid())))$p$;
end $do$;

-- ------------------------------------------------------------------ premier administrateur
-- Après avoir créé votre compte depuis angor.fr/compte.html, exécutez UNE fois (avec votre e-mail) :
--   update public.profiles set role = 'admin', status = 'approved', approved_at = now()
--    where email = 'votre-adresse@exemple.fr';
