# Mettre Angor Intelligence en ligne

Résultat : la carte est accessible sur `https://<identifiant>.github.io/angor-intelligence/`, puis sur votre propre domaine (ex. `https://carte.mondomaine.fr`). Un robot GitHub la met à jour toutes les 30 minutes, même PC éteint.

Toutes les commandes se tapent dans le terminal de VS Code (PowerShell), dans le dossier `veille-surete`.

À savoir :
- **Dépôt public** (gratuit) : le code est visible, pas vos secrets (`.env`) ni vos vrais sites (`config/sites.local.json`), qui ne partent jamais sur GitHub.
- **La carte en ligne n'affiche jamais vos sites** (`VS_PUBLIC=1`).

---

## Partie A – GitHub (≈ 20 min)

### A1. Installer l'outil GitHub (une fois)
```
winget install -e --id GitHub.cli
```
Fermez VS Code, rouvrez-le, puis :
```
gh auth login
```
Réponses : **GitHub.com** → **HTTPS** → **Yes** → **Login with a web browser**. Copiez le code à 8 caractères, appuyez sur Entrée, collez le code dans la page qui s'ouvre, validez.

### A2. Vous présenter à Git (une fois)
```
git config --global user.name "Stef"
git config --global user.email "adresse-de-votre-compte-github@exemple.com"
```

### A3. Installer le robot
```
mkdir .github\workflows
copy tools\github-actions-collecte.yml .github\workflows\collecte.yml
```

### A4. Contrôle de sécurité avant envoi
```
git init -b main
git add .
git status
```
Dans la liste verte, **ne doivent PAS apparaître** : `.env`, `config/sites.local.json`, `data/`. Si l'un d'eux apparaît : stop, demandez à Claude.

### A5. Créer le dépôt et envoyer
```
git commit -m "Angor Intelligence – première mise en ligne"
gh repo create angor-intelligence --public --source . --push
```

### A6. Activer la publication
Sur github.com → votre dépôt → **Settings** → **Pages** (colonne de gauche) → **Source : GitHub Actions**.

### A7. Donner les secrets au robot
Pour chacun, la commande demande la valeur : collez-la (elle reste invisible), Entrée.
```
gh secret set TELEGRAM_BOT_TOKEN
gh secret set TELEGRAM_CHAT_ID
gh secret set ANTHROPIC_API_KEY
```
(la dernière seulement si vous avez une clé Anthropic). Vos vrais sites, si vous en avez :
```
Get-Content config\sites.local.json -Raw | gh secret set SITES_JSON
```

### A8. Premier lancement
github.com → dépôt → onglet **Actions** → **Collecte** (à gauche) → **Run workflow** → **Run workflow**.
Rond jaune = en cours (3 à 5 min), coche verte = réussi. Cliquez sur l'exécution : l'adresse de la carte s'affiche sous l'étape **deploy**.

### A9. Éviter les alertes en double
Le robot en ligne envoie désormais les alertes Telegram. Sur votre PC, mettez un `#` devant `TELEGRAM_BOT_TOKEN=` dans `.env`, sinon chaque collecte locale renverra les mêmes alertes.

### Mises à jour ensuite
Claude modifie les fichiers sur votre PC → vous double-cliquez **`publier.bat`** (depuis l'Explorateur Windows). Le robot publie la nouvelle version dans les 5 minutes qui suivent l'envoi (déclenchement automatique à chaque `publier.bat`, à condition d'avoir recopié la dernière version du robot : voir « Mettre à jour les robots », partie D).

---

## Partie B – Nom de domaine (≈ 15 min + propagation)

### B1. Choisir et acheter
- Registrar conseillé : **Cloudflare Registrar** (prix coûtant, et Cloudflare Access servira ensuite à réserver la bêta à vos testeurs) ou **OVHcloud** (français). Comptez ~10–15 €/an.
- Avant d'acheter : vérifiez sur l'INPI (data.inpi.fr) et l'EUIPO que le nom n'est pas déjà une marque du secteur.
- Choisissez un sous-domaine pour la carte : `carte.mondomaine.fr` (le domaine nu reste libre pour un futur site vitrine).

### B2. Protéger le domaine côté GitHub (anti-détournement)
github.com → photo de profil → **Settings** → **Pages** (colonne de gauche) → **Add a domain** → saisissez `mondomaine.fr`. GitHub affiche un enregistrement **TXT** : ajoutez-le chez votre registrar (zone DNS), attendez quelques minutes, cliquez **Verify**.

### B3. Pointer le sous-domaine vers GitHub
Chez le registrar, zone DNS → ajouter :

| Type | Nom | Valeur |
|---|---|---|
| CNAME | `carte` | `<votre-identifiant>.github.io` |

Chez Cloudflare : laissez le nuage **gris** (« DNS only ») au début, sinon GitHub ne peut pas créer le certificat HTTPS.

### B4. Déclarer le domaine dans le dépôt
Dépôt → **Settings** → **Pages** → **Custom domain** : `carte.mondomaine.fr` → **Save**. Attendez la coche verte « DNS check successful » (de 5 min à quelques heures), puis cochez **Enforce HTTPS**.

La carte est alors sur `https://carte.mondomaine.fr`.

---

## Passer en accès privé (bêta, puis clients)

- **Cloudflare Access** (gratuit jusqu'à 50 utilisateurs, code par e-mail) devant le domaine. Limite : l'adresse `github.io` reste publique → pour une vraie confidentialité, héberger la carte sur **Cloudflare Pages** (Claude adaptera le robot).
- **Obligatoire dès qu'une source payante est branchée** : ses données ne doivent pas être publiques (licences).
- Avant toute ouverture publique : compléter et relire les textes légaux (`config/legal.json`, pages CGU, CGV, confidentialité – voir `doc/RGPD.md`) et vérifier votre contrat de travail.

---

## Partie C – Base historique (5 ans) et résumés IA

### C1. Installer le robot « Historique » (une fois)
```
copy tools\github-actions-historique.yml .github\workflows\historique.yml
copy tools\github-actions-collecte.yml .github\workflows\collecte.yml
```
Tapez `O` si Windows demande de confirmer, puis double-cliquez sur **`publier.bat`**.

### C2. Construire la base
github.com → dépôt → onglet **Actions** → **Historique** (à gauche) → **Run workflow** → **Run workflow**.
Durée : 30 à 90 minutes (5 ans de GDELT, UCDP, USGS, GDACS, NASA, OMS). À la fin, le robot enregistre la base
dans le dépôt et republie la carte. Relancez-le une fois par mois pour l'actualiser.

### C3. Récupérer la base sur votre PC
`publier.bat` le fait tout seul : il récupère d'abord ce que le robot a enregistré (`git pull`), puis envoie vos changements.

### C4. Résumés d'incidents par l'IA (recommandé)
```
gh secret set ANTHROPIC_API_KEY
```
Collez votre clé Anthropic (créée sur console.anthropic.com, avec un plafond de dépenses). Budget interne :
20 $/mois, lissé jour par jour (`config/settings.json` → `ai`).

---

## Partie D – Conflits UCDP (depuis votre PC) et nouvelles sources

Le site de l'université d'Uppsala (UCDP) refuse les serveurs de GitHub : la partie « conflits vérifiés »
se télécharge donc depuis votre PC, une fois par mois environ.

```
python historique.py --only ucdp
```
(quelques minutes ; le fichier `history_parts/ucdp.json.gz` est créé). Puis double-cliquez sur **`publier.bat`**,
et relancez le robot **Historique** en laissant « Parties » vide : il réutilise la partie UCDP envoyée.

### Mettre à jour les robots (après chaque nouvelle version de ces fichiers)
```
copy tools\github-actions-collecte.yml .github\workflows\collecte.yml
copy tools\github-actions-historique.yml .github\workflows\historique.yml
```

### Sources optionnelles
- **ReliefWeb (ONU OCHA)** : demander un nom d'application gratuit sur https://apidoc.reliefweb.int, puis
  `gh secret set RELIEFWEB_APPNAME` et passer la source `reliefweb` à `"enabled": true` dans `config/sources.json`.
- **Telegram** : ajouter des canaux publics dans la source `telegram` de `config/sources.json`.
- **Prestataires** : ils s'inscrivent eux-mêmes, gratuitement (compte « Prestataire de services » sur angor.fr/compte.html), et vous
  vérifiez leurs fiches dans Administration → Prestataires. Ceux que vous repérez vous-même (non vérifiés) : `config/providers_directory.json`.

---

## Partie E – « My travel buddy » avec IA (facultatif)

Sans rien configurer, le Travel buddy répond déjà à partir des données Angor (avis officiels, incidents,
fiches pays), sans IA. Pour des réponses rédigées par Claude, il faut un petit relais gratuit qui garde
la clé Anthropic à l'abri (le site étant public, la clé ne peut pas y figurer).

1. Créez un compte gratuit sur https://dash.cloudflare.com (aucune carte bancaire).
2. **Workers & Pages** → **Create** → **Create Worker** → nom `angor-buddy` → **Deploy**.
3. **Edit code** : remplacez tout le contenu par celui de `tools/buddy-worker.js` → **Deploy**.
4. **Settings** → **Variables and Secrets** :
   - `ANTHROPIC_API_KEY` (type *Secret*) : votre clé Anthropic ;
   - `ALLOWED_ORIGINS` : `https://angor.fr,https://www.angor.fr` ;
   - `DAILY_LIMIT` : `150` ; `USER_LIMIT` : `20`.
5. **Storage & Databases** → **KV** → **Create** `angor-quota`, puis dans le Worker **Settings** → **Bindings** →
   **KV namespace**, nom de variable `QUOTA` (limite les abus et donc les coûts).
6. Copiez l'adresse du Worker (ex. `https://angor-buddy.<vous>.workers.dev`) dans `config/settings.json` :
   `"ai_url": "https://angor-buddy.<vous>.workers.dev"`, puis **publier.bat**. Le même relais sert au Travel buddy,
   à l'avis go/no-go et à la synthèse du brief.

Coût : environ 0,5 centime par question avec Claude Haiku ; avec `DAILY_LIMIT` = 150, 1 $ par jour au maximum.

---

## Partie F – Point quotidien, pays suivis et mode analyste

### F1. Point quotidien sur Telegram
Rien à installer : il part sur le même canal que les alertes, une fois par jour à partir de 5 h UTC (7 h à Paris l'été).
Réglages dans `config/settings.json` → `"digest"` :
- `hour_utc` : heure d'envoi (UTC) ;
- `countries` : vos pays suivis, ex. `["ML", "NG", "UA"]` (vide = vue monde) ;
- `enabled` : `false` pour le couper.

Le plus simple pour remplir `countries` : sur la carte, cliquez sur l'étoile des pays à suivre (fiche pays), puis onglet
**Pays** → **Copier pour Telegram**, collez la liste dans `countries`, et double-cliquez sur **publier.bat**.

### F2. Alertes Pulse
`config/settings.json` → `"pulse"` : alerte Telegram si l'indice de stabilité d'un pays chute d'au moins `drop_alert`
points en 7 jours, ou passe sous `threshold`. `countries` vide = tous les pays. Au démarrage, il faut quelques jours
d'historique avant les premières tendances.

### F3. Mode analyste (« Vérifié Angor »)
1. Ouvrez `https://angor.fr/?analyste=1` (le mode reste actif dans ce navigateur ; bouton **Quitter** pour en sortir).
2. Sur un incident : **Valider**, **Corriger** (gravité, catégorie) ou **Infirmer**, avec une note (source de confirmation).
3. Bouton **Exporter verified.json** → remplacez `config/verified.json` par le fichier téléchargé → **publier.bat**.
Les incidents validés portent le badge « Vérifié Angor » et la cote 1 ; les incidents infirmés disparaissent de la carte,
des alertes et des calculs.

### F4. Liens et vues
Bouton **Partager** : copie l'adresse de la vue affichée (période, filtres, calque, zoom, fiche ouverte).
Bouton **Vues** : enregistre des vues dans votre navigateur (ex. « Sahel – 7 j »).

---

## Partie G – Brancher l'IA (API Anthropic), quand toutes les fonctionnalités sont prêtes

Tout est déjà câblé : sans clé, l'outil utilise ses textes automatiques ; avec la clé, chaque usage s'active.

1. **Clé** : https://console.anthropic.com → **API Keys** → **Create Key**. Dans **Limits**, fixez un plafond mensuel
   (ex. 25 $) : c'est la vraie sécurité financière.
2. **Robot** (résumés d'incidents, chronologies, explications du Pulse, « L'essentiel du jour ») :
   ```
   gh secret set ANTHROPIC_API_KEY
   ```
3. **Carte** (Travel buddy, avis go/no-go, synthèse du brief) : relais Cloudflare, partie E (clé à mettre dans le Worker,
   jamais dans le site), puis `"ai_url"` dans `config/settings.json`.
4. **Réglages** (`config/settings.json` → `"ai"`) :
   - `monthly_budget_usd` : budget interne du robot, lissé jour par jour (20 $ par défaut) ;
   - `tasks` : `event_summaries`, `crisis_summaries`, `digest_editorial`, `pulse_explanations` (true / false) ;
   - `max_calls_per_run` : nombre maximal d'appels par collecte hors résumés d'incidents (12).
5. **publier.bat**. Les textes rédigés par l'IA sont toujours signalés « IA – à vérifier ».

Ordre de grandeur avec Claude Haiku : 10 à 20 $ par mois pour le robot, moins de 1 $ par jour pour la carte
(quota de 150 questions par jour dans le Worker).

## Partie H – Comptes clients, administration, safety check et application Android

Sans cette partie, la carte fonctionne comme avant (sans compte). Comptez **≈ 1 h 15** la première fois, dont 30 min pour les e-mails.
Résultat : vos clients créent un compte sur angor.fr/compte.html, acceptent les CGU (preuve horodatée), confirment leur adresse ;
vous validez chaque compte depuis angor.fr/admin.html.

> Règle d'or : **seules** l'adresse du projet et la clé **publique** (« anon » ou « publishable ») vont dans `config/settings.json`.
> La clé `service_role` / « secret », le mot de passe de la base et la clé SMTP ne sont **jamais** copiés dans un fichier du projet,
> dans le site ou dans un message (pas même à Claude).

### H1. Créer le projet Supabase (10 min)

1. https://supabase.com → **Start your project** → connectez-vous avec votre compte GitHub.
2. Activez tout de suite la **double authentification** de votre compte Supabase (photo de profil → **Account preferences → Security**).
   Faites de même sur GitHub si ce n'est pas déjà le cas : ces deux comptes donnent accès aux données de vos clients.
3. **New project** :
   - Organisation : `Angor` (offre **Free** pour la bêta) ;
   - Nom : `angor` ;
   - Mot de passe de la base : **Generate a password**, puis rangez-le dans votre gestionnaire de mots de passe ;
   - Région : **Europe – Paris (eu-west-3)** (données hébergées en France, comme l'annonce la politique de confidentialité).
4. Attendez 2 minutes que le projet soit prêt.

### H2. Installer (ou mettre à jour) la base (5 min)

1. **SQL Editor** → **New query** → collez tout le fichier `supabase/schema.sql` → **Run**. Message attendu : *Success. No rows returned*.
2. **Advisors → Security Advisor** : aucune erreur rouge. Il reste **deux avertissements attendus** (« Signed-In Users Can Execute
   SECURITY DEFINER Function ») pour `admin_set_status` et `delete_my_account` : ces deux fonctions doivent pouvoir être appelées
   par un utilisateur connecté et vérifient elles-mêmes qui les appelle. Tout autre avertissement : prévenir Claude.
   Le message *pg_cron* éventuel signifie que l'entretien nocturne n'a pas pu être planifié : **Database → Extensions** →
   activez **pg_cron**, puis relancez le script.
3. **À chaque nouvelle version** de `schema.sql` (indiquée dans le CHANGELOG), recommencez l'étape 1 : le script se relance sans
   rien effacer.

### H3. Réglages de connexion (10 min)

1. **Authentication → Sign In / Providers** :
   - **Email** : activé ; **Confirm email** : activé ; **Secure email change** : activé ;
   - **Minimum password length** : `10` ; **Password requirements** : lettres et chiffres ;
   - désactivez **Allow anonymous sign-ins** et les autres fournisseurs (Google, etc.) que vous n'utilisez pas.
2. **Authentication → URL Configuration** :
   - **Site URL** : `https://angor.fr`
   - **Redirect URLs** : ajoutez `https://angor.fr/compte.html` (et `http://localhost:8000/compte.html` pour vos essais sur le PC).
3. **Authentication → Rate Limits** : laissez les valeurs par défaut ; après l'étape H4, réglez *emails sent* sur `30` par heure.

### H4. Serveur d'envoi (SMTP) puis e-mails en français (30 min)

Supabase n'autorise la modification des modèles d'e-mails (objet et texte) **qu'après** le branchement d'un serveur d'envoi
(« custom SMTP ») : sans lui, la page des modèles affiche *Set up custom SMTP to edit templates* et les textes restent en anglais.
Son serveur intégré n'envoie de toute façon que **quelques e-mails par heure** et sert seulement aux essais.

> **Pas pressé ?** Vous pouvez sauter H4 pour l'instant, faire H5 et H6 avec les e-mails anglais par défaut (quelques
> inscriptions de test par heure), et revenir ici avant d'ouvrir l'inscription à vos clients.

**H4.1 – Compte Brevo** (société française, offre gratuite suffisante pour les e-mails de connexion)
1. https://www.brevo.com → **S'inscrire gratuitement** (votre adresse habituelle convient) ; renseignez le profil demandé.
   Brevo peut demander quelques informations sur votre activité avant d'autoriser l'envoi : répondez « e-mails
   transactionnels (confirmation d'inscription, mot de passe) pour une application ».

**H4.2 – Authentifier le domaine angor.fr** (indispensable pour envoyer depuis `no-reply@angor.fr` sans finir en indésirables)
1. Brevo → **Paramètres → Expéditeurs, domaines et IP → Domaines → Ajouter un domaine** → `angor.fr`.
2. Si votre domaine est chez **Cloudflare** ou **OVH**, choisissez la **configuration automatique** : Brevo se connecte à
   votre compte et crée lui-même les enregistrements (chez Cloudflare, désactivez le *CNAME flattening* si Brevo le signale).
   Sinon, recopiez dans la zone DNS de votre registraire les 3 enregistrements affichés : **code Brevo** (TXT), **DKIM**
   (CNAME ou TXT), **DMARC** (TXT).
3. **Authentifier** : de quelques minutes à quelques heures. Le domaine doit apparaître comme authentifié.

**H4.3 – Identifiants SMTP**
1. Brevo → https://app.brevo.com/settings/keys/smtp (**Paramètres → SMTP et API → SMTP**).
2. Notez le **serveur** (`smtp-relay.brevo.com`), le **port** (`587`) et l'**identifiant** (de la forme `xxxxxx@smtp-brevo.com`).
3. **Générer une nouvelle clé SMTP** (nom : `supabase`) et copiez-la : elle ne sera plus affichée. Attention : c'est une clé
   **SMTP**, pas une clé API. Elle ne va **que** dans Supabase (étape suivante), jamais dans un fichier ni un message.

**H4.4 – Brancher Supabase**
1. Supabase → **Authentication → Emails** → bouton **Set up SMTP** (ou onglet **SMTP Settings**) → **Enable custom SMTP** :
   - Sender email : `no-reply@angor.fr` ; Sender name : `Angor Intelligence` ;
   - Host : `smtp-relay.brevo.com` ; Port : `587` ;
   - Username : l'identifiant `xxxxxx@smtp-brevo.com` ; Password : la clé SMTP ;
   - **Save**.
2. **Authentication → Rate Limits** : *Rate limit for sending emails* : `30` par heure.

**H4.5 – Modèles en français** (la page des modèles est maintenant modifiable)
**Authentication → Emails → Templates**. Pour chaque modèle : ouvrez le fichier correspondant de `supabase/templates/`
dans VS Code, copiez **tout** son contenu, collez-le dans **Body** (onglet **Source**), recopiez l'objet indiqué en tête du
fichier dans **Subject**, puis **Save**.

| Modèle Supabase | Fichier | Objet |
|---|---|---|
| Confirm signup | `confirmation.html` | Confirmez votre adresse – Angor Intelligence |
| Reset password | `recovery.html` | Réinitialisation de votre mot de passe – Angor Intelligence |
| Change email address | `email_change.html` | Confirmez votre nouvelle adresse – Angor Intelligence |
| Invite user | `invite.html` | Invitation à rejoindre Angor Intelligence |
| Magic Link | `magic_link.html` | Votre lien de connexion – Angor Intelligence |

**H4.6 – Déclarer le prestataire** : dites à Claude « Brevo est branché » : il complète la ligne « Envoi des e-mails » des
sous-traitants dans `config/legal.json` (la politique de confidentialité se met à jour toute seule).

### H5. Brancher le site (5 min)

1. Supabase → **Project Settings → API Keys** : copiez l'adresse du projet (**Project URL**, `https://xxxx.supabase.co`) et la clé
   **publique** (onglet *Legacy* : `anon public`, ou nouvelle clé `sb_publishable_…` : les deux fonctionnent).
2. Dans `config/settings.json`, section `accounts` (ne touchez pas au reste du fichier) :
   ```json
   "accounts": { "supabase_url": "https://xxxx.supabase.co", "supabase_anon_key": "eyJ… ou sb_publishable_…", "vapid_public_key": "" }
   ```
   Cette clé est publique par nature : la sécurité repose sur les règles d'accès installées à l'étape H2.
3. **publier.bat**. Cinq minutes plus tard, https://angor.fr/compte.html affiche **Connexion / Créer un compte**.

### H6. Devenir administrateur et tester le parcours complet (10 min)

1. https://angor.fr/compte.html → **Créer un compte** avec votre adresse → cochez l'acceptation des CGU → confirmez l'e-mail reçu.
2. **SQL Editor** (une seule fois, avec votre adresse) :
   ```sql
   update public.profiles set role = 'admin', status = 'approved', approved_at = now()
    where email = 'votre-adresse@exemple.fr';
   ```
   **Administration** apparaît alors dans Mon compte et dans le menu Plus de la carte.
3. **Testez le parcours d'un client** avec une seconde adresse (personnelle) : inscription → e-mail de confirmation en français →
   compte « en attente » → validation dans https://angor.fr/admin.html (colonne **Conditions** : version des CGU acceptée et date)
   → connexion → **Mot de passe oublié** → e-mail de réinitialisation.

### H7. Sécurité et exploitation (à lire une fois)

- **Mise en pause de l'offre gratuite** : un projet sans activité pendant 7 jours est mis en pause. Le robot de collecte envoie un
  signe de vie toutes les 30 minutes, ce qui l'en empêche. Si le projet est malgré tout en pause : tableau de bord Supabase →
  **Restore project**.
- **Entretien automatique** : chaque nuit (3 h 17 UTC), la base efface elle-même les données arrivées à expiration (réponses aux
  safety checks après 12 mois, position après 30 jours, demandes jamais validées après 6 mois), comme l'annonce la politique de
  confidentialité. Contrôle : **Integrations → Cron** (tâche `angor-housekeeping`).
- **Sauvegardes** : l'offre gratuite n'inclut pas de sauvegarde restaurable (vérifiez la page *Pricing*). **Avant le premier client
  payant**, passez en offre **Pro** (≈ 25 $ par mois, sauvegardes quotidiennes, pas de mise en pause) – c'est le premier poste du
  plan « Réinvestir ».
- **Accord de traitement (DPA)** : il est accepté automatiquement avec les conditions de Supabase. Téléchargez-en une copie
  (supabase.com → Legal → DPA) et gardez-la avec votre registre des traitements (`doc/RGPD.md`).
- **Comptes inactifs** : une fois par an, dans Supabase → **Authentication → Users** (colonne *Last sign in*), repérez les comptes
  inutilisés depuis 3 ans, prévenez-les par e-mail puis supprimez-les (engagement de la politique de confidentialité).

### H8. Notifications des safety checks (Web Push)

1. Générez une paire de clés VAPID (une seule fois, sur votre PC avec Node.js) :
   ```
   npx web-push generate-vapid-keys
   ```
   - la **clé publique** va dans `config/settings.json` → `accounts.vapid_public_key` ;
   - la **clé privée** ne va que dans les secrets Supabase (étape suivante).
2. Installez l'outil Supabase (`npm i -g supabase`), puis dans le dossier du projet :
   ```
   supabase login
   supabase link --project-ref xxxx
   supabase secrets set VAPID_PUBLIC_KEY=… VAPID_PRIVATE_KEY=… VAPID_SUBJECT=mailto:contact@angor.fr
   supabase functions deploy safety-push
   ```
   (`xxxx` = identifiant du projet, visible dans l'adresse du projet Supabase.)
3. **publier.bat**. Sur votre téléphone : Mon compte → **Notifications sur cet appareil**.
   Test : admin.html → Safety checks → titre « Test », zone « Tous », durée 1 h → Envoyer.

Sans l'étape H8, les safety checks fonctionnent quand même : bandeau à l'ouverture de l'application, sans notification.

### H9. Application Android (Google Play)

L'application Android est la carte elle-même, emballée (« Trusted Web Activity ») : chaque publication met l'application à jour,
sans nouvelle version à soumettre.

1. Testez d'abord sans Play Store : sur Android, Chrome → angor.fr → menu ⋮ → **Installer l'application**.
2. https://www.pwabuilder.com → saisissez `https://angor.fr` → **Package for stores → Android** →
   identifiant de paquet `fr.angor.app` → téléchargez le paquet (fichier `.aab` + clé de signature : **conservez la clé**,
   elle est indispensable pour toute mise à jour).
3. Copiez `tools/assetlinks.example.json` vers `docs/.well-known/assetlinks.json` et remplacez l'empreinte par la valeur
   **SHA-256** fournie par PWABuilder (ou par Google Play → Intégrité de l'application → Signature). **publier.bat.**
   Sans ce fichier, l'application affiche une barre d'adresse.
4. Compte développeur Google Play (frais uniques ≈ 25 $) → **Créer une application** → envoyez le `.aab`.
   Commencez en **test interne** (jusqu'à 100 testeurs par e-mail) : c'est le bon format pour la bêta.
   Fiche Play : politique de confidentialité obligatoire : https://angor.fr/confidentialite.html.

iOS : même principe plus tard (PWABuilder → iOS, compte Apple Developer ≈ 99 $/an). En attendant, sur iPhone, Safari →
Partager → **Sur l'écran d'accueil** donne déjà l'application et, depuis iOS 16.4, les notifications.

### Limite actuelle et prochaine étape

Les comptes protègent les **données personnelles** (profil, préférences, réponses aux safety checks), pas la carte :
les données d'incidents restent publiques sur angor.fr. Prochaines évolutions, avant la commercialisation :
**espaces clients** (une organisation, son référent, ses utilisateurs, son offre et sa période d'abonnement, invitations),
fonctions « Résilier mon abonnement » et « Renoncer au contrat ici » prévues par les CGV, puis carte réservée aux comptes validés.

## Partie I – Rapports et alerte précoce (rien à installer)

Les deux onglets se remplissent seuls après **publier.bat** :
- **Rapports** : premiers titres dès la collecte suivante, puis mise à jour toutes les 3 heures (`config/reports.json` pour ajouter un
  producteur ou un rapport à la main, section `"manual"`).
- **Alerte précoce** : limites administratives et données humanitaires à la première collecte ; le climat NASA POWER arrive
  par lots de 30 unités par collecte (≈ 4 heures pour les 230 unités des deux régions). Ajouter une région : `config/early_warning.json`.

Pour aller plus loin (facultatif) :
- **ReliefWeb** (rapports de situation de l'ONU et des ONG, par pays) : demander un nom d'application gratuit sur
  https://apidoc.reliefweb.int, le mettre dans le secret GitHub `RELIEFWEB_APPNAME`, puis `"enabled": true` pour `reliefweb`
  dans `config/sources.json`.
- **HDX HAPI** : l'identifiant d'application par défaut est générique ; vous pouvez générer le vôtre (nom + e-mail) sur
  https://hapi.humdata.org/docs et le mettre dans `config/early_warning.json` → `hapi_app_identifier`.
- **Presse régionale française** : 6 titres ajoutés (Télégramme, Progrès, DNA, Est Républicain, Dauphiné, La 1ère) sans
  vérification possible depuis l'atelier ; ceux qui ne répondent pas passent en pause (voir « État des sources »).


## Partie J – Bouton « Actualiser » : collecte immédiate (facultatif, nécessite la partie H)

Sans cette partie, le bouton ⟳ recharge simplement les dernières données publiées et indique l'heure de la prochaine
collecte automatique. Avec elle, un utilisateur connecté et validé peut lancer une collecte tout de suite (≈ 5 min).
Garde-fous : une seule collecte à la fois, et au plus une demande toutes les 10 minutes pour tout le monde.

1. GitHub → photo de profil → **Settings → Developer settings → Personal access tokens → Fine-grained tokens →
   Generate new token** : nom « angor-actualiser », expiration 1 an, **Only select repositories** → `angor-intelligence`,
   **Repository permissions → Actions : Read and write**. Copiez le jeton (il ne sera plus affiché).
2. Dans le dossier du projet :
   ```
   supabase secrets set GITHUB_TOKEN=… GITHUB_REPO=Slift42/angor-intelligence GITHUB_WORKFLOW=collecte.yml
   supabase functions deploy trigger-collect
   ```
3. **publier.bat**. Le jeton ne quitte jamais Supabase : il n'est ni dans le site ni dans le dépôt.

## Traduction automatique

- **Dans le navigateur** (Chrome et Edge récents, sur ordinateur) : les titres sont traduits sur l'appareil, gratuitement,
  sans rien envoyer à un tiers. La première fois, le navigateur télécharge le modèle de langue au premier clic.
  Bouton 文A pour activer ou couper la traduction.
- **Pour tous les navigateurs** (Firefox, Safari, mobile) : dès que la clé Anthropic est branchée (partie G), le robot traduit
  chaque titre en français et en anglais pendant l'analyse (coût négligeable : même appel que le résumé).
- Sinon, la fiche d'un incident propose un lien « Traduire avec Google ».
