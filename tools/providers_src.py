"""Source de docs/data/providers.js : prestataires de sécurité / sûreté et d'assistance.

Liste de départ, volontairement limitée aux acteurs établis et publics (sites officiels). Aucune
personne nommée : les contacts nominatifs sont des données personnelles et changent souvent ; passez
par le formulaire ou la ligne 24/7 du site, ou par votre réseau (CDSE, CLUSIF, club sûreté).
Couverture et capacités : indicatives, à confirmer avec chaque prestataire pour le pays visé.
« local » : vos prestataires locaux vérifiés, par pays (ISO2) – à compléter par l'analyste.
Regénérer : python tools/providers_src.py
"""
import json
from pathlib import Path

S = {  # codes de services
    "cp": ("Protection rapprochée", "Close protection"),
    "ts": ("Transport sécurisé / véhicules blindés", "Secure transport / armoured vehicles"),
    "ev": ("Évacuation / extraction", "Evacuation / extraction"),
    "med": ("Assistance et évacuation médicales", "Medical assistance and evacuation"),
    "int": ("Renseignement, analyse de risques, alertes", "Intelligence, risk analysis, alerts"),
    "gs": ("Gardiennage / sûreté de sites", "Guarding / site security"),
    "cm": ("Gestion de crise, kidnapping et rançon (K&R)", "Crisis management, kidnap & ransom (K&R)"),
    "tr": ("Suivi des voyageurs, formation HEAT", "Traveller tracking, HEAT training"),
    "cit": ("Transport de fonds et valeurs", "Cash and valuables in transit"),
}
ALL = ["Afrique", "Moyen-Orient", "Europe", "Asie", "Amériques", "Océanie"]

PROVIDERS = [
    ("GardaWorld / Crisis24", "Canada", "https://www.garda.com", ALL, ["cp", "ts", "ev", "int", "gs", "cm", "tr"],
     "Très présent en zones de conflit (Afrique, Moyen-Orient) ; Crisis24 = renseignement et alertes."),
    ("Control Risks", "Royaume-Uni", "https://www.controlrisks.com", ALL, ["int", "cm", "cp", "ev", "tr"],
     "Référence du conseil en risques, réponse aux crises et K&R."),
    ("International SOS", "Royaume-Uni / Singapour", "https://www.internationalsos.com", ALL, ["med", "ev", "int", "tr"],
     "Assistance médicale et sécuritaire 24/7, évacuations sanitaires et sécuritaires."),
    ("Amarante International", "France", "https://www.amarante.com", ["Afrique", "Moyen-Orient", "Europe", "Asie"],
     ["cp", "ts", "ev", "int", "gs", "cm", "tr"], "Groupe français, forte implantation en Afrique et au Moyen-Orient."),
    ("Allied Universal / G4S", "États-Unis / Royaume-Uni", "https://www.g4s.com", ALL, ["gs", "ts", "cit", "cp"],
     "Gardiennage et transport de valeurs dans de nombreux pays d'Afrique et d'Asie."),
    ("Securitas", "Suède", "https://www.securitas.com", ["Europe", "Amériques", "Afrique", "Asie"], ["gs", "int", "cp"],
     "Sûreté de sites, sécurité électronique, services de risque."),
    ("Prosegur", "Espagne", "https://www.prosegur.com", ["Amériques", "Europe", "Asie", "Afrique"], ["cit", "gs", "ts"],
     "Transport de fonds, gardiennage ; très présent en Amérique latine."),
    ("Brink's", "États-Unis", "https://www.brinks.com", ALL, ["cit", "ts"], "Transport sécurisé de valeurs."),
    ("Constellis", "États-Unis", "https://www.constellis.com", ["Moyen-Orient", "Afrique", "Asie", "Amériques"],
     ["cp", "ts", "gs", "tr"], "Protection en environnement hostile, formation."),
    ("Unity Resources Group", "Australie / Émirats", "https://www.unityresourcesgroup.com",
     ["Moyen-Orient", "Afrique", "Asie", "Océanie"], ["cp", "ts", "gs", "int"], "Sécurité en environnements complexes."),
    ("Pilgrims Group", "Royaume-Uni", "https://www.pilgrimsgroup.com", ["Europe", "Moyen-Orient", "Afrique"],
     ["cp", "ts", "ev", "tr", "int"], "Protection rapprochée, formation HEAT, évacuations."),
    ("Global Guardian", "États-Unis", "https://www.globalguardian.com", ALL, ["cp", "ev", "med", "int", "tr"],
     "Réponse d'urgence 24/7, évacuations, protection de dirigeants."),
    ("Pinkerton", "États-Unis", "https://pinkerton.com", ALL, ["cp", "int", "cm"], "Protection de dirigeants, enquêtes, risques."),
    ("Solace Global", "Royaume-Uni", "https://www.solaceglobal.com", ALL, ["ev", "ts", "cp", "int", "tr"],
     "Évacuations, transport sécurisé, suivi de voyageurs."),
    ("Northcott Global Solutions", "Royaume-Uni", "https://www.northcottglobalsolutions.com", ALL, ["ev", "med", "cp"],
     "Réponse d'urgence et évacuation terrestre/aérienne."),
    ("Drum Cussac", "Royaume-Uni", "https://www.drum-cussac.com", ALL, ["int", "tr", "cm", "ev"],
     "Gestion des risques voyageurs, alertes, assistance."),
    ("Healix International", "Royaume-Uni", "https://www.healix.com", ALL, ["med", "ev", "int", "tr"],
     "Assistance médicale et sécuritaire (a intégré AKE)."),
    ("Europ Assistance", "France", "https://www.europ-assistance.com", ALL, ["med", "ev", "tr"],
     "Assistance médicale et rapatriement, offres sûreté voyageurs."),
]

LOCAL = Path(__file__).resolve().parent.parent / "config" / "providers_local.json"  # {"ML": [{name, web, services, note}]}

if __name__ == "__main__":
    out = {"note": ("Liste indicative de prestataires établis (sites officiels). Couverture et capacités à confirmer "
                    "pour chaque pays. Pas de contact nominatif : passer par le site (formulaire, ligne 24/7) ou votre réseau."),
           "services": {k: {"fr": v[0], "en": v[1]} for k, v in S.items()},
           "providers": [{"name": n, "hq": hq, "web": w, "regions": r, "services": sv, "note": note,
                          "linkedin": "https://www.linkedin.com/search/results/companies/?keywords=" + n.split(" /")[0].replace(" ", "%20")}
                         for n, hq, w, r, sv, note in PROVIDERS],
           "local": json.loads(LOCAL.read_text(encoding="utf-8")) if LOCAL.exists() else {}}
    dest = Path(__file__).resolve().parent.parent / "docs" / "data" / "providers.js"
    dest.write_text("window.VS_PROVIDERS = " + json.dumps(out, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print(f"{len(PROVIDERS)} prestataires → {dest}")
