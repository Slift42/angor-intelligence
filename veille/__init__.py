"""Veille Sûreté – moteur de collecte, de normalisation et de scoring.

Organisation :
- config.py      : lecture de config/*.json et du fichier .env (clés d'API)
- http.py        : accès réseau commun (délais, relances, authentification)
- model.py       : format d'événement standard et taxonomie (catégories, gravités)
- geo.py         : pays, point-dans-polygone, distances
- connectors/    : un fichier par source (gratuites aujourd'hui, payantes demain)
- dedupe.py      : fusion des doublons entre sources
- risk.py        : note de risque pays (1 Minimal → 5 Extrême)
- publish.py     : historique local et fichiers lus par la carte
"""

__version__ = "0.1.0"
