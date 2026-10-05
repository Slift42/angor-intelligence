"""Veille Sûreté – moteur de collecte, de normalisation et de scoring.

Organisation :
- config.py      : lecture de config/*.json et du fichier .env (clés d'API)
- http.py        : accès réseau commun (délais, relances, authentification)
- model.py       : format d'événement standard et taxonomie (catégories, gravités)
- geo.py         : pays, point-dans-polygone, distances
- connectors/    : un fichier par source (gratuites aujourd'hui, payantes demain)
- dedupe.py      : fusion des doublons entre sources
- risk.py        : note de risque pays (1 Minimal → 5 Extrême)
- pulse.py       : indice de stabilité « Pulse » (0-100), tendance et causes
- quality.py     : validations de l'analyste (config/verified.json) et cotation de l'Amirauté (A1-F6)
- notify.py      : alertes Telegram / e-mail, point quotidien, alertes Pulse
- crises.py      : chronologies de crise (incidents liés sur plusieurs jours)
- agenda.py      : jours fériés, élections, fêtes religieuses, échéances de l'analyste
- llm.py         : socle IA commun (budget, cache, tâches activables)
- reports.py     : agrégateur de rapports (think tanks, OI, ONG) → onglet Rapports
- early_warning.py : alerte précoce climat-conflit par unité administrative → onglet Alerte précoce
- fcdo.py        : texte détaillé des conseils FCDO par rubrique (rapport pays)
- country_detail.py : villes, aéroports, secours, santé par pays → docs/data/country/<ISO>.js
- legal.py       : informations légales (config/legal.json → docs/data/legal.js)
- providers.py   : annuaire des prestataires (inscrits + repérés par Angor) → docs/data/providers.js
- accounts.py    : signe de vie envoyé à la base des comptes Supabase (évite sa mise en pause)
- publish.py     : historique local et fichiers lus par la carte
"""

__version__ = "0.22.0"
