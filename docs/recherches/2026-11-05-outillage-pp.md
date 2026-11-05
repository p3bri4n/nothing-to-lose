# Outillage du jalon PP (préparation de l'environnement)

Date de la recherche : 2026-11-05. Étape E0 du jalon PP. Note rédigée par `chercheur-web`.

Méthode : les versions viennent de l'API GitHub (`/releases/latest`, champ `published_at`), du registre npm, de PyPI (JSON), de `endoflife.date`, du canal officiel Rust (`static.rust-lang.org`) et des pages officielles (dépôt `nodejs/Release`, python.org, docs.github.com, code.claude.com, mise.jdx.dev, developer.hashicorp.com, registry.terraform.io ou dépôt GitHub du provider). Les pages ont été lues par un outil de résumé : les citations sont reformulées, pas copiées mot à mot. Les recherches web (sources secondaires, blogs, agrégateurs) ne servent qu'en complément ; elles sont signalées. Une information marquée « non vérifié » n'a pas été trouvée dans une source primaire.

## Réponse courte

Les versions stables actuelles sont : mise 2026.11.2 (publiée aujourd'hui, 2026-11-05 12:19 UTC), Rust 1.99.1, Node.js 26.13.0 (ligne 26 en Active LTS depuis le 2026-10-28), Python 3.15.2 (3.14.10 pour la compatibilité la plus large), uv 0.13.7, just 1.59.0, Terraform 1.17.1 (licence BSL 1.1, pas MPL), gitleaks 8.30.1 (projet déclaré « feature complete », successeur Betterleaks 1.10.0). Point à trancher : gitleaks n'est plus développé. Pour Python, le paquet `osmium` (pyosmium) ne déclare pas 3.15 dans ses classifiers : 3.14 est la version la plus sûre pour torch, shapely et osmium.

## Détails utiles

### 1. Versions stables (dates de publication)

| Outil | Version | Date | Source | Confiance |
|---|---|---|---|---|
| mise | v2026.11.2 | 2026-11-05 12:19 UTC | API GitHub `jdx/mise` | élevé |
| Rust (stable) | 1.99.1 | canal daté du 2026-10-15 (paquet `1.99.1 (58cf8f9c3 2026-10-13)`) | `static.rust-lang.org/dist/channel-rust-stable.toml` | élevé |
| Node.js | 26.13.0 (Active LTS) ; 24.22.2 (Maintenance LTS) ; 22.23.4 (Maintenance LTS) | 26.13.0 et 24.22.2 : 2026-10-28 ; 22.23.4 : 2026-10-21 | `endoflife.date/api/nodejs.json` ; `nodejs/Release` README | élevé (calendrier officiel) / moyen (dates des versions via endoflife) |
| Python | 3.15.2 (bugfix) ; 3.14.10 (bugfix) | 3.15.2 et 3.14.10 : 2026-10-25 ; 3.15.0 : 2026-10-09 | `endoflife.date/api/python.json` ; python.org/downloads | élevé pour 3.15.0 et 3.14 ; moyen pour les versions de correctif |
| uv | 0.13.7 | 2026-11-03 | API GitHub `astral-sh/uv` | élevé |
| just | 1.59.0 | 2026-10-15 | API GitHub `casey/just` | élevé |
| Terraform | 1.17.1 | 2026-10-28 | API GitHub `hashicorp/terraform` | élevé |
| gitleaks | v8.30.1 (projet déclaré « feature complete ») | 2026-03-21 | API GitHub `gitleaks/gitleaks` | élevé (version et statut) |
| Betterleaks (successeur de gitleaks) | v1.10.0 | 2026-11-04 | API GitHub `betterleaks/betterleaks` | élevé (version) / moyen (compatibilité, voir plus bas) |
| actionlint | v1.7.12 | 2026-03-30 (année déduite : 2026, d'après le champ `published_at`) | API GitHub `rhysd/actionlint` | élevé |
| ruff | 0.17.3 | 2026-10-27 | API GitHub `astral-sh/ruff` | élevé |
| taplo | 0.10.0 (CLI) | 2025-05-23 | API GitHub `tamasfe/taplo` | élevé ; possiblement ancien (aucune release depuis) |
| prettier | 3.9.10 | 2026-10-10 | API GitHub `prettier/prettier` ; registre npm `prettier` (3.9.10) | élevé |
| shfmt (`mvdan/sh`) | v3.14.1 | 2026-09-06 | API GitHub `mvdan/sh` | élevé |
| shellcheck | v0.11.0 | 2025-08-04 | API GitHub `koalaman/shellcheck` | élevé ; ancien mais dernière release |
| gh (GitHub CLI) | v2.103.3 | 2026-10-26 | API GitHub `cli/cli` | élevé |
| Claude Code (npm `@anthropic-ai/claude-code`) | 2.1.318 | 2026-11-04 (release GitHub `v2.1.318`) | API GitHub `anthropics/claude-code` ; registre npm (`dist-tags.latest` = 2.1.318) | élevé |
| jdx/mise-action | v5.2.6 | 2026-11-02 | API GitHub `jdx/mise-action` | élevé |
| Provider Terraform `integrations/github` | v6.13.0 | 2026-07-08 | API GitHub `integrations/terraform-provider-github` | élevé |

Remarques :
- **mise v2026.11.2 est sortie aujourd'hui** (2026-11-05 12:19 UTC, date de l'API). Par défaut, `mise-action` installe « la release la plus récente vieille d'au moins 24 h » : une protection à garder en tête si on épingle `version`.
- **Node.js** : des pages secondaires (recherche web) indiquent que Node 24 est l'Active LTS ; c'est contredit par le calendrier officiel. Le dépôt `nodejs/Release` indique : 22.x Maintenance LTS (fin : 2027-04-30) ; 24.x Maintenance LTS depuis 2026-10-20 (fin : 2028-04-30) ; 26.x Active LTS depuis 2026-10-28 (fin : 2029-04-30) ; 27.x en Alpha. Node 27 passera à une version majeure par an, et chaque ligne aura 30 mois de LTS ; le calendrier « est sujet à changement ».
- **Python** : une recherche web donnait 3.15.0 le 2026-10-01 (prévision PEP 790) ; python.org et endoflife donnent 2026-10-09. La date de python.org fait foi. Une recherche web annonçait 3.15.1 et 3.14.9 au 2026-10-21 ; endoflife donne 3.15.2 et 3.14.10 au 2026-10-25, à confirmer sur python.org.
- **gitleaks** : voir la section 4 (statut « feature complete »).

### 2. mise

- **Installation Linux** (doc officielle, `mise.jdx.dev/getting-started.html`) : `curl -fsSL https://mise.run | sh`, binaire placé dans `~/.local/bin/mise`, vérification avec `~/.local/bin/mise --version`. La page ne donne pas de commande apt/dnf/brew.
- **Syntaxe** (même page) :
  ```toml
  [tools]
  node = "24"

  [env]
  NODE_ENV = "development"
  ```
  `"24"` est un préfixe de version, pas une version exacte. Pour figer, utiliser `mise lock`. `mise set NODE_ENV=development` écrit dans `[env]`.
- **Confiance (trust)** : mise ne charge un `mise.toml` que s'il est approuvé, car `[env]`, hooks et templates peuvent exécuter du code. Un projet est approuvé lors de `mise install`, `mise exec` ou `mise run`, ou par la commande `mise trust`. Syntaxe exacte de `mise trust` : non vérifiée au-delà de la mention.
- **Backends et noms (registre `mise.jdx.dev/registry.html`)** :
  - `uv` : `aqua:astral-sh/uv` (`pipx:uv` existe aussi)
  - `just` : `aqua:casey/just`
  - `terraform` : `aqua:hashicorp/terraform`
  - `gitleaks` : `aqua:gitleaks/gitleaks` ; `betterleaks` : `aqua:betterleaks/betterleaks`
  - `actionlint` : `aqua:rhysd/actionlint`
  - `ruff` : `aqua:astral-sh/ruff`
  - `taplo` : `aqua:tamasfe/taplo` (aussi `cargo:taplo-cli`)
  - `prettier` : `npm:prettier`
  - `shfmt` : `aqua:mvdan/sh`
  - `shellcheck` : `aqua:koalaman/shellcheck`
  - `gh` : `aqua:cli/cli` (alias `github-cli`)
  - `claude-code` : `aqua:anthropics/claude-code` (alias `claude`) ; le paquet npm reste `@anthropic-ai/claude-code`
  - `node` : `core:node` ; `python` : `core:python` ; `rust` : `core:rust`
  - `mise` lui-même : non trouvé dans les extraits lus ; l'installer par `mise.run`.
- **`rust-toolchain.toml`** : mise le lit, mais seulement après opt-in : `mise settings add idiomatic_version_file_enable_tools rust` (global) ou avec `--local` (projet). Les clés lues sont `channel`, `profile`, `components`, `targets` dans la table `[toolchain]`. Un fichier nommé `rust-toolchain` (sans extension) n'est pas mentionné. Options de l'outil `rust` dans `mise.toml` : `rust = { version = "1.99", components = ["rust-src"], profile = "minimal" }` (les exemples de la doc montrent deux lignes séparées, ce qui duplique une clé en TOML : les combiner en une table inline). La doc prévient que `profile = "complete"` échoue presque toujours.
- **`mise.lock`** (`mise.jdx.dev/dev-tools/mise-lock.html`) :
  - Existe. Créer : `mise lock` (résout sans installer). Installer strictement ce qu'il contient : `mise install --locked`.
  - Création automatique : `lockfile = true` sous `[settings]` dans `mise.toml` ; sans ce réglage, mise met à jour un lock existant mais n'en crée pas.
  - À committer avec `mise.toml`. `mise.local.lock` ne se committe pas.
  - Plateformes : `mise lock --platform linux-x64,linux-arm64,macos-arm64`.
  - `MISE_LOCKED=1` : échoue si une entrée manque. `MISE_SAFE=1` : refuse tâches, `exec()` de templates et installations de plugins, et saute les hooks. Pratique pour un bot qui met à jour le lock.
  - Le lock ne couvre que les outils ; `uv.lock`, `package-lock.json` restent nécessaires.
  - Le changelog de `v2026.11.2` mentionne des corrections du lock en mode sûr (`MISE_SAFE=1 MISE_LOCKED=1 mise install` pour node, python, go). Source : page de release GitHub.

### 3. jdx/mise-action (v5.2.6)

- Version courante : **v5.2.6**, publiée le 2026-11-02. SHA du commit : **`f5be966e4a917d54244728e6a5fdcd1d93a35e6c`**. Le tag `v5.2.6` est un tag léger qui pointe directement sur ce commit (vérifié via l'API git refs).
- Exemple (README au tag v5.2.6) :
  ```yaml
  - uses: jdx/mise-action@v5
    with:
      version: 2026.3.10
      install: true
      cache: true
      github_token: ${{ secrets.GITHUB_TOKEN }}
  ```
- Entrées principales (valeurs par défaut) : `version` (« la release la plus récente vieille d'au moins 24 h ») ; `install` (`true`) ; `install_args` ; `cache` (`true`, cache GitHub) ; `cache_key_prefix` (`mise-v1`) ; `cache_max_age_days` (`30`) ; `experimental` (`false`) ; `working_directory` (`.`) ; `mise_toml` ; `env` (`true`) ; `minimum_release_age` (`24h`) ; `github_token` (`${{ github.token }}`).
- `github_token` : mise interroge l'API GitHub pour les outils hébergés sur GitHub (ex. `gh`, `node`, `bun`) ; sans jeton, les appels sont limités et l'installation peut échouer avec une erreur de limite de débit. Le défaut (jeton du workflow) suffit en général.

### 4. gitleaks 8.x (et son successeur)

- **Statut** : le README du dépôt `gitleaks/gitleaks` indique : « Gitleaks is feature complete. I'm not merging new features into Gitleaks. » et « Future releases will be security patches only. » Le successeur indiqué est `github.com/betterleaks/betterleaks`. Source primaire : README (sans date sur la page). Une recherche web (mars 2026) va dans le même sens (secondaire). **Décision à poser** : gitleaks ou betterleaks (choix d'outil).
- **Commandes** (source : `cmd/git.go` et `cmd/root.go` du dépôt gitleaks, branche `master`, qui peut être plus récent que le tag v8.30.1) :
  - Scanner l'index avant commit : `gitleaks git --pre-commit --staged` (`--pre-commit` : « scan using git diff » ; `--staged` : « scan staged commits (good for pre-commit) »). Forme à vérifier sur la version épinglée (`gitleaks git --help`).
  - Historique : `gitleaks git -v --log-opts="--all" .` (le README indique que `--log-opts` passe des options à `git log -p`).
  - Redaction : flag `--redact` (type entier). **Conflit** : le flag source a une valeur par défaut `0`, alors que le README indique « default is 100 percent ». Exemple documenté : `--redact=20`. À vérifier sur la version épinglée.
  - Config : `--config` / `-c` ; ordre de priorité : `--config`, variable `GITLEAKS_CONFIG` (chemin), `GITLEAKS_CONFIG_TOML` (contenu), puis `.gitleaks.toml` dans le dossier scanné.
  - Ignorés : `-i` / `--gitleaks-ignore-path` (chemin du `.gitleaksignore`).
  - Code de sortie : `--exit-code` (défaut `1`).
  - Rapport : `-r` / `--report-path` ; `-f` / `--report-format` (json, csv, junit, sarif, template).
- **`.gitleaks.toml`** : `[extend]` avec `useDefault = true` pour reprendre les règles par défaut, ajouté en v8.9.0 (release GitHub v8.9.0 ; exemples tiers). Confiance moyenne : une seule recherche, pas la doc officielle. Le fichier par défaut `config/gitleaks.toml` contient `minVersion = "v8.25.0"` et une section `[allowlist]`.
- **`.gitleaksignore`** : format d'empreinte `<commit>:<chemin>:<règle>:<ligne>`. Le commit est une SHA complète jusqu'à v8.25, une SHA courte (7 caractères) à partir de v8.26 ; lister les deux formes couvre les deux versions. Les empreintes sont liées au commit : une réécriture d'historique les rend obsolètes. Sources : pages tierces (PR GitHub), confiance faible à moyenne ; la doc officielle n'a pas été trouvée sur ce point.
- **Pre-commit** : le README montre un hook `pre-commit` (`rev: v8.24.2`, exemple, pas forcément la dernière version). `SKIP=gitleaks git commit ...` saute le hook.
- **Betterleaks** : v1.10.0 (2026-11-04). Notes de version : « `.gitleaks.toml` et `.betterleaks.toml` ne sont chargés automatiquement qu'avec `--unsafe-auto-load-config` » (changement de sécurité à connaître) ; isolation de la config Git locale par défaut. Un article secondaire indique que Betterleaks accepte les mêmes flags et le même format de config ; non vérifié sur le code source (la requête au fichier `git.go` a échoué).

### 5. Hooks Claude Code (`code.claude.com/docs/en/hooks`)

- **Schéma `.claude/settings.json`** (exemple de la doc, `PreToolUse` ; même structure pour `PostToolUse`) :
  ```json
  {
    "hooks": {
      "PreToolUse": [
        {
          "matcher": "Bash",
          "hooks": [
            {
              "type": "command",
              "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/nom.sh",
              "timeout": 30
            }
          ]
        }
      ]
    }
  }
  ```
  - `matcher` : nom de l'outil pour les événements d'outil ; `"*"`, `""` ou absent = tous. La syntaxe « A|B » n'a pas été vérifiée.
  - `type` : `command`, `http`, `mcp_tool`, `prompt` ou `agent`.
  - `timeout` : en secondes. Défaut : 600 pour `command`.
  - `if` : filtre optionnel (« best-effort », pas une frontière de sécurité). `args` : si présent, exécution sans shell.
  - `onFailure: "block"` : disponible à partir de Claude Code v2.1.295.
- **Entrée JSON sur stdin** : champs communs `session_id`, `cwd`, `hook_event_name`, `transcript_path`, `permission_mode` ; pour les événements d'outil, `tool_name`, `tool_input`, `tool_use_id`. Pour Bash, `tool_input.command` ; pour Write/Edit, `tool_input.file_path` (d'après un exemple de la doc, confiance moyenne).
- **`$CLAUDE_PROJECT_DIR`** : « the project root where the session started » ; reste fixe quand `cwd` change (worktree) ; exporté dans le processus du hook.
- **Codes de sortie** :
  - `0` : succès. Le JSON éventuel sur stdout est interprété. Sur `UserPromptSubmit`, `SessionStart` ou `PostModelSwitch`, la sortie est ajoutée au contexte de Claude. « Claude never sees stderr from a hook that exits 0. »
  - `2` : erreur bloquante (sur les événements qui peuvent bloquer) ; stderr est la raison transmise à Claude. Sur `PostToolUse`, l'outil a déjà tourné : stderr est montré à Claude, sans blocage.
  - autre (y compris `1`) : erreur non bloquante ; l'action continue, avec une notice.
- **Permissions et `--dangerously-skip-permissions`** :
  - Les hooks `PreToolUse` s'exécutent avant le prompt de permission, pour chaque outil (doc permissions).
  - Les règles `deny` restent appliquées même si un hook `PreToolUse` renvoie `allow` : « Claude Code evaluates deny and ask rules regardless of what a PreToolUse hook returns » (doc permissions, `code.claude.com/docs/en/permissions`).
  - Mode `bypassPermissions` (équivalent de `--dangerously-skip-permissions`) : « Deny rules block in every mode, including bypassPermissions. » Les règles `allow` n'ont aucun effet dans ce mode (doc `permission-modes`).
  - **Non vérifié** : si les hooks `PreToolUse` continuent de s'exécuter en `bypassPermissions`. La doc ne le dit pas explicitement ; le champ `permission_mode` peut valoir `bypassPermissions`. Ne pas supposer qu'ils sont désactivés : tester.

### 6. GitHub

- **Issue forms** (`docs.github.com/.../syntax-for-issue-forms`) : fichier YAML dans `.github/ISSUE_TEMPLATE/`. Clés de premier niveau obligatoires : `name`, `description`, `body`. Optionnelles : `title`, `labels`, `assignees`, `projects` (format `OWNER/NUMÉRO`), `type`. Types d'éléments de `body` : `markdown`, `input`, `textarea`, `dropdown` (`options`, `multiple`), `checkboxes` (`options` avec `label` et `required`), `upload`. Chaque champ a un `id`, `attributes.label`, `validations.required`. Le suffixe `.yml` n'est pas explicitement cité dans la page lue (non vérifié à ce niveau).
- **`config.yml`** (`configuring-issue-templates-for-your-repository`) : dans `.github/ISSUE_TEMPLATE/`. Clés `blank_issues_enabled: false` et `contact_links` (chaque entrée a `name`, `url`, `about`). Effet à la fusion sur la branche par défaut.
- **Modèle de PR** (`about-issue-and-pull-request-templates`) : emplacements acceptés : racine du dépôt, dossier `docs/`, dossier caché `.github/`. Nom insensible à la casse, extension `.md` ou `.txt` possible. Le modèle doit être sur la branche par défaut. Le nom exact `pull_request_template.md` et un dossier `PULL_REQUEST_TEMPLATE/` ne sont pas cités par la page lue (non vérifié).
- **Événement `pull_request`** (`events-that-trigger-workflows`) : le type `edited` existe dans la liste (« opened, edited, closed, reopened, synchronize… »), sans définition sur la page. Les workflows des forks ne tournent pas par défaut, et `GITHUB_TOKEN` est en lecture seule sur les PR de forks.
- **Jeton à granularité fine** (`docs.github.com/.../managing-your-personal-access-tokens`) : permissions de dépôt : **Contents** (lecture/écriture) pour pousser ; **Pull requests** (lecture/écriture) pour ouvrir une PR ; **Workflows** (écriture) pour modifier `.github/workflows/`. La page ne dit pas explicitement que « Workflows » est requis pour ces fichiers ; elle le suggère dans son exemple. Confiance moyenne. La page n'a pas de date.
- **Rulesets** (`docs.github.com/en/rest/repos/rules`, version d'API `2026-03-10`) : `bypass_mode` accepte `always` (défaut), `pull_request` (contournement seulement sur les PR ; non applicable au type `DeployKey` ; seulement pour les rulesets de branche) et `exempt` (règles non exécutées pour cet acteur, sans entrée d'audit). `actor_type` : `Integration`, `OrganizationAdmin`, `RepositoryRole`, `Team`, `DeployKey`, `User`.
- **Provider Terraform `integrations/github` v6.13.0** (doc du dépôt, branche `main`, fichier `docs/resources/repository_ruleset.md`) :
  ```terraform
  bypass_actors {
    actor_id    = 13473
    actor_type  = "Integration"
    bypass_mode = "always"
  }
  ```
  `bypass_mode` est optionnel et accepte `always`, `pull_request`, `exempt` (la doc ne décrit en détail que `pull_request`). `actor_type` inclut aussi `EnterpriseOwner`. `required_status_checks` contient `required_check { context, integration_id }`, `strict_required_status_checks_policy` (défaut `false`) et `do_not_enforce_on_create` (défaut `false` : « allows repository and branch creation even if a check would otherwise block it »). Une issue du provider (n° 2802) mentionne les tests des trois modes ; la version où `exempt` est apparu n'a pas été vérifiée. `~> 6.0` couvre v6.13.0.
- **Premier push vers un dépôt vide couvert par un ruleset** : **non vérifié**. Aucune doc officielle trouvée. Pistes : le paramètre `do_not_enforce_on_create` du provider et une discussion communautaire GitHub (« Required Workflows break repository auto_init », orgs/community #58854) suggèrent qu'un ruleset peut bloquer la création ou le premier push. À tester dans un dépôt jetable avant de compter dessus.

### 7. `terraform.lock.hcl` pour plusieurs plateformes

- Commande (`developer.hashicorp.com/terraform/cli/commands/providers/lock`) : `terraform providers lock -platform=linux_amd64 -platform=darwin_arm64 -platform=windows_amd64` (répéter `-platform` ; format `OS_ARCH`). Options : `-fs-mirror=PATH`, `-net-mirror=URL`, `-enable-plugin-cache`, `-var`, `-var-file`.
- Sans adresse de provider, la commande met à jour tous les providers du dossier. Avec `-fs-mirror` ou `-net-mirror`, seuls les checksums fournis par le miroir sont ajoutés. Seul le registre d'origine fournit des checksums officiels signés.
- Le format interne du fichier `.terraform.lock.hcl` n'est **pas décrit dans les pages lues** : non vérifié, ne pas le documenter d'après la mémoire.

### 8. Licence Terraform

- Le fichier `LICENSE` de `hashicorp/terraform` (branche `main`) est la **Business Source License 1.1**, pas la MPL. Licencié : IBM (`International Business Machines Corporation`) pour « Terraform Version 1.6.0 or later ». Usage en production permis, sauf offre à des tiers « en concurrence avec » les versions payantes d'IBM. La MPL 2.0 n'est que la **Change License** : elle s'applique quatre ans après la Change Date (ou quatre ans après la première distribution d'une version donnée, selon le premier événement).
- Conséquence : licence source-disponible, pas open source au sens de l'OSI, pour les versions récentes. À signaler si la licence du projet compte.

### 9. Compatibilité Python (torch, shapely, osmium)

Source : métadonnées PyPI (JSON `pypi.org/pypi/<nom>/json`), classifiers et `requires_python`.

| Paquet | Version | Date de publication | `requires_python` | Classifiers Python listés |
|---|---|---|---|---|
| torch | 2.15.0 | 2026-10-28 | `>=3.11` | 3.14 et 3.15 |
| shapely | 2.2.0 | 2026-10-07 | `>=3.11` | 3.13, 3.14, 3.15 |
| osmium (pyosmium, nom PyPI `osmium`) | 4.3.2 | 2026-10-18 | `>=3.8` | 3.13, 3.14 ; **3.15 absent** |

- Le nom PyPI de pyosmium est `osmium` (`pypi.org/pypi/pyosmium/json` renvoie 404).
- Les classifiers sont des déclarations du mainteneur, pas une garantie de test.
- Python 3.15.2 : compatibilité complète non démontrée (osmium ne le déclare pas). Python 3.14.10 : les trois paquets déclarent 3.14. **Confiance moyenne.**

## Niveau de confiance

- Élevé : versions et dates publiées sur GitHub, npm, PyPI, canal Rust, calendrier Node (dépôt officiel), statut gitleaks (README), licence Terraform (fichier LICENSE), SHA de mise-action.
- Moyen : schéma des hooks (doc officielle, quelques champs vus seulement dans un exemple), permission Workflows, `[extend]` de gitleaks, compatibilité Python par classifiers, Betterleaks.
- Faible ou non vérifié : comportement des hooks `PreToolUse` en `bypassPermissions`, premier push vers un dépôt vide sous ruleset, format `.gitleaksignore` (sources tierces), `terraform.lock.hcl`, syntaxe exacte de `mise trust`, nom du modèle de PR, détail du `.yml` des issue forms, version du provider où `bypass_mode` / `exempt` est apparu.

## Points à poser à l'utilisateur (choix structurants ou d'outil)

1. **gitleaks ou betterleaks** : gitleaks n'aura plus de nouvelles fonctionnalités ; betterleaks est son successeur (2026). Choix d'outil de sécurité.
2. **Version de Node** : 26 (Active LTS) ou 24 (maintenance jusqu'en 2028-04-30).
3. **Version de Python** : 3.14 (les trois paquets le déclarent) ou 3.15 (osmium ne le déclare pas).
4. **Épinglage de mise** : `version` fixe dans `mise-action` ou défaut « 24 h ». La version du jour a moins de 24 h.

## Tableau récapitulatif des versions proposées (sans trancher)

| Outil | Version proposée | Date | Backend mise / note |
|---|---|---|---|
| mise | 2026.11.2 | 2026-11-05 | `curl -fsSL https://mise.run \| sh` |
| Rust | 1.99.1 | 2026-10-15 (canal) | `core:rust` ; `rust-toolchain.toml` par opt-in |
| Node.js | 26.13.0 (Active LTS) ou 24.22.2 (Maintenance) | 2026-10-28 | `core:node` |
| Python | 3.14.10 (recommandé pour la compatibilité) ou 3.15.2 | 2026-10-25 | `core:python` |
| uv | 0.13.7 | 2026-11-03 | `aqua:astral-sh/uv` |
| just | 1.59.0 | 2026-10-15 | `aqua:casey/just` |
| Terraform | 1.17.1 (BSL 1.1) | 2026-10-28 | `aqua:hashicorp/terraform` |
| gitleaks | 8.30.1 (feature complete) | 2026-03-21 | `aqua:gitleaks/gitleaks` |
| betterleaks | 1.10.0 | 2026-11-04 | `aqua:betterleaks/betterleaks` |
| actionlint | 1.7.12 | 2026-03-30 | `aqua:rhysd/actionlint` |
| ruff | 0.17.3 | 2026-10-27 | `aqua:astral-sh/ruff` |
| taplo | 0.10.0 | 2025-05-23 | `aqua:tamasfe/taplo` |
| prettier | 3.9.10 | 2026-10-10 | `npm:prettier` |
| shfmt | 3.14.1 | 2026-09-06 | `aqua:mvdan/sh` |
| shellcheck | 0.11.0 | 2025-08-04 | `aqua:koalaman/shellcheck` |
| gh | 2.103.3 | 2026-10-26 | `aqua:cli/cli` |
| Claude Code | 2.1.318 | 2026-11-04 | `aqua:anthropics/claude-code` ; npm `@anthropic-ai/claude-code` (engines `>=22.0.0`) |
| jdx/mise-action | v5.2.6 (SHA `f5be966e4a917d54244728e6a5fdcd1d93a35e6c`) | 2026-11-02 | `uses: jdx/mise-action@<SHA>  # v5.2.6` (épingler par SHA) |
| provider github | v6.13.0 | 2026-07-08 | `version = "~> 6.0"` |

## Sources

- [mise — dernière release (API GitHub)](https://api.github.com/repos/jdx/mise/releases/latest) : v2026.11.2, 2026-11-05
- [mise — page de release v2026.11.2](https://github.com/jdx/mise/releases/tag/v2026.11.2) : changelog, corrections du lock
- [mise — démarrage (installation, mise.toml, trust)](https://mise.jdx.dev/getting-started.html) : doc officielle, date non indiquée
- [mise — Rust (`rust-toolchain.toml` par opt-in)](https://mise.jdx.dev/lang/rust.html) : doc officielle, date non indiquée
- [mise — lockfile](https://mise.jdx.dev/dev-tools/mise-lock.html) : doc officielle, date non indiquée
- [mise — registre des outils](https://mise.jdx.dev/registry.html) : doc officielle, date non indiquée
- [Rust — canal stable (`channel-rust-stable.toml`)](https://static.rust-lang.org/dist/channel-rust-stable.toml) : date du canal 2026-10-15
- [Node.js — calendrier de release (dépôt `nodejs/Release`)](https://raw.githubusercontent.com/nodejs/Release/main/README.md) : état courant, date non indiquée
- [Node.js — cycles (endoflife.date)](https://endoflife.date/api/nodejs.json) : dates de release 2026-10-21 et 2026-10-28
- [Python — téléchargements (python.org)](https://www.python.org/downloads/) : liste des versions, date non indiquée
- [Python — cycles (endoflife.date)](https://endoflife.date/api/python.json) : 3.15.2 et 3.14.10 au 2026-10-25
- [uv — dernière release (API GitHub)](https://api.github.com/repos/astral-sh/uv/releases/latest) : 0.13.7, 2026-11-03
- [just — dernière release (API GitHub)](https://api.github.com/repos/casey/just/releases/latest) : 1.59.0, 2026-10-15
- [Terraform — dernière release (API GitHub)](https://api.github.com/repos/hashicorp/terraform/releases/latest) : v1.17.1, 2026-10-28
- [Terraform — fichier LICENSE (branche `main`)](https://raw.githubusercontent.com/hashicorp/terraform/main/LICENSE) : BSL 1.1, IBM, date non indiquée
- [gitleaks — dernière release (API GitHub)](https://api.github.com/repos/gitleaks/gitleaks/releases/latest) : v8.30.1, 2026-03-21
- [gitleaks — README (statut « feature complete »)](https://github.com/gitleaks/gitleaks/blob/master/README.md) : date non indiquée
- [gitleaks — `cmd/git.go` (flags `--staged`, `--pre-commit`, `--log-opts`)](https://raw.githubusercontent.com/gitleaks/gitleaks/master/cmd/git.go) : branche `master`, date non indiquée
- [gitleaks — `cmd/root.go` (flags `--redact`, `--config`, `--gitleaks-ignore-path`, `--exit-code`, `--report-path`, `--report-format`)](https://raw.githubusercontent.com/gitleaks/gitleaks/master/cmd/root.go) : branche `master`
- [gitleaks — `config/gitleaks.toml` (minVersion v8.25.0)](https://raw.githubusercontent.com/gitleaks/gitleaks/master/config/gitleaks.toml) : branche `master`
- [Betterleaks — release v1.10.0 (API GitHub)](https://api.github.com/repos/betterleaks/betterleaks/releases/latest) : 2026-11-04 ; notes sur les chargements automatiques de config
- [actionlint — dernière release (API GitHub)](https://api.github.com/repos/rhysd/actionlint/releases/latest) : v1.7.12, 2026-03-30
- [ruff — dernière release (API GitHub)](https://api.github.com/repos/astral-sh/ruff/releases/latest) : 0.17.3, 2026-10-27
- [taplo — dernière release (API GitHub)](https://api.github.com/repos/tamasfe/taplo/releases/latest) : 0.10.0, 2025-05-23
- [prettier — dernière release (API GitHub)](https://api.github.com/repos/prettier/prettier/releases/latest) : 3.9.10, 2026-10-10
- [prettier — npm](https://registry.npmjs.org/prettier/latest) : 3.9.10, engines `>=14`
- [shfmt (`mvdan/sh`) — dernière release (API GitHub)](https://api.github.com/repos/mvdan/sh/releases/latest) : v3.14.1, 2026-09-06
- [shellcheck — dernière release (API GitHub)](https://api.github.com/repos/koalaman/shellcheck/releases/latest) : v0.11.0, 2025-08-04
- [gh — dernière release (API GitHub)](https://api.github.com/repos/cli/cli/releases/latest) : v2.103.3, 2026-10-26
- [Claude Code — dernière release (API GitHub)](https://api.github.com/repos/anthropics/claude-code/releases/latest) : v2.1.318, 2026-11-04
- [Claude Code — npm (`latest`)](https://registry.npmjs.org/@anthropic-ai/claude-code/latest) : 2.1.318, engines `>=22.0.0`
- [Claude Code — hooks (doc officielle)](https://code.claude.com/docs/en/hooks) : schéma, stdin, codes de sortie ; date non indiquée
- [Claude Code — permissions (doc officielle)](https://code.claude.com/docs/en/permissions) : précédence hooks / deny ; date non indiquée
- [Claude Code — modes de permission (doc officielle)](https://code.claude.com/docs/en/permission-modes) : deny en `bypassPermissions` ; date non indiquée
- [mise-action — dernière release (API GitHub)](https://api.github.com/repos/jdx/mise-action/releases/latest) : v5.2.6, 2026-11-02
- [mise-action — tag v5.2.6 (API git refs)](https://api.github.com/repos/jdx/mise-action/git/refs/tags/v5.2.6) : SHA `f5be966e4a917d54244728e6a5fdcd1d93a35e6c`
- [mise-action — README au tag v5.2.6](https://raw.githubusercontent.com/jdx/mise-action/v5.2.6/README.md) : inputs et défauts
- [GitHub — permissions de jeton à granularité fine](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) : page sans date
- [GitHub — API des rulesets (version 2026-03-10)](https://docs.github.com/en/rest/repos/rules) : `bypass_mode`, `actor_type`
- [GitHub — about rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) : sans date
- [GitHub — syntaxe des issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms) : sans date
- [GitHub — configuration des templates d'issues (`config.yml`)](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository) : sans date
- [GitHub — modèles d'issues et de PR](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates) : sans date
- [GitHub — événements déclencheurs de workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) : sans date
- [Provider Terraform GitHub — `repository_ruleset` (branche `main`)](https://raw.githubusercontent.com/integrations/terraform-provider-github/main/docs/resources/repository_ruleset.md) : `bypass_actors`, `required_status_checks`
- [Provider Terraform GitHub — dernière release (API GitHub)](https://api.github.com/repos/integrations/terraform-provider-github/releases/latest) : v6.13.0, 2026-07-08
- [Provider Terraform GitHub — issue 2802 (secondaire, via recherche)](https://github.com/integrations/terraform-provider-github/issues/2802) : tests des modes `always`, `pull_request`, `exempt`
- [Terraform — `providers lock` (doc officielle)](https://developer.hashicorp.com/terraform/cli/commands/providers/lock) : options `-platform`, `-fs-mirror` ; date non indiquée
- [PyPI — torch (JSON)](https://pypi.org/pypi/torch/json) : version 2.15.0, classifiers 3.14 et 3.15
- [PyPI — torch 2.15.0 (JSON)](https://pypi.org/pypi/torch/2.15.0/json) : publiée 2026-10-28
- [PyPI — shapely 2.2.0 (JSON)](https://pypi.org/pypi/shapely/2.2.0/json) : publiée 2026-10-07 ; classifiers 3.13 à 3.15 (via `shapely/json`)
- [PyPI — osmium 4.3.2 (JSON)](https://pypi.org/pypi/osmium/4.3.2/json) : publiée 2026-10-18 ; classifiers 3.13 et 3.14 (via `osmium/json`)
- [PEP 790 (calendrier Python 3.15, secondaire, via recherche)](https://peps.python.org/pep-0790/) : prévision 2026-10-01, différente de la date python.org
- [gitleaks — release v8.9.0 (`[extend]`, secondaire)](https://github.com/gitleaks/gitleaks/releases/tag/v8.9.0) : fonctionnalité ajoutée en v8.9.0
- [Betterleaks — article secondaire (via recherche)](https://aikido.dev/blog/gitleaks-alternatives) : mêmes flags et config, non vérifié sur le code

Recherches web à usage de contexte uniquement (agrégateurs de versions, pages de news) : non retenues comme preuve.
