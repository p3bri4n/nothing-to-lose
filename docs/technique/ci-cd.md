# CI/CD et infrastructure GitHub

*Mise à jour : 2026-11-07 (étape E9 du jalon PP : CI alignée sur mise, actions épinglées par SHA, contrôle de la liste de contrôle branché)*

Décisions : [0001](../decisions/0001-terraform-pour-github.md), [0002](../decisions/0002-etat-terraform-local.md), [0003](../decisions/0003-depot-public.md), [0004](../decisions/0004-cloudflare-pages.md).

## Vue d'ensemble

| Élément | Où | Rôle |
|---|---|---|
| Configuration GitHub | `infra/terraform/` | Dépôt, ruleset, permissions des actions, variables, environnement `production`, secrets, labels |
| CI sans GPU | `.github/workflows/ci.yml` | Job `ci-cpu` : outils de mise, versions, secrets, liens, formatage, actionlint, Terraform, tests des outils, liste de contrôle des PR ; puis Rust, WASM, Python, viewer, `just check` quand ils existent |
| Évaluation GPU | `.github/workflows/gpu-eval.yml` | `just eval` avec Laya et le LLM, sur le runner auto-hébergé |
| Déploiement | `.github/workflows/deploy-viewer.yml` | Viewer de replays sur Cloudflare Pages |
| En-têtes du viewer | `web/viewer/public/_headers` | COOP/COEP, nécessaires au multithread WebAssembly |

## Terraform

**Prérequis** : Terraform ≥ 1.6, un jeton GitHub avec les droits d'administration du dépôt (jeton à granularité fine : *Administration*, *Actions*, *Secrets*, *Variables*, *Environments*, *Issues* en lecture/écriture), exporté dans `GITHUB_TOKEN`.

```bash
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars   # puis compléter
export GITHUB_TOKEN=...      # jamais dans un fichier du dépôt
just tf-init                 # état dans ~/.local/share/terraform/nothing-to-lose/ (TF_STATE_PATH pour changer)
just tf-plan
just tf-apply                # réservé à l'utilisateur
```

**Premier lancement** : `terraform apply` crée le dépôt vide (`auto_init = false`). Ensuite, depuis le dépôt local :

```bash
git remote add origin "$(cd infra/terraform && terraform output -raw repository_ssh_url)"
git push -u origin main
```

**Piège du premier `apply` (constaté le 2026-11-07)** : GitHub crée des labels par défaut dans tout nouveau dépôt (`bug`, `documentation`, `duplicate`, `enhancement`…). Le label `bug` de `labels.tf` échoue alors en `422 already_exists`. Supprimer le label par défaut (`curl -X DELETE -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/repos/<propriétaire>/nothing-to-lose/labels/bug`, code `204`), puis relancer `just tf-apply` : Terraform reprend où il s'est arrêté.

Si le dépôt existe déjà sur GitHub : `terraform import github_repository.main nothing-to-lose` avant le premier `apply` (commande réservée à l'utilisateur).

**État** : local, hors du dépôt. Il contient les valeurs des secrets fournis à Terraform : le sauvegarder dans un endroit sûr et chiffré.

**Points à vérifier au premier `plan`** :
- `actor_id = 5` dans `ruleset.tf` (rôle de dépôt « admin » pour le contournement d'urgence) ;
- disponibilité de `security_and_analysis` sur un dépôt public personnel.

## Ruleset de la branche principale

Passage obligatoire par une pull request (0 approbation requise, conversations résolues), check `ci-cpu` obligatoire et à jour, historique linéaire, ni suppression ni force-push. Le propriétaire peut contourner les règles en cas d'urgence.

## CI sans GPU (`ci.yml`)

Déclenchée sur les pull requests (`opened`, `edited`, `synchronize`, `reopened`) et sur chaque push vers `main`. Le déclencheur `edited` relance le job quand la description de la PR change, pour que le contrôle de la liste de contrôle voie le corps à jour. Permissions : `contents: read`. Job unique **`ci-cpu`** (nom inchangé : c'est le check obligatoire du ruleset, `required_ci_check` dans Terraform), sur `ubuntu-24.04` (version figée, pas `ubuntu-latest`), délai de 30 minutes.

### Outils : mise, comme en local

Le job ne préinstalle plus rien avec des actions spécifiques à un langage (`dtolnay/rust-toolchain`, `astral-sh/setup-uv`, `actions/setup-node` et `extractions/setup-just` ont disparu de `ci.yml`). `jdx/mise-action` installe mise (version figée dans le workflow : `version: 2026.11.0`, car mise n'est pas dans `mise.toml`) puis tous les outils de [`mise.toml`](../../mise.toml), qui prennent la priorité sur ceux préinstallés sur le runner. Rust vient donc de mise (avec `rustfmt`, `clippy` et la cible `wasm32-unknown-unknown`), conformément à `rust-toolchain.toml`. L'étape `just versions` (avec `CI=true`, fourni par GitHub : mode `--ci`, qui ignore Claude Code) prouve que les versions de la CI sont celles de `mise.toml` (critère C4).

- **Cache** : `cache: true` (cache GitHub des outils, clé dérivée de `mise.toml`, reconstruit au plus tous les 30 jours).
- **Jeton** : `github_token: ${{ secrets.GITHUB_TOKEN }}` pour les téléchargements d'outils hébergés sur GitHub (limites de débit de l'API, risque R11). Vérifié dans le `action.yml` du SHA épinglé (`82a612c…`) : l'entrée `github_token` existe (par défaut `${{ github.token }}`, donc la ligne explicite est redondante mais documente l'intention) et `persist_github_token` vaut `"false"` par défaut, ce qui garde le jeton local à l'action. Les autres entrées utilisées existent aussi : `version`, `cache`, `install_args`, `cache_key_prefix`. À revérifier dans le `action.yml` du nouveau SHA à chaque montée de version de l'action.
- **Historique complet** : `actions/checkout` avec `fetch-depth: 0`, car `gitleaks git` parcourt tout l'historique (lecture locale du dépôt, sans réseau). `persist-credentials: false` (dans les trois workflows) : le jeton n'est pas laissé dans `.git/config` ; aucune étape ne pousse ni ne récupère après le checkout.
- **Version de mise : exception à la règle des deux semaines.** Les actions et outils sont choisis parmi les releases publiées depuis au moins deux semaines. `version: 2026.11.0` (mise lui-même) fait exception : c'est la version **installée en local**, et CI et local doivent rester identiques. Le choix de `jdx/mise-action` v5.2.3 (et non v5.2.6, plus récente) découle de la règle des deux semaines : v5.2.3 est la dernière release de l'action publiée depuis plus de deux semaines au 2026-11-07.
- **Concurrence** : `cancel-in-progress` n'est actif que pour les pull requests (un nouveau push annule l'exécution devenue inutile) ; sur `main`, chaque push va au bout (pas d'annulation d'un contrôle de `main`).

### Étapes, dans l'ordre

| Étape | Commande | Condition |
|---|---|---|
| Versions des outils | `just versions` | toujours |
| Secrets | `just secrets-scan` | toujours |
| Liens internes de la documentation | `just docs-links` | toujours |
| Formatage | `just fmt-check` | toujours |
| Workflows | `just actionlint` | toujours |
| Terraform | `terraform -chdir=infra/terraform init -backend=false -input=false -lockfile=readonly`, puis `just tf-check` | toujours (aucun backend, état ni jeton nécessaires ; `-lockfile=readonly` : `.terraform.lock.hcl` fait foi, l'init échoue s'il devait être modifié) |
| Tests des outils du dépôt | `just tools-test` | toujours |
| Cache Rust (`Swatinem/rust-cache`), `cargo fmt`, `clippy`, `cargo test` | | `Cargo.toml` à la racine |
| Compilation `wasm32-unknown-unknown` | | `crates/wasm/Cargo.toml` |
| `ruff`, `pytest` (via `uv`) | | `pyproject.toml` à la racine |
| `npm ci`, `npm run build` du viewer | | `web/viewer/package.json` |
| `just check` | | `Cargo.toml` à la racine |
| **Liste de contrôle de la PR** (dernière étape du job) | `python3 tools/check_pr_checklist.py` | `github.event_name == 'pull_request'` (et `!cancelled()`, voir ci-dessous) |

Les étapes Rust, Python et Node utilisent les outils de mise (`cargo`, `uv`, `node`, `npm`) et `UV_PYTHON_DOWNLOADS=never` (section `[env]` de `mise.toml`). Le cache npm de l'ancien `setup-node` n'existe plus ; il pourra être rétabli avec `actions/cache` quand `web/viewer/package.json` existera.

### Contrôle de la liste de contrôle (bloquant)

Décision D4 du plan PP : une PR dont la section « Liste de contrôle » contient une case décochée fait **échouer** `ci-cpu`, donc bloque la fusion. Le corps et l'auteur de la PR passent par `env:` (`PR_BODY`, `PR_AUTHOR`), **jamais** par une expression `${{ }}` dans un `run:` (injection de script, risque R10 ; le dépôt est public). Les PR de `dependabot[bot]` sont exemptées. L'étape est la **dernière** du job et porte `if: ${{ !cancelled() && github.event_name == 'pull_request' }}` : elle s'exécute même si une étape précédente a échoué, pour que l'auteur voie tous les problèmes en une fois (elle doit rester en dernier : sans cela, une étape ajoutée après elle serait ignorée en cas d'échec du contrôle). Elle ne s'exécute pas sur les push vers `main`. Détails du script et du modèle : [`modeles-github.md`](modeles-github.md).

Les tests qui dépendent de Laya ou du LLM utilisent des doublures (réponses enregistrées) en CI ; les vrais modèles ne tournent que dans `gpu-eval.yml`.

## Actions utilisées, épinglées par SHA

Toutes les actions de `.github/workflows/` sont référencées par le SHA de leur commit (40 caractères), avec la version en commentaire. Versions choisies le 2026-11-07 : dernière release stable publiée depuis au moins deux semaines ; SHA obtenus par l'API GitHub (`git/ref/tags/<tag>`, avec déréférencement des tags annotés) et recontrôlés par `gh api repos/<dépôt>/commits/<sha>` (ce recontrôle seul ne prouve rien, voir la procédure ci-dessous). Exception : la version de mise elle-même, voir plus haut.

| Action | Version | SHA | Workflows | Autorisation (`actions.tf`) |
|---|---|---|---|---|
| `actions/checkout` | v7.0.1 (2026-07-20) | `3d3c42e5aac5ba805825da76410c181273ba90b1` | ci, deploy-viewer, gpu-eval | éditeur GitHub |
| `jdx/mise-action` | v5.2.3 (2026-10-24) | `82a612c5ab8bcda7cc5db6b7e81a8e7584c3dc6e` | ci, deploy-viewer | `jdx/mise-action@*` |
| `Swatinem/rust-cache` | v2.9.3 (2026-10-20) | `d1527c8f67ef9af357290475d4af4b0fab8f12e0` | ci | `Swatinem/rust-cache@*` |
| `actions/upload-artifact` | v7.0.2 (2026-10-07) | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` | gpu-eval | éditeur GitHub |
| `cloudflare/wrangler-action` | v4.1.3 (2026-09-24) | `953926a2e2182532811c01a25e53647d93bf07c0` | deploy-viewer | `cloudflare/wrangler-action@*` |

`actions.tf` n'a pas été modifié : `dtolnay/rust-toolchain`, `extractions/setup-just` et `astral-sh/setup-uv` y restent autorisées alors qu'aucun workflow ne les utilise (leur retrait est laissé à une PR ultérieure, pour ne pas multiplier les `apply`). Mettre à jour une action :

1. choisir la release (publiée depuis au moins deux semaines) ;
2. **obtenir le SHA par la résolution du tag** : `gh api repos/<dépôt>/git/ref/tags/<tag>`. Si `object.type` vaut `tag` (tag annoté), déréférencer : `gh api repos/<dépôt>/git/tags/<sha-du-tag>` et prendre `object.sha`. `gh api repos/<dépôt>/commits/<sha>` seul **ne prouve rien** : GitHub sert aussi les commits des forks sous l'adresse du dépôt, un SHA piégé y répondrait normalement ;
3. remplacer SHA et commentaire dans **tous** les workflows qui l'utilisent, et mettre à jour ce tableau ;
4. lancer `just actionlint` et `just tools-test` (`tools/tests/test_workflows.py` vérifie l'épinglage, la version unique de mise, l'absence de `pull_request` dans `gpu-eval.yml` et la présence du job `ci-cpu`).

## Évaluation GPU (`gpu-eval.yml`)

- **Runner auto-hébergé** sur la machine de développement, avec les labels `self-hosted`, `linux`, `gpu`. Enregistrement manuel : *Settings → Actions → Runners → New self-hosted runner*, en ajoutant le label `gpu`. Le faire tourner sous un utilisateur dédié, sans droits d'administration, idéalement dans un conteneur.
- **Sécurité, dépôt public** : jamais déclenché par `pull_request` ; seulement sur push vers `main` (protégée) ou lancement manuel, et seulement si l'auteur de l'action est le propriétaire du dépôt. Déclencheurs et garde `if` inchangés par E9 : seuls les actions (épinglées par SHA), `persist-credentials: false` et le passage de `inputs.seeds` par `env:` (validé par `[[ "$SEEDS" =~ ^[0-9]+$ ]]`, jamais par une expression dans `run:`, risque R10) ont changé. Mise n'est **pas** installé sur ce runner (il fournit lui-même `just` et le reste de l'environnement).
- **Risque connu, non couvert** : la garde de `gpu-eval.yml` ne protège que ce workflow. Une pull request d'un fork peut modifier `ci.yml` pour viser `runs-on: [self-hosted, gpu]` : le workflow modifié de la PR s'exécuterait alors sur le runner. Décision à instruire **avant P2** (activation de `GPU_EVAL_ENABLED` et enregistrement du runner) : exiger l'approbation des workflows des contributeurs de forks (réglage Actions, via Terraform) et/ou un runner éphémère et isolé. Sans runner enregistré, le risque est nul.
- **Interrupteur** : variable `GPU_EVAL_ENABLED`, gérée par Terraform (`gpu_eval_enabled`), à passer à `true` au jalon P2.
- Le rapport (`reports/report.md`, `summary.json`, `violations.txt`) est publié comme artefact du workflow.

## Déploiement (`deploy-viewer.yml`)

- Node vient de mise (`jdx/mise-action` avec `install_args: node`, donc seul Node est installé, et `cache_key_prefix: mise-v1-deploy` pour ne pas mélanger ce cache « node seul » avec celui de `ci-cpu`) ; `runs-on: ubuntu-24.04` ; permissions et déclencheurs inchangés.
- Cible : **Cloudflare Pages**, qui accepte les en-têtes COOP/COEP via `web/viewer/public/_headers`.
- **Interrupteur** : variable `DEPLOY_ENABLED` (Terraform `deploy_enabled`), à activer au jalon du replay public.
- Secrets `CLOUDFLARE_API_TOKEN` et `CLOUDFLARE_ACCOUNT_ID` : uniquement dans l'environnement `production`, utilisable seulement depuis `main`. Créés par Terraform quand les variables correspondantes sont renseignées.
- **`wrangler-action` v3 → v4 : à valider avant d'activer le déploiement** (lire le changelog, figer `wranglerVersion`, faire un essai de déploiement). Le workflow est épinglé sur v4.1.3 mais n'a jamais tourné.
- **À faire avant activation** : créer le projet Pages (`npx wrangler pages project create nothing-to-lose`, ou plus tard via le provider Terraform Cloudflare, dont le schéma est à vérifier par `chercheur-web`), et créer un jeton Cloudflare limité à *Pages : édition*.

## Validation locale

```bash
just lint                                                      # versions, tools-test, fmt-check, docs-links, secrets-scan, actionlint, tf-check
just actionlint                                                # workflows (config : .github/actionlint.yaml)
```

`just tf-check` suppose un `terraform init` déjà fait (`just tf-init` en local avec l'état ; `terraform -chdir=infra/terraform init -backend=false` suffit pour valider sans état ni jeton, comme en CI). Le contrôle de la liste de contrôle est branché dans `ci.yml` : voir [`modeles-github.md`](modeles-github.md).

**Points de vigilance** : la première exécution de `ci-cpu` sur un cache vide installe tous les outils de `mise.toml` (Rust, Node, Python, Terraform…), ce qui est long ; les suivantes utilisent le cache. L'effet réel des SHA et du cache ne se vérifie que sur une vraie pull request.
