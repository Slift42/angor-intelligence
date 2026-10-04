"""Remplacé en v0.20 : l'annuaire des prestataires est désormais construit par le robot (veille/providers.py).

- prestataires repérés par Angor (non vérifiés) : config/providers_directory.json ;
- catégories de services et niveaux de fiabilité : config/providers.json ;
- prestataires inscrits : fiches remplies par les prestataires eux-mêmes (prestataire.html, base Supabase).
Pour régénérer docs/data/providers.js sans lancer de collecte : python -c "from veille import providers; providers.update({})"
"""

if __name__ == "__main__":
    print(__doc__)
