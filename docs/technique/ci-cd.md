# CI/CD et infrastructure GitHub

*Mise à jour : 2026-11-05 (renommage du dépôt et du projet en `nothing-to-lose`, voir [0016](../decisions/0016-nom-nothing-to-lose.md))*

Décisions : [0001](../decisions/0001-terraform-pour-github.md), [0002](../decisions/0002-etat-terraform-local.md), [0003](../decisions/0003-depot-public.md), [0004](../decisions/0004-cloudflare-pages.md).

## Vue d'ensemble

| Élément | Où | Rôle |
|---|---|---|
| Configuration GitHub | `infra/terraform/` | Dépôt, ruleset, permissions des actions, variables, environnement `production`, secrets, labels |
| CI sans GPU | `.github/workflows/ci.yml` | Job `ci-cpu` : liens de la doc, Rust, WASM, Python, viewer, `just check` |
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

Déclenchée sur chaque pull request et chaque push sur `main`. Chaque étape ne s'exécute que si la partie du projet existe (`hashFiles(...)`), ce qui permet à la CI de fonctionner dès maintenant et de grandir avec le projet :

| Étape | Condition |
|---|---|
| Liens internes de la documentation (`tools/check_links.py`) | toujours |
| `cargo fmt`, `clippy`, `cargo test` | `Cargo.toml` à la racine |
| Compilation `wasm32-unknown-unknown` | `crates/wasm/Cargo.toml` |
| `ruff`, `pytest` (via `uv`) | `pyproject.toml` à la racine |
| `npm ci`, `npm run build` du viewer | `web/viewer/package.json` |
| `just check` | `Cargo.toml` à la racine |

Les tests qui dépendent de Laya ou du LLM utilisent des doublures (réponses enregistrées) en CI ; les vrais modèles ne tournent que dans `gpu-eval.yml`.

## Évaluation GPU (`gpu-eval.yml`)

- **Runner auto-hébergé** sur la machine de développement, avec les labels `self-hosted`, `linux`, `gpu`. Enregistrement manuel : *Settings → Actions → Runners → New self-hosted runner*, en ajoutant le label `gpu`. Le faire tourner sous un utilisateur dédié, sans droits d'administration, idéalement dans un conteneur.
- **Sécurité, dépôt public** : jamais déclenché par `pull_request` ; seulement sur push vers `main` (protégée) ou lancement manuel, et seulement si l'auteur de l'action est le propriétaire du dépôt.
- **Interrupteur** : variable `GPU_EVAL_ENABLED`, gérée par Terraform (`gpu_eval_enabled`), à passer à `true` au jalon P2.
- Le rapport (`reports/report.md`, `summary.json`, `violations.txt`) est publié comme artefact du workflow.

## Déploiement (`deploy-viewer.yml`)

- Cible : **Cloudflare Pages**, qui accepte les en-têtes COOP/COEP via `web/viewer/public/_headers`.
- **Interrupteur** : variable `DEPLOY_ENABLED` (Terraform `deploy_enabled`), à activer au jalon du replay public.
- Secrets `CLOUDFLARE_API_TOKEN` et `CLOUDFLARE_ACCOUNT_ID` : uniquement dans l'environnement `production`, utilisable seulement depuis `main`. Créés par Terraform quand les variables correspondantes sont renseignées.
- **À faire avant activation** : créer le projet Pages (`npx wrangler pages project create nothing-to-lose`, ou plus tard via le provider Terraform Cloudflare, dont le schéma est à vérifier par `chercheur-web`), et créer un jeton Cloudflare limité à *Pages : édition*.

## Validation locale

```bash
just tf-check                                                  # terraform fmt + validate
actionlint -config-file .github/actionlint.yaml .github/workflows/*.yml
python3 tools/check_links.py
```
