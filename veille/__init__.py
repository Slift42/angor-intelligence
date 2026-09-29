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
- publish.py     : historique local et fichiers lus par la carte
"""

__version__ = "0.9.1"
