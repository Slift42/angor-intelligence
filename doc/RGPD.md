# Conformité juridique et RGPD

> Les textes légaux d'Angor Intelligence (v0.19) ont été rédigés avec l'aide d'une IA à partir des règles en vigueur en
> octobre 2026. Ils constituent une **base de travail sérieuse, pas un avis juridique** : faites-les relire par un avocat
> avant d'ouvrir les abonnements payants, en particulier les CGV destinées aux consommateurs.

## Où sont les textes

| Document | Page publiée | Contenu modifiable |
|---|---|---|
| Hub « Informations légales » | `docs/legal.html` | – |
| Mentions légales (LCEN, art. 6) | `docs/mentions-legales.html` | identité de l'éditeur, hébergeurs : `config/legal.json` |
| CGU (tous les utilisateurs) | `docs/cgu.html` | texte : la page ; version : `config/legal.json` |
| CGV (professionnels et consommateurs) | `docs/cgv.html` | texte : la page ; offres, médiateur, tribunal : `config/legal.json` |
| Politique de confidentialité et cookies | `docs/confidentialite.html` | sous-traitants et services tiers : `config/legal.json` |
| Accord de sous-traitance (art. 28 RGPD, clients pro) | `docs/sous-traitance.html` | sous-traitants : `config/legal.json` |
| Sources, crédits et licences | `docs/licences.html` | crédits : `config/legal.json` ; sources : `config/sources.json` |

Fonctionnement : le robot publie `config/legal.json` dans `docs/data/legal.js` (`python -m veille.legal` pour le faire
immédiatement) ; `docs/legal.js` remplit les pages. Un champ vide s'affiche « [à compléter : …] » et, tant que `status`
vaut `"projet"`, un bandeau « Projet – non contractuel » s'affiche sur chaque page.

**Changer le fond d'un texte** = modifier la page **et** augmenter sa `version` (et sa `date`) dans `config/legal.json`.
Pour les documents marqués `"acceptation": true` (CGU, confidentialité), les utilisateurs doivent accepter la nouvelle version
à leur connexion suivante (preuve horodatée dans la table Supabase `legal_acceptances`). Tant que le statut est `"projet"`,
les acceptations sont enregistrées avec le suffixe `-projet` : la version définitive sera donc acceptée à nouveau.

## Check-list avant d'ouvrir les abonnements payants

1. **Contrat de travail** : vérifier clause d'exclusivité, non-concurrence, conflit d'intérêts (plan d'action, phase 0).
2. **Structure** : créer la micro-entreprise (ou la société) ; compléter `editeur` dans `config/legal.json` (nom suivi de la
   mention « EI » pour un entrepreneur individuel, SIREN, adresse, téléphone, directeur de la publication).
3. **Adresses e-mail** sur le domaine : `contact@angor.fr` (et éventuellement `rgpd@angor.fr` → `editeur.contact_donnees`).
4. **Médiateur de la consommation** (obligatoire dès qu'un particulier peut s'abonner, art. L612-1 du Code de la consommation) :
   adhérer à un médiateur référencé, compléter `mediateur`. La plateforme européenne RLL a fermé le 20 juillet 2025 : ne plus
   y faire référence.
5. **Tribunal** compétent entre professionnels : compléter `tribunal`.
6. **Assurance** responsabilité civile professionnelle (recommandée pour une activité de conseil en sûreté).
7. **Vente en ligne aux consommateurs** – ne pas l'ouvrir avant d'avoir développé (prévu avec les espaces clients) :
   - le bouton de commande « Commande avec obligation de paiement » et l'e-mail de confirmation (CGV + formulaire de rétractation) ;
   - la fonction de rétractation « Renoncer au contrat ici » → « Confirmer la rétractation », avec accusé de réception immédiat
     par e-mail (ordonnance n° 2026-2 du 5 janvier 2026, en vigueur depuis le 19 juin 2026) ;
   - la fonction « Résilier mon abonnement » avec confirmation par e-mail (art. L215-1-1, résiliation en trois clics) ;
   - l'e-mail d'information avant reconduction tacite (art. L215-1).
   D'ici là, vendre **sur devis ou bon de commande signé** uniquement.
8. **Facturation** : factures numérotées avec les mentions obligatoires, conservées 10 ans ; anticiper la facturation
   électronique (réception obligatoire pour toutes les entreprises depuis septembre 2026, émission pour les micro-entreprises
   prévue en septembre 2027 – à confirmer avec un expert-comptable).
9. **Licences des sources** pour un usage commercial : ACLED (licence payante), fonds de carte Esri (conditions ArcGIS Online à
   vérifier ou remplacement par OpenFreeMap seul), Global Fishing Watch et OpenSky (non commerciaux), Meteoalarm (licence EUMETNET),
   worldhotlines.org (sans licence explicite).
10. **Supabase** : passer en offre Pro (sauvegardes, pas de mise en pause) ; garder une copie du DPA Supabase.
11. **Analyse d'impact (AIPD)** : documenter en une page pourquoi la géolocalisation des safety checks ne crée pas de risque
    élevé (facultative, à l'initiative de la personne, arrondie à ≈ 100 m, effacée après 30 jours, pas de suivi continu) ; en
    faire une vraie AIPD si un client demande un suivi permanent.
12. **Notice pour les salariés des clients** (information préalable, art. 13 RGPD, et du CSE) : modèle à rédiger avec les
    espaces clients.
13. **Accessibilité** : la directive européenne sur l'accessibilité (en vigueur depuis le 28 juin 2025) exempte les
    micro-entreprises de services ; à revoir si l'activité dépasse 10 salariés ou 2 M€ de chiffre d'affaires.
14. **Relecture par un avocat**, puis `"status": "en vigueur"` et `"beta_gratuite": false` dans `config/legal.json`.

## Registre des traitements (article 30 du RGPD)

Responsable : l'éditeur (voir `config/legal.json`). Mettre à jour à chaque nouveau traitement ou prestataire.

| Traitement | Finalité | Base légale | Personnes | Données | Destinataires | Hors UE | Conservation | Sécurité |
|---|---|---|---|---|---|---|---|---|
| Comptes utilisateurs | Gérer l'accès, synchroniser les réglages, alertes près des sites | Contrat (CGU) | Utilisateurs | Nom, organisation, fonction, e-mail, téléphone (facultatif), préférences, sites, trajets | Éditeur ; référent du client ; Supabase/AWS | Accès support Supabase (CCT) | Durée du compte ; non validés 6 mois ; inactifs 3 ans | RLS, mots de passe hachés, TLS |
| Preuves d'acceptation | Prouver l'acceptation des CGU / confidentialité | Intérêt légitime | Utilisateurs | Document, version, horodatage | Éditeur | Idem | Durée du compte | Écriture par fonction uniquement |
| Safety checks (pour le compte des clients) | Devoir de protection des collaborateurs | Sous-traitance (client responsable) ; position : choix de la personne | Collaborateurs des clients | Réponse, message, date, position arrondie si activée | Client (référent, admins) ; Supabase | Idem | Réponses 12 mois ; position 30 jours | RLS, effacement automatique |
| Notifications | Prévenir sur l'appareil | Consentement | Utilisateurs | Adresse d'abonnement Web Push | Supabase ; service de push du navigateur | Selon navigateur | Jusqu'à désactivation | Clé VAPID privée dans les secrets Supabase |
| Gestion commerciale | Devis, contrats, factures | Contrat ; obligation légale | Clients, contacts de facturation | Identité, coordonnées, offre, factures | Éditeur ; expert-comptable | Non | Contrat 5 ans après fin ; factures 10 ans | Stockage hors dépôt public |
| Support | Répondre aux demandes | Intérêt légitime | Demandeurs | E-mail, messages | Éditeur ; prestataire e-mail | Selon prestataire | 3 ans | Messagerie sécurisée |
| Veille presse | Informer sur les événements | Intérêt légitime, liberté d'information | Personnes citées dans des titres publics | Titre, résumé, lien | Utilisateurs | Hébergeur du site (GitHub) | Durée d'archivage des incidents | Pas de recherche par personne ; retrait sur demande |
| Journaux techniques | Sécurité | Intérêt légitime | Visiteurs, utilisateurs | IP, navigateur, horodatage | Hébergeurs | GitHub (DPF) | Durée fixée par l'hébergeur | – |

## Procédures

- **Demande d'exercice des droits** : répondre sous un mois (prolongeable de deux mois si complexe, en prévenant la personne) ;
  vérifier l'identité en cas de doute ; pour un collaborateur d'un client, informer le référent du client.
- **Violation de données** (perte, fuite, accès non autorisé) : la consigner dans un registre des violations ; notifier la CNIL
  sous 72 heures si elle présente un risque pour les personnes ; prévenir les clients professionnels sous 48 heures (accord de
  sous-traitance) ; informer les personnes si le risque est élevé.
- **Demande de retrait** d'un titre de presse citant une personne : examiner sous un mois ; masquer l'incident (configuration
  `config/verified.json`, « fausse alerte ») si la demande est fondée.
- **Nouveau sous-traitant** : l'ajouter à `config/legal.json`, prévenir les clients professionnels 30 jours avant (accord de
  sous-traitance, article 3.4), mettre à jour ce registre.

## Ce que le code garantit

- Preuve d'acceptation horodatée et versionnée (`legal_acceptances`, fonction `accept_legal`), visible dans Administration.
- Effacement automatique selon les durées annoncées (`private.housekeeping()`, planifiée chaque nuit dans la base par pg_cron).
- Fonctions à privilèges hors API ou réservées aux utilisateurs connectés (recommandations du conseiller de sécurité Supabase).
- Aucun traceur : pas de cookie publicitaire ni de mesure d'audience ; polices et drapeaux auto-hébergés (`docs/vendor/`).
- Lien « Informations légales » sur la carte (attribution), dans le menu Plus, l'aide, Mon compte et Administration.
- Test automatique : `tests/test_legal.py` (références des pages, absence d'appel à Google Fonts / flagcdn, entretien des comptes).
