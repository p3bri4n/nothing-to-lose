# Plan du jalon PP — Préparation de l'environnement

*Statut : validé par l'utilisateur le 2026-11-05 (décisions D1 à D9 ci-dessous ; sandbox reporté). Auteur : `architecte`.*
*Sources : [16-jalons.md](../conception/16-jalons.md), [03-architecture-technique.md](../conception/03-architecture-technique.md), [22-boucle-de-retour.md](../conception/22-boucle-de-retour.md), [ci-cd.md](../technique/ci-cd.md).*

## 1. Objectif

Rendre l'environnement de travail **reproductible et sûr** pour un développement fait surtout par des agents Claude Code, avant P0 :

- versions d'outils figées (`mise.toml`, `rust-toolchain.toml`), identiques en local et en CI ;
- fichiers formatés automatiquement après chaque modification par Claude Code ;
- commit bloqué s'il contient un secret ou casse un lien de la documentation, avec un second contrôle en CI ;
- circuit Git unique pour chaque tâche : branche, pull request ouverte avec `gh`, liste de contrôle vérifiée par la CI, modèles de tickets.

PP ne crée **aucun** `Cargo.toml`, `pyproject.toml` ni `package.json` : ces fichiers activent des étapes de CI qui appartiennent à P0 et P1.

**Écart par rapport à `16-jalons.md`, validé par l'utilisateur** : l'image du sandbox Docker est **reportée après PP** (voir §10). Le critère « mêmes versions en local, dans le sandbox et en CI » devient « mêmes versions en local et en CI ».

## 2. Critères d'acceptation (vérifiables)

Les vérifications passent par `tools/verify_pp.sh`, appelé par `just verify-pp <sous-commande>`. Chaque sous-commande renvoie 0 si le critère est rempli. `just verify-pp all` enchaîne `secrets`, `format` et `versions`.

| # | Critère | Commande | Résultat attendu |
|---|---|---|---|
| C1 | Un commit contenant un faux secret est bloqué | `just verify-pp secrets` | Dans un dépôt temporaire, le commit d'un fichier contenant un jeton factice **généré à l'exécution** échoue (sortie gitleaks « leaks found ») et `HEAD` reste inchangé. Un commit témoin sans secret passe. Un lien Markdown cassé bloque aussi le commit. Après un commit forcé par `--no-verify`, `just secrets-scan` (la commande lancée par la CI) détecte le secret et renvoie 1. Sortie finale : `OK C1`, code 0. |
| C2 | Une modification de fichier est formatée automatiquement | `just verify-pp format`, puis un test de bout en bout manuel en local | Pour chaque fixture mal formatée de `tools/tests/fixtures/format/` (`.py`, `.toml`, `.tf`, `.sh`, `.yaml`, `.json`, `.rs`), on envoie au hook `PostToolUse` le JSON `{"tool_name":"Write","tool_input":{"file_path":…}}`. Le fichier, copié au préalable, est modifié et passe ensuite le `--check` du formateur. Un fichier `.md` reste inchangé. Bout en bout (manuel, en local) : dans une session Claude Code lancée à la racine du dépôt, avec `mise` dans son `PATH`, demander d'écrire `e2e_format_probe.py` **à la racine** (chemin non ignoré par Git) avec `x=1;y= 2`. Une fois relu, le fichier contient `x = 1` et `y = 2` sur deux lignes, et `.cache/hooks/format.log` n'a pas de nouvelle ligne. Demander ensuite, par `Edit`, de remplacer `y = 2` par `y = 3` : la modification doit aboutir, au besoin après une relecture du fichier (observation de R8, à noter avec la durée ressentie). Refaire l'essai confié à un sous-agent (`executant`). Supprimer le fichier ; `git status` est propre. Le critère ne change pas, seul le fichier d'essai change (décision [0020](../decisions/0020-securite-hook-formatage.md)). |
| C3 | Une pull request de test passe la CI avec la liste de contrôle remplie | `just verify-pp pr <numéro>` | `gh pr view <n> --json body,statusCheckRollup` donne `ci-cpu` = `SUCCESS` et aucune case `- [ ]` dans la section « Liste de contrôle ». Contre-épreuve : avec une case décochée sur la même PR, `ci-cpu` échoue et affiche « Liste de contrôle incomplète ». |
| C4 | Mêmes versions d'outils en local et en CI | `just versions` (en local) et l'étape `just versions` de `ci-cpu`, puis `just verify-pp versions` | Dans les deux environnements, `tools/check_tool_versions.py` affiche `OK : N outils conformes à mise.toml et rust-toolchain.toml` et renvoie 0. `verify-pp versions` contrôle en plus que la liste vérifiée en local est exactement celle de `mise.toml` et que chaque outil répond à la version figée. La CI fait le même contrôle sur les mêmes fichiers. Les outils marqués « local seulement », comme Claude Code, ne sont pas vérifiés en CI. |

## 3. Prérequis

### 3.1 État constaté (2026-11-05)

- Git : un seul commit (`c1f1c8a`) sur `main`, **aucun remote**. Le dépôt GitHub n'existe pas encore.
- Outils présents en local : docker 29.9.3, gh 2.46.0 (ancien), uv 0.11.14, python3 3.14.4, node 22.22.1, npm 9.2.0, jq, git 2.53.0. **Absents** : mise, gitleaks, just, terraform, actionlint, rustc/cargo, shellcheck.
- CI : versions non figées (`dtolnay/rust-toolchain@stable`, node 20, uv et just sans version) ; actions référencées par étiquette (`@v4`) et non par SHA.
- `infra/terraform/actions.tf` n'autorise pas `jdx/mise-action` ; `labels.tf` ne contient pas `jalon:PP`.
- `just check` renvoie 1 pendant PP (« à venir (P1) »), ce qui casse la méthode de l'`executant`. Ce point est traité en E5.
- Le chemin du dépôt contient **des espaces et un « : »** (voir R1 et R2).

### 3.2 Actions réservées à l'utilisateur

| # | Action | Quand |
|---|---|---|
| U1 | Installer mise en local (méthode officielle vérifiée par `chercheur-web`), l'activer dans le shell, puis lancer `mise trust` et `mise install` à la racine du dépôt | après E1 |
| U2 | Préparer `infra/terraform/terraform.tfvars` et un jeton d'administration dans `GITHUB_TOKEN`, puis lancer `just tf-init`, `just tf-plan` (à relire) et `just tf-apply` | après E2 |
| U3 | Ajouter le remote (`git remote add origin …`) et faire le premier `git push -u origin main`, avec le contournement du propriétaire | après U2 |
| U4 | `gh auth login` en local, avec le gh installé par mise | après U3 |
| U5 | Créer le **jeton à granularité fine des agents** : limité à ce dépôt ; *Contents*, *Pull requests* et *Issues* en écriture ; *Workflows* en écriture si les agents modifient la CI ; durée courte. Le ranger hors du dépôt, par exemple dans `~/.config/nothing-to-lose/agents.env` (`chmod 600`, variable `GH_TOKEN`) | après U3 |
| U6 | Relire la PR d'E3 (`bypass_mode`), la fusionner, puis relancer `just tf-plan` et `just tf-apply` | après U3 |
| U7 | **Fusionner toutes les pull requests** : l'utilisateur est seul à le faire (D8) | à chaque PR |

### 3.3 À vérifier immédiatement (E0)

Le **type de système de fichiers** de `/run/media/pebrian/Data` (`findmnt -no FSTYPE,OPTIONS --target "<racine>"`). Sur NTFS ou exFAT, les bits d'exécution, les liens symboliques et les propriétaires se comportent différemment, et Git peut avoir `core.fileMode=false`. Les hooks de `.githooks/` pourraient alors ne pas être exécutables.

## 4. Séquencement (D9)

```
E0 recherche + vérifications ─► E1 mise.toml ─► E2 Terraform (mise-action, jalon:PP)
   ─► U2 tf-apply + U3 premier push (amorçage : E0–E2 commités directement sur main)
   ─► ensuite, une branche et une PR par étape, fusionnées par l'utilisateur :
      E3 bypass_mode pull_request (+ U6 tf-apply) ─► E4 versions ─► E5 formateurs
      ─► E6 hook Claude Code ─► E7 hooks Git + gitleaks ─► E8 modèles GitHub
      ─► E9 CI alignée sur mise ─► E10 garde-fous des agents
      ─► E11 vérification finale ─► E12 documentation + journal
```

Les PR de PP servent de premières PR de test (C3). Tant que E9 n'est pas fusionnée, `ci-cpu` ne vérifie que les liens de la documentation : c'est voulu. Les étapes E8 et E9 peuvent être regroupées dans une même PR pour que la liste de contrôle et son contrôle arrivent ensemble.

## 5. Étapes

Chaque étape se vérifie indépendamment. La sous-commande de `verify_pp.sh` qui la concerne est ajoutée dans la même étape.

### E0 — Recherche et vérifications préalables

- **Agents** : `chercheur-web`, qui produit une note `docs/recherches/2026-11-xx-outillage-pp.md` ; `explorateur`, qui vérifie le système de fichiers.
- **À vérifier, avec source et date** (aucune version n'est tenue pour acquise) :
  - versions stables actuelles de mise, Rust, Node (ligne LTS active), Python, uv, just, terraform, gitleaks, actionlint, ruff, taplo, prettier, shfmt, shellcheck, gh et Claude Code. Pour Python, vérifier la compatibilité avec les dépendances prévues (torch, pyosmium, shapely) ;
  - backends mise pour chaque outil (`aqua:`, `npm:`, registre). Pour Claude Code : backend possible et désactivation de la mise à jour automatique (variable d'environnement) pour que la version reste figée ;
  - prise en charge de `rust-toolchain.toml` par mise et rustup ; existence et statut de `mise.lock` ;
  - syntaxe de gitleaks 8.x : `gitleaks git --pre-commit --staged`, `--redact`, `[extend] useDefault`, `.gitleaksignore` ;
  - schéma des hooks Claude Code : `PostToolUse` et `PreToolUse`, matchers `Write|Edit|MultiEdit`, `$CLAUDE_PROJECT_DIR`, JSON reçu sur stdin, codes de sortie, `timeout`. Comportement des règles `deny` et des hooks en mode `--dangerously-skip-permissions` (point central pour Claudeus, voir §10) ;
  - `jdx/mise-action` : version courante, SHA, cache, utilisation de `GITHUB_TOKEN` contre les limites de débit ;
  - syntaxe des issue forms GitHub ; permissions d'un jeton à granularité fine pour pousser, ouvrir une PR et modifier `.github/workflows/` ;
  - effet de `bypass_mode = "pull_request"` dans le ruleset ; premier push sur un dépôt vide déjà couvert par le ruleset.
- **Vérification** : la note existe, chaque version a une source et une date, et `python3 tools/check_links.py` passe.

### E1 — Versions figées (`mise.toml`, `rust-toolchain.toml`)

- **Agent** : `executant` (configuration), relu par `relecteur`.
- **Fichiers** :
  - `mise.toml` : section `[tools]` avec des **versions exactes** (D5) issues d'E0, Claude Code compris. Section `[env]` avec `UV_PYTHON_DOWNLOADS = "never"`, pour qu'uv utilise le Python de mise. **Aucun** chemin du dépôt ajouté à `PATH` (R1).
  - `rust-toolchain.toml` : `channel` exact, `components = ["rustfmt", "clippy"]`, `targets = ["wasm32-unknown-unknown"]`.
  - `.gitignore` : ajouter `.cache/`, `mise.local.toml` et `.claude/settings.local.json`.
  - `justfile` : `set shell := ["bash", "-euo", "pipefail", "-c"]` et une recette `setup` (`mise install`, puis `just hooks-install` une fois E7 faite).
- **Vérification** (après U1) : `mise install && mise ls --current` liste toutes les versions de `mise.toml` ; `rustc --version` correspond à `rust-toolchain.toml` ; `just --version` répond.

### E2 — Terraform avant le premier `apply`

- **Agent** : `developpeur`, avec revue d'`architecte` (changement d'infrastructure).
- **Fichiers** :
  - `infra/terraform/actions.tf` : ajouter `jdx/mise-action@*` à `patterns_allowed` (D3) ;
  - `infra/terraform/labels.tf` : ajouter `jalon:PP` ;
  - `infra/terraform/.terraform.lock.hcl` : versionné (plateforme `linux_amd64`).
- **Vérification** : `just tf-check`, avec le terraform de mise (au besoin `terraform init -backend=false`). `just tf-plan` et `just tf-apply` sont lancés **par l'utilisateur** (U2), suivis de U3, U4 et U5.

### E3 — `bypass_mode = "pull_request"` (première PR du circuit)

- **Agent** : `developpeur`, avec revue d'`architecte`.
- **Fichier** : `infra/terraform/ruleset.tf` : `bypass_mode = "pull_request"` pour le rôle admin (D8). Plus personne, propriétaire compris, ne pousse directement sur `main` : les changements passent toujours par une PR, que le propriétaire peut encore fusionner en contournant la CI en cas d'urgence.
- **Vérification** : `just tf-check` ; la PR passe `ci-cpu` ; l'utilisateur fusionne puis applique (U6). Ensuite, `git push origin HEAD:main` depuis une branche de test est refusé par GitHub.

### E4 — Contrôle des versions

- **Agents** : `developpeur` (script), `testeur` (tests).
- **Fichiers** :
  - `tools/check_tool_versions.py` (bibliothèque standard, `tomllib`) ;
  - `tools/tests/test_check_tool_versions.py` (`unittest`, pour ne pas créer de `pyproject.toml`) ;
  - squelette de `tools/verify_pp.sh` (`set -euo pipefail`, chemins entre guillemets) avec la sous-commande `versions`.
- **Interface** : `check_tool_versions.py [--print] [--ci]`.
  - Lit `mise.toml` et `rust-toolchain.toml`, exécute `<outil> --version` via le `PATH` réel et extrait la version avec une expression régulière propre à chaque outil.
  - Affiche une ligne par outil : `outil attendu obtenu statut`. Renvoie 1 si un outil est absent ou n'a pas la bonne version.
  - `--ci` ignore les outils marqués « local seulement » (Claude Code) ; `--print` affiche la liste normalisée.
- **Recettes** : `just versions` (ajoute `--ci` si `CI=true`), `just tools-test` (`python -m unittest discover -s tools/tests`).
- **Vérification** : `just versions` renvoie 0 en local. Les tests couvrent l'analyse des sorties `--version` (fixtures), un outil absent et une version différente.

### E5 — Formateurs et formatage du dépôt

- **Agents** : `developpeur` (aiguillage), `executant` (fichiers de configuration).
- **Fichiers** :
  - `tools/fmt.py` : **seule source** de la correspondance entre extension et formateur, Markdown **exclu** (D7) :

    | Extension | Formateur |
    |---|---|
    | `.rs` | rustfmt |
    | `.py` | ruff format |
    | `.toml` | taplo |
    | `.tf` | terraform fmt |
    | `.sh` | shfmt |
    | `.json`, `.yaml`, `.js`, `.ts`, `.html`, `.css` | prettier, installé par mise, sans `package.json` à la racine |

  - fichiers de configuration : `ruff.toml`, `taplo.toml`, `.prettierrc.json`, `.prettierignore` (contient `*.md`), `rustfmt.toml` (`edition = "2024"`, à reconfirmer en P1), `.editorconfig`, `.gitattributes` (`* text=auto eol=lf`) ;
  - fixtures mal formatées dans `tools/tests/fixtures/format/`, exclues de `fmt-check`.
- **Interface** : `tools/fmt.py --write|--check [chemins…]`. Sans chemin, l'outil traite les fichiers suivis par Git. Les formateurs sont lancés via `mise exec --`.
- **Recettes** :
  - `just fmt` et `just fmt-check` ;
  - `just lint`, qui enchaîne `versions`, `tools-test`, `fmt-check`, `docs-links`, `secrets-scan`, `actionlint` et `tf-check` (liste complétée au fil des étapes) ;
  - `just check`, qui appelle `just lint` jusqu'à P1, où il sera complété.
- **Commit séparé** « formatage initial » (`just fmt` sur l'existant), pour que les diffs suivants restent lisibles.
- **Vérification** : `just fmt-check` renvoie 0 sur le dépôt. `python3 tools/fmt.py --check tools/tests/fixtures/format/*` renvoie 1 (les fixtures sont bien détectées).

### E6 — Hook Claude Code de formatage

- **Agent** : `developpeur`, avec revue d'`architecte` (exécution automatique de commandes).
- **Fichiers** :
  - `tools/hooks/format_on_edit.py` : lit le JSON sur stdin et récupère `tool_input.file_path`. Ignore les chemins hors de `$CLAUDE_PROJECT_DIR`, les chemins ignorés par Git et les dossiers générés (`target/`, `runs/`, `shots/`, `node_modules/`). Appelle ensuite `tools/fmt.py --write <chemin>`.
  - `.claude/settings.json` : section `hooks.PostToolUse`, matcher `Write|Edit|MultiEdit` (à confirmer en E0), commande `python3 "$CLAUDE_PROJECT_DIR/tools/hooks/format_on_edit.py"` (variable entre guillemets doubles à cause des espaces et du « : »), `timeout` de 30 s.
- **Comportement** :
  - **ne bloque jamais** : renvoie toujours 0 ;
  - un formateur absent ou une erreur de syntaxe produit une ligne dans `.cache/hooks/format.log` ;
  - désactivable avec `NTL_FORMAT_HOOK=off` ;
  - **garde de configuration** (décision [0020](../decisions/0020-securite-hook-formatage.md), option c) : le hook refuse de formater tant que `mise.toml`, `mise.local.toml`, `.prettierrc.json` ou `rust-toolchain.toml` diffèrent de HEAD. Configuration Prettier imposée via `--config`, pas d'installation automatique par mise, processus formateur tué à l'expiration du délai.
- **Vérification** : `just verify-pp format` (C2, partie automatique), puis le test de bout en bout de C2 **en local** (procédure et fichier d'essai à la racine décrits en C2). Point à observer : Claude Code accepte-t-il sans erreur une modification ultérieure d'un fichier reformaté par le hook (R8) ?

### E7 — Hooks Git avant commit et gitleaks

- **Agents** : `developpeur` (hooks, recettes), `testeur` (`verify_pp secrets`).
- **Fichiers** (D1 : scripts maison ; D2 : gitleaks via mise et `.gitleaks.toml`) :
  - `.githooks/pre-commit` (bash, exécutable). Il cherche `mise` dans le `PATH`, sinon dans `~/.local/bin/mise`, puis lance `mise exec -- just pre-commit`. Il est **fermé par défaut** : si `mise` ou `gitleaks` est introuvable, le commit est refusé avec un message clair.
  - `.gitleaks.toml` : `[extend] useDefault = true`, sans liste blanche large. `.gitleaksignore` au besoin, avec des empreintes précises.
  - `justfile` :

    | Recette | Rôle |
    |---|---|
    | `hooks-install` | `git config core.hooksPath .githooks`, appelée par `setup` |
    | `pre-commit` | `gitleaks git --pre-commit --staged --redact`, puis `docs-links` |
    | `secrets-scan` | `gitleaks git --redact` sur tout l'historique ; utilisée par la CI |
    | `docs-links` | `python3 tools/check_links.py` |

- **Avant d'activer le hook** : lancer `just secrets-scan` sur l'historique existant. Les faux positifs éventuels (par exemple `export GITHUB_TOKEN=...` dans `ci-cd.md`) sont traités par empreinte.
- **`verify_pp.sh secrets`** :
  1. Crée un dépôt temporaire (`mktemp -d`) contenant une copie de `.githooks/`, `.gitleaks.toml`, `justfile`, `mise.toml` et `tools/`, avec `MISE_TRUSTED_CONFIG_PATHS` qui pointe dessus.
  2. Génère le jeton factice **à l'exécution** (préfixe de fournisseur suivi de caractères aléatoires) : il n'apparaît jamais en clair dans le dépôt ni dans la documentation.
  3. Vérifie que le commit est bloqué, que le commit témoin passe et qu'un lien cassé bloque le commit.
  4. Fait un commit avec `--no-verify` et vérifie que `secrets-scan` le détecte.
  5. Supprime le dépôt temporaire.
- **Vérification** : `just verify-pp secrets` renvoie 0 (C1).

### E8 — Modèles GitHub et contrôle de la liste

- **Agents** : `executant` (modèles), `developpeur` (script), `testeur`.
- **Fichiers** :
  - `.github/pull_request_template.md` : résumé, jalon, ticket lié, puis la section **« Liste de contrôle »** :
    - `just lint` / `just check` passe ;
    - `just eval` lancé si la simulation ou les IA sont touchées ;
    - `docs/technique/` à jour ;
    - test de non-régression si la PR corrige un bug ;
    - décision structurante posée à l'utilisateur, ou « sans objet » ;
    - `reports/baseline.json` inchangé, ou changement expliqué ;
    - aucun secret.

    Un point qui ne s'applique pas est coché et suivi de « — sans objet ».
  - `.github/ISSUE_TEMPLATE/bug.yml` : seed, tick, agent, commit, commande de reproduction, comportement attendu et observé, capture ; label `bug`.
  - `.github/ISSUE_TEMPLATE/decision.yml` : contexte, options, recommandation, documents touchés ; label `décision`.
  - `.github/ISSUE_TEMPLATE/config.yml`.
  - `tools/check_pr_checklist.py`, avec ses tests.
- **Interface** : `check_pr_checklist.py` lit le corps de la PR dans la variable d'environnement `PR_BODY`, jamais interpolé dans `run:` (R10). Il renvoie 1 et liste les cases non cochées de la section « Liste de contrôle ». Les PR de `dependabot[bot]` sont exemptées.
- **Vérification** : `just tools-test`. `PR_BODY="$(cat .github/pull_request_template.md)" python3 tools/check_pr_checklist.py` renvoie 1, puis 0 une fois toutes les cases cochées.

### E9 — CI alignée sur mise

- **Agent** : `developpeur`, avec revue d'`architecte` (CI, check obligatoire).
- **`.github/workflows/ci.yml`** :
  - le job garde le nom **`ci-cpu`** (R12) ;
  - `runs-on: ubuntu-24.04` ;
  - actions épinglées par SHA, avec la version en commentaire ;
  - `actions/checkout` avec `fetch-depth: 0` ;
  - `jdx/mise-action` (D3), avec `GITHUB_TOKEN` et cache ;
  - étapes : `just versions`, `just secrets-scan`, `just docs-links`, `just fmt-check`, `actionlint`, `terraform init -backend=false` puis `just tf-check`, `just tools-test` ;
  - **contrôle bloquant de la liste** (D4) : `on.pull_request.types: [opened, edited, synchronize, reopened]`, étape active seulement si `github.event_name == 'pull_request'`, corps passé par `env: PR_BODY` ;
  - les étapes conditionnelles Rust, Python et Node prennent leurs outils dans mise et `rust-toolchain.toml`. `dtolnay/rust-toolchain@stable`, `setup-uv`, `setup-node` et `setup-just` disparaissent. Leur retrait de `actions.tf` est laissé à une PR ultérieure, pour ne pas multiplier les `apply`.
- **`deploy-viewer.yml`** : node fourni par mise, pour respecter C4.
- **`gpu-eval.yml`** : **déclencheurs inchangés**. Seule l'installation des outils via mise est ajoutée, si nécessaire.
- **Vérification** : `actionlint -config-file .github/actionlint.yaml .github/workflows/*.yml` en local. La PR de cette étape passe `ci-cpu` (C3), et la contre-épreuve de la liste de contrôle échoue comme prévu.

### E10 — Circuit Git des agents et garde-fous

- **Agents** : `developpeur` (hook `PreToolUse`), `executant` et `documentaliste` (documentation), avec revue d'`architecte`.
- **Fichiers** :
  - `.claude/settings.json` : en plus des règles `deny` existantes, interdire `git commit --no-verify`, `git commit -n`, `git push --force`, tout push vers `main`, `gh repo delete` et **`gh pr merge`** (l'utilisateur fusionne seul, D8).
  - `tools/hooks/guard_bash.py` : hook `PreToolUse` sur `Bash`. Il analyse la commande avec des expressions régulières et la bloque (code 2 et explication sur stderr). Il est **plus robuste que les règles `deny` par préfixe** et doit rester actif avec `--dangerously-skip-permissions` (à confirmer en E0), qui est le mode par défaut de Claudeus.
  - `docs/technique/circuit-git.md`, `CLAUDE.md` (routine).
- **Circuit** :
  1. Créer la branche depuis `main` à jour : `git switch -c <jalon>/<sujet-court>`.
  2. Commiter, messages en français.
  3. `git push -u origin HEAD`.
  4. `gh pr create --title … --body-file <corps rempli à partir du modèle>`.
  5. `gh pr checks --watch --required`.
  6. Prévenir l'utilisateur, qui fusionne (squash).

  Les agents utilisent le jeton U5 (`GH_TOKEN`).
- **Vérification** : tests unitaires de `guard_bash.py` sur des commandes autorisées et refusées, y compris des variantes comme `git -c x=y commit --no-verify`, `git commit -an` et `gh pr merge --auto`. Puis un essai manuel : quand on demande à Claude un `git commit --no-verify`, il est refusé avec une explication.

### E11 — Vérification finale

- **Agent** : `testeur`.
- **Commandes** :
  - `just verify-pp all` (`secrets`, `format`, `versions`) ;
  - `just verify-pp pr <n>` sur une PR de test (modification triviale de la documentation, liste de contrôle remplie), puis la contre-épreuve ;
  - test de bout en bout de C2 en local (procédure de C2, fichier d'essai à la racine, hors `.cache/`) ;
  - contrôle que l'étape `just versions` de `ci-cpu` est verte.
- **Livrable** : compte rendu avec les sorties des commandes, remis au `documentaliste`.

### E12 — Documentation et journal

- **Agent** : `documentaliste` (voir §9).
- **Vérification** : `just docs-links` renvoie 0 ; `docs/technique/README.md` indexe les nouvelles pages.

## 6. Interfaces récapitulatives

| Élément | Interface |
|---|---|
| `tools/fmt.py` | `--write\|--check [chemins…]`. Renvoie 0 si tout est formaté (`--check`) ou si le formatage a réussi (`--write`). Formateurs lancés via `mise exec --`. Markdown exclu. |
| `tools/hooks/format_on_edit.py` | JSON du hook sur stdin. Renvoie toujours 0. Journal dans `.cache/hooks/format.log`. Désactivable avec `NTL_FORMAT_HOOK=off`. |
| `tools/hooks/guard_bash.py` | JSON `PreToolUse` sur stdin. Renvoie 2 avec un message sur stderr si la commande est interdite, 0 sinon. |
| `tools/check_tool_versions.py` | `[--print] [--ci]`. Renvoie 1 en cas d'écart. |
| `tools/check_pr_checklist.py` | Lit `PR_BODY`. Renvoie 1 et liste les cases non cochées. |
| `tools/verify_pp.sh` | `secrets\|format\|versions\|pr <n>\|all`. Renvoie 0 si le critère est rempli. |
| Recettes `just` | `setup`, `hooks-install`, `pre-commit`, `secrets-scan`, `docs-links`, `fmt`, `fmt-check`, `versions`, `tools-test`, `lint`, `check` (= `lint` jusqu'à P1), `verify-pp` |

## 7. Risques et points de vigilance

| # | Risque | Parade |
|---|---|---|
| R1 | Le **« : » du chemin** casse toute liste séparée par des deux-points (`PATH`, `PYTHONPATH`, `LD_LIBRARY_PATH`). | Ne jamais mettre un chemin du dépôt dans ces variables (pas de `_.path` dans mise). |
| R2 | Les espaces et le « : » cassent les scripts mal écrits, ainsi que `docker run -v`. | Guillemets partout (`"$CLAUDE_PROJECT_DIR"`, `"{{justfile_directory()}}"`), `pathlib` en Python, relecture par shellcheck. Pour Docker plus tard : `--mount type=bind,source=…` (voir §10). |
| R3 | **Système de fichiers** de `/run/media/…` (NTFS, exFAT ?) : bit d'exécution des hooks, liens symboliques, lenteur de `target/` et de `node_modules/`. | Vérification en E0. Au besoin, appeler les hooks via `bash .githooks/…` depuis un hook d'amorce, et placer les artefacts lourds hors du dépôt. |
| R4 | `--no-verify` contourne les hooks Git. | Gitleaks et les liens refaits dans `ci-cpu` (obligatoire). Protection contre le push de secrets côté GitHub, déjà activée par Terraform. `guard_bash.py` côté agents. |
| R5 | Fuite du faux secret de test dans le dépôt public (les références de PR ne s'effacent pas). | Jeton généré à l'exécution, utilisé seulement dans un dépôt temporaire, **jamais poussé**. Le contrôle CI se vérifie en local avec la même recette `secrets-scan`. |
| R6 | **Jeton des agents** : un jeton du propriétaire hérite du contournement admin. Modifier `.github/workflows/` exige en plus la permission *Workflows*. | `bypass_mode = "pull_request"` (E3), `gh pr merge` interdit (E10), durée courte, dépôt unique, fichier `env` en `chmod 600` hors du dépôt. |
| R7 | Agents lancés avec `--dangerously-skip-permissions` (Claudeus) : les règles `deny` risquent de ne pas s'appliquer. | `guard_bash.py` en hook `PreToolUse` ; comportement à confirmer en E0 et à tester dès que Claudeus sera utilisé sur ce dépôt. |
| R8 | Le hook de formatage modifie un fichier juste après l'édition de Claude, si bien que le contenu attendu à l'édition suivante a changé. Un hook lent ou bavard gêne la session. | Observation en E6. Timeout de 30 s, pas d'échec bruyant, formatage limité au fichier touché. |
| R9 | Les versions dérivent : la CI préinstalle python, node et gh ; `ubuntu-latest` évolue ; Dependabot ne lit pas `mise.toml`. | `just versions` en CI, `ubuntu-24.04`, mise à jour volontaire par une PR dédiée (procédure dans `docs/technique/outillage.md`). |
| R10 | **Injection de script** par le corps de la PR dans la CI (dépôt public). | Corps passé par `env:`, jamais par `${{ }}` dans `run:`. |
| R11 | Limites de débit de l'API GitHub lors des téléchargements de mise en CI. | `GITHUB_TOKEN` fourni à mise, cache. |
| R12 | Renommer `ci-cpu` casserait le ruleset. | Nom inchangé ; sinon, mettre à jour `required_ci_check` dans le même changement. |
| R13 | Faux positifs de gitleaks dans la documentation (exemples de commandes). | Analyse de l'historique avant activation ; exceptions par empreinte, jamais par dossier entier. |
| R14 | Le formatage initial produit des diffs très bruyants. | Un commit dédié ; Markdown exclu. |
| R15 | Déterminisme : PP n'y touche pas, mais la version de `rustc` fera partie de la traçabilité de `summary.json` (P1). | `rust-toolchain.toml` devient la référence à enregistrer en P1. |
| R16 | Latence des modèles : sans objet en PP (pas de GPU, pas de modèle). | — |
| R17 | Le volume dépasse « une session » (environ 9 PR). | Regroupements possibles : E4 à E6, puis E8 et E9. |

## 8. Hors périmètre

- `Cargo.toml`, `pyproject.toml` et `package.json` (à la racine ou du viewer) : P0 et P1. Le contenu de `just check` au-delà de `lint`, ainsi que `sim`, `eval` et `inspect`.
- **Image du sandbox Docker** : reportée (§10).
- GPU, TabbyAPI, `laya-serve` et `docker compose` des services.
- Enregistrement du runner GPU, activation de `GPU_EVAL_ENABLED` et toute modification des **déclencheurs** de `gpu-eval.yml`.
- Cloudflare Pages, `DEPLOY_ENABLED`.
- Signature des commits, CODEOWNERS, file de fusion, convention de commits imposée par un outil.
- Renovate ou Dependabot pour mise et les actions ; retrait des actions devenues inutiles dans `actions.tf`.
- Claude Code dans GitHub Actions.
- Hooks Claude Code autres que le formatage et la garde Bash. **Exception ajoutée à la demande de l'utilisateur (2026-11-05)** : le hook `SessionStart` (`tools/hooks/session_start.py`) qui résume l'état du projet à l'ouverture de Claude Code, documenté dans [`../technique/hook-session-start.md`](../technique/hook-session-start.md). Il n'était pas prévu par ce plan.
- Vérifications lourdes au moment du push (`cargo test`, etc.).

## 9. Mises à jour documentaires

| Fichier | Contenu |
|---|---|
| `docs/technique/outillage.md` (nouveau) | mise, références des versions (`mise.toml`, `rust-toolchain.toml`), `just setup`, procédure de mise à jour d'un outil, formateurs et leur configuration, hook Claude Code |
| `docs/technique/circuit-git.md` (nouveau) | branches, PR, liste de contrôle, modèles de tickets, hooks Git, garde-fous des agents, jeton des agents, fusion réservée à l'utilisateur |
| `docs/technique/commandes.md` (nouveau, prévu dans l'index) | toutes les recettes `just` |
| `docs/technique/ci-cd.md` | mise en CI, nouvelles étapes de `ci-cpu`, `jdx/mise-action` autorisée, label `jalon:PP`, contrôle de la liste, gitleaks, `bypass_mode = "pull_request"` |
| `docs/technique/README.md` | index |
| `CLAUDE.md` | tableau des commandes (nouvelles recettes, `check` = `lint` jusqu'à P1), routine (branche et PR, fusion par l'utilisateur), interdiction de `--no-verify` et de `gh pr merge` |
| `README.md` (racine) | section « Démarrage » : installer mise, `mise install`, `just setup` |
| `docs/decisions/` | fiches 0007 et suivantes pour D1 à D9, dont le report du sandbox ; index |
| `docs/conception/16-jalons.md` | ligne PP : sandbox reporté, C4 limité au local et à la CI |
| `docs/recherches/` | note d'E0 |
| `docs/journal/` | entrée de fin de session |

## 10. Reporté : sandbox Docker et Claudeus

**Décision de l'utilisateur (D6)** : l'image du sandbox est reportée après PP. L'utilisateur dispose de son propre outil, **Claudeus** (<https://github.com/p3bri4n/claudeus>). C'est une image `node:20` complétée par `apt`, commune à tous ses projets et **sans mise**. Ce que PP en tient compte dès maintenant :

- **C4** se limite au local et à la CI. Le critère d'origine (« … dans le sandbox … ») sera rétabli quand le sandbox sera traité.
- **`guard_bash.py`** (E10) est la principale protection des agents dans Claudeus, qui tourne par défaut avec `--dangerously-skip-permissions`.

**Problèmes probables de Claudeus sur ce dépôt** (à vérifier, non testés) :

1. `-v "$PROJECT_DIR":/workspace` : avec l'ancien chemin du dépôt (« Guide Or Fade : Your command »), le « : » était lu comme un séparateur par la syntaxe `-v`. Le dossier est désormais `nothing-to-lose` (renommé le 2026-11-07), mais `--mount` reste plus sûr : `--mount type=bind,source="$PROJECT_DIR",target=/workspace`.
2. `--name claudeus-<dossier>` : les espaces et le « : » de l'ancien chemin n'étaient pas autorisés dans un nom de conteneur Docker (`[a-zA-Z0-9][a-zA-Z0-9_.-]*`). Il faut assainir le nom, par exemple en remplaçant tout autre caractère par `-`.
3. **Liste blanche réseau** : elle n'inclut pas les domaines de téléchargement de mise (dépôts GitHub des outils, `mise.jdx.dev`, miroirs Node, Python et Rust selon les backends), ni peut-être `static.rust-lang.org`. Sans eux, `mise install` échoue dans le conteneur.
4. **Pas de mise dans l'image** : les versions du conteneur (node 20, outils `apt`) ne correspondent pas à `mise.toml`. Les hooks Git (fermés par défaut) refuseront donc les commits faute de `mise` et de `gitleaks`, ce qui est voulu mais bloque le travail des agents.

**Pistes pour le jalon qui reprendra le sujet** (à arbitrer à ce moment-là, avec l'utilisateur) :

- **(a)** Adapter Claudeus : `--mount`, nom assaini, installation de mise et `mise install` à partir du `mise.toml` du projet monté, ajouts à la liste blanche. Cette option profite à tous les projets de l'utilisateur.
- **(b)** Image propre à Nothing To Lose (Debian slim avec mise), lancée par Claudeus ou par des recettes `just sandbox*`.
- **(c)** Déplacer ou lier le dépôt vers un chemin sans « : » ni espace.

Points de vigilance à reprendre : UID et GID, `safe.directory`, `CARGO_TARGET_DIR` et `UV_PROJECT_ENVIRONMENT` séparés entre l'hôte et le conteneur, pas de socket Docker, pas de GPU, identifiants Claude Code (volume dédié plutôt que montage de `~/.claude`), jeton des agents passé par `--env-file`.

## 11. Décisions de l'utilisateur (2026-11-05)

| # | Sujet | Décision |
|---|---|---|
| D1 | Gestionnaire de hooks Git | Scripts maison dans `.githooks/` + `core.hooksPath` |
| D2 | Gitleaks | Binaire figé via mise ; `.gitleaks.toml` qui étend les règles par défaut ; même binaire en CI |
| D3 | Outils en CI | `jdx/mise-action`, épinglée par SHA ; ajout dans `actions.tf` |
| D4 | Liste de contrôle des PR | Contrôle bloquant dans `ci-cpu` |
| D5 | Politique de versions | Versions exactes partout, Claude Code compris ; mise à jour par PR dédiée. Valeurs proposées après E0. |
| D6 | Sandbox Docker | **Reporté** après PP (§10) |
| D7 | Formateurs | Socle rustfmt, ruff, taplo, terraform fmt, shfmt, prettier ; **Markdown exclu** |
| D8 | Identité et fusion | Jeton à granularité fine pour les agents ; `bypass_mode = "pull_request"` après le premier push ; **l'utilisateur seul fusionne** |
| D9 | Séquencement | `tf-apply` et premier push pendant PP, juste après E2 |

## 12. Choix mineurs pris en autonomie (à noter dans le journal)

- Emplacements : `.githooks/`, `tools/hooks/`, `tools/tests/`.
- Scripts en Python standard (`unittest`) plutôt qu'avec pytest, pour ne pas créer de `pyproject.toml` ; `verify_pp.sh` en bash, relu par shellcheck.
- Noms des recettes `just` ; `just check` appelle `just lint` jusqu'à P1.
- Hook de formatage qui ne bloque jamais, avec timeout, journal et variable de désactivation.
- Issue forms en YAML ; formulation de la liste de contrôle ; convention de branche `<jalon>/<sujet>`.
- `ubuntu-24.04`, actions épinglées par SHA, `fetch-depth: 0`.
- `rustfmt.toml` avec `edition = "2024"` (à reconfirmer en P1) ; `.editorconfig` et `.gitattributes`.
- `UV_PYTHON_DOWNLOADS=never`.
- Label `jalon:PP` (étiquette de suivi, appliquée avec le reste par U2).
- Retrait des actions devenues inutiles dans `actions.tf` reporté à une PR ultérieure.
