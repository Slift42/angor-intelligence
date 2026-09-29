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
Claude modifie les fichiers sur votre PC → vous double-cliquez **`publier.bat`** (depuis l'Explorateur Windows). Le robot publie la nouvelle version à sa prochaine exécution (ou lancez **Run workflow**).

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
- Avant toute ouverture publique : CGU « outil d'aide à la décision, sans garantie d'exhaustivité » et vérification de votre contrat de travail.

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
- **Prestataires locaux vérifiés** : `config/providers_local.json` puis `python tools/providers_src.py`.

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
   `"buddy_url": "https://angor-buddy.<vous>.workers.dev"`, puis **publier.bat**.

Coût : environ 0,5 centime par question avec Claude Haiku ; avec `DAILY_LIMIT` = 150, 1 $ par jour au maximum.
