# Nothing To Lose — commandes du projet (voir CLAUDE.md)
# Les recettes marquées « à venir » seront implémentées au jalon indiqué.

set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

# PP — installer les outils aux versions figées de mise.toml (les hooks Git s'ajoutent à l'étape E7)
setup:
    mise install

# P0 — extraire et préparer la carte du centre de Toulouse (OSM)
bake:
    @echo "à venir (P0) : pipeline carto dans bake/" && exit 1

# P0 — lancer le viewer local
viewer:
    @echo "à venir (P0) : viewer Three.js dans web/viewer/ (prototype de rendu : web/viewer/prototype/index.html)" && exit 1

# P0 — captures d'écran automatisées dans shots/
shots:
    @echo "à venir (P0) : script Playwright" && exit 1

# P1 — partie headless : just sim --seed 42 --minutes 10 --out runs/42/
sim *ARGS:
    @echo "à venir (P1) : runner headless ({{ ARGS }})" && exit 1

# PP/P1 — contrôle complet : pour l'instant `lint` seul ; P1 y ajoute tests, non-régression, invariants, mini-partie
check: lint

# P2 — inspecter un agent : just inspect --seed 42 --tick 5320 --agent z123
inspect *ARGS:
    @echo "à venir (P2) ({{ ARGS }})" && exit 1

# P2 — lot de parties et rapport : just eval --seeds 50
eval *ARGS:
    @echo "à venir (P2) ({{ ARGS }})" && exit 1

# PP — vérifier que les outils installés correspondent à mise.toml (--ci si CI=true)
versions:
    python3 tools/check_tool_versions.py {{ if env_var_or_default("CI", "") == "true" { "--ci" } else { "" } }}

# PP — tests des outils du dépôt (tools/tests)
tools-test:
    python3 -m unittest discover -s tools/tests

# PP — formater tous les fichiers suivis par Git (tools/fmt.py ; Markdown exclu) et le justfile
fmt:
    python3 tools/fmt.py --write
    just --fmt --unstable

# PP — vérifier le formatage (fichiers suivis et justfile) sans rien modifier ; les fixtures de tools/tests/fixtures/format/ sont exclues
fmt-check:
    python3 tools/fmt.py --check
    just --fmt --check --unstable

# PP — vérifier les liens relatifs de la documentation
docs-links:
    python3 tools/check_links.py

# À venir : secrets-scan (E7) et actionlint (E8), à ajouter à `lint` dans leurs étapes.
# PP — contrôles statiques : versions, tests des outils, formatage, liens, Terraform
lint: versions tools-test fmt-check docs-links tf-check

# --- Infrastructure GitHub (Terraform) ---
# État local hors dépôt (décision 0002). Le jeton GitHub vient de GITHUB_TOKEN.
tf_state := env_var_or_default("TF_STATE_PATH", env_var("HOME") + "/.local/share/terraform/nothing-to-lose/terraform.tfstate")

# Initialiser Terraform (une fois, ou après un changement de provider)
tf-init:
    mkdir -p "$(dirname '{{ tf_state }}')"
    cd infra/terraform && terraform init -reconfigure -backend-config="path={{ tf_state }}"

# Vérifier le format et la validité
tf-check:
    cd infra/terraform && terraform fmt -check -recursive && terraform validate

# Afficher ce qui changerait sur GitHub (sans rien appliquer)
tf-plan:
    cd infra/terraform && terraform plan

# Appliquer : réservé à l'utilisateur, jamais lancé par un agent
tf-apply:
    cd infra/terraform && terraform apply
