// Angor Intelligence – « Actualiser » : lance une collecte immédiate du robot GitHub (Supabase Edge Function, Deno).
// Appelée par la carte (bouton Actualiser) pour un utilisateur connecté et validé.
// Garde-fous : une seule collecte à la fois, et pas plus d'une demande toutes les 10 minutes pour tout le monde.
// Secrets de la fonction (voir GUIDE_MISE_EN_LIGNE.md, partie J) :
//   GITHUB_TOKEN    jeton « fine-grained » limité au dépôt, permission Actions : Read and write
//   GITHUB_REPO     ex. Slift42/angor-intelligence
//   GITHUB_WORKFLOW ex. collecte.yml (nom du fichier dans .github/workflows)
import { createClient } from "npm:@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (b: unknown, status = 200) => new Response(JSON.stringify(b), { status, headers: { ...cors, "Content-Type": "application/json" } });
const MIN_INTERVAL_MIN = 10;

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });
  const asUser = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!,
    { global: { headers: { Authorization: req.headers.get("Authorization") ?? "" } } });
  const { data: approved } = await asUser.rpc("is_approved");
  if (!approved) return json({ error: "forbidden" }, 403);

  const token = Deno.env.get("GITHUB_TOKEN");
  const repo = Deno.env.get("GITHUB_REPO") ?? "Slift42/angor-intelligence";
  const wf = Deno.env.get("GITHUB_WORKFLOW") ?? "collecte.yml";
  if (!token) return json({ error: "GITHUB_TOKEN manquant" }, 500);
  const gh = (path: string, init: RequestInit = {}) => fetch(`https://api.github.com/repos/${repo}/actions/workflows/${wf}${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "angor-intelligence", ...(init.headers || {}) },
  });

  // 1. une collecte est déjà en cours ou en file d'attente : inutile d'en lancer une autre
  for (const status of ["in_progress", "queued"]) {
    const r = await gh(`/runs?status=${status}&per_page=1`);
    if (!r.ok) return json({ error: `GitHub ${r.status}` }, 502);
    const d = await r.json();
    if (d.total_count > 0) return json({ status: "running", started_at: d.workflow_runs[0].run_started_at || d.workflow_runs[0].created_at });
  }
  // 2. dernière collecte lancée il y a moins de 10 minutes : les données sont fraîches
  const last = await (await gh("/runs?per_page=1")).json();
  const run = (last.workflow_runs || [])[0];
  if (run && Date.now() - Date.parse(run.created_at) < MIN_INTERVAL_MIN * 60000) {
    return json({ status: "recent", created_at: run.created_at, conclusion: run.conclusion });
  }
  // 3. lancement
  const r = await gh("/dispatches", { method: "POST", body: JSON.stringify({ ref: "main" }) });
  if (r.status !== 204) return json({ error: `GitHub ${r.status}: ${(await r.text()).slice(0, 200)}` }, 502);
  return json({ status: "started" });
});
