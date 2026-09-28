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
