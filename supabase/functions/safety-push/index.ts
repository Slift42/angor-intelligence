// Angor Intelligence – envoi des notifications de safety check (Supabase Edge Function, Deno).
// Appelée par la page d'administration juste après la création d'un safety check : { "check_id": "…" }.
// Déploiement (une fois) : voir GUIDE_MISE_EN_LIGNE.md, partie H.
// Secrets de la fonction : VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUBJECT (ex. mailto:contact@angor.fr).
// SUPABASE_URL, SUPABASE_ANON_KEY et SUPABASE_SERVICE_ROLE_KEY sont fournis automatiquement par Supabase.
import { createClient } from "npm:@supabase/supabase-js@2";
import webpush from "npm:web-push@3.6.7";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (b: unknown, status = 200) => new Response(JSON.stringify(b), { status, headers: { ...cors, "Content-Type": "application/json" } });

function km(a: number, b: number, c: number, d: number) {
  const r = Math.PI / 180, x = Math.sin((c - a) * r / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin((d - b) * r / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(x));
}
// même règle que la carte : tous, pays (résidence déclarée ou dernière position), ou rayon autour d'un point
function concerned(area: any, org: string | null, p: any) {
  if (org && (p.organization || "").toLowerCase() !== org.toLowerCase()) return false;
  const loc = p.location || {}, prefs = p.prefs || {};
  if (!area || area.type === "all") return true;
  if (area.type === "country") return loc.iso === area.iso || prefs.base_country === area.iso || (prefs.travel_countries || []).includes(area.iso);
  if (area.type === "circle") return loc.lat != null && km(area.lat, area.lon, loc.lat, loc.lon) <= (area.radius_km || 50);
  return false;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });
  const url = Deno.env.get("SUPABASE_URL")!;
  // 1. l'appelant doit être un administrateur validé
  const asUser = createClient(url, Deno.env.get("SUPABASE_ANON_KEY")!, { global: { headers: { Authorization: req.headers.get("Authorization") ?? "" } } });
  const { data: isAdmin } = await asUser.rpc("is_admin");
  if (!isAdmin) return json({ error: "forbidden" }, 403);
  const { check_id } = await req.json().catch(() => ({}));
  if (!check_id) return json({ error: "check_id manquant" }, 400);

  // 2. lecture du safety check et des utilisateurs concernés (clé de service : contourne RLS, côté serveur uniquement)
  const admin = createClient(url, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const { data: check } = await admin.from("safety_checks").select("*").eq("id", check_id).single();
  if (!check) return json({ error: "safety check introuvable" }, 404);
  const { data: users } = await admin.from("profiles").select("id, organization, prefs, location").eq("status", "approved");
  const targets = (users || []).filter((p: any) => concerned(check.area, check.organization, p)).map((p: any) => p.id);
  if (!targets.length) return json({ targets: 0, sent: 0 });
  const { data: subs } = await admin.from("push_subscriptions").select("*").in("user_id", targets);

  // 3. envoi (les abonnements expirés sont supprimés)
  webpush.setVapidDetails(Deno.env.get("VAPID_SUBJECT") ?? "mailto:contact@angor.fr",
    Deno.env.get("VAPID_PUBLIC_KEY")!, Deno.env.get("VAPID_PRIVATE_KEY")!);
  const payload = JSON.stringify({ title: `Safety check – ${check.title}`, body: check.message || "Êtes-vous en sécurité ? Répondez en un geste.",
    check_id: check.id, tag: `safety-${check.id}` });
  let sent = 0, gone = 0;
  await Promise.all((subs || []).map(async (s: any) => {
    try {
      await webpush.sendNotification({ endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } }, payload, { TTL: 86400, urgency: "high" });
      sent++;
    } catch (e: any) {
      if (e?.statusCode === 404 || e?.statusCode === 410) { gone++; await admin.from("push_subscriptions").delete().eq("endpoint", s.endpoint); }
    }
  }));
  return json({ targets: targets.length, devices: (subs || []).length, sent, expired: gone });
});
