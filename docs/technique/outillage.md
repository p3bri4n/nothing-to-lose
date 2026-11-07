# Outillage : versions des outils, formatage et vérification

*Mise à jour : 2026-11-07 (ajout du hook de formatage à l'édition, de `just verify-pp` et de ses sous-commandes `format` et `secrets`, des recettes de hooks Git et de `secrets-scan`)*

Décrit le code **tel qu'il existe** : source unique des versions, commande `just versions`, formatage (`tools/fmt.py`, `just fmt`, `just fmt-check`), recette `just lint`, tests des outils, sous-commande `tools/verify_pp.sh versions`, procédure de mise à jour. La politique (versions exactes partout) est dans [0011](../decisions/0011-politique-versions-exactes.md) ; le Markdown hors formatage est dans [0012](../decisions/0012-markdown-hors-formatage.md). Les sources et dates des versions sont dans [la note de recherche](../recherches/2026-11-05-outillage-pp.md).

## Source unique des versions

| Fichier | Rôle |
|---|---|
| [`mise.toml`](../../mise.toml) | Table `[tools]` : une version exacte par outil (`node`, `python`, `rust`, `aqua:…`, `npm:prettier`). Table `[env]` : `UV_PYTHON_DOWNLOADS = "never"`. |
| [`rust-toolchain.toml`](../../rust-toolchain.toml) | Table `[toolchain]` : `channel`, `components`, `targets` du toolchain Rust. |

Règles :

- **Versions exactes** partout, y compris Claude Code (`aqua:anthropics/claude-code`), conformément à [0011](../decisions/0011-politique-versions-exactes.md). Pas de plage ni de préfixe.
- Le `channel` de `rust-toolchain.toml` doit être **égal** à la valeur `rust` de `mise.toml` (comparaison d'égalité : `stable` ou tout autre nom symbolique est refusé). L'incohérence est une erreur de configuration.
- La clé `rust` de `mise.toml` peut être une table (`{ version = "…", components = "…", targets = "…" }`) ; seul `version` est lu par le script.
- Ne jamais ajouter un chemin de dépôt dans `PATH` via `mise.toml` (le chemin contient `:`, voir `docs/plans/PP.md`, R1).

Le fichier `mise.toml` porte un commentaire d'en-tête qui affirme que le même fichier sert en CI (`jdx/mise-action`). **À la date de cette page, aucun workflow de `.github/workflows/` ne mentionne mise ni `just versions`** : cette utilisation en CI n'existe pas encore.

## `just versions`

Recette du `justfile` :

```
python3 tools/check_tool_versions.py [--ci si CI=true]
```

Le script est `tools/check_tool_versions.py`. Il se lance depuis n'importe quel répertoire (`REPO_ROOT` est déduit de sa propre position). Il utilise le `python` du `PATH` ; Python 3.11 au moins est nécessaire (module `tomllib`).

### Options

| Option | Effet |
|---|---|
| `--ci` | Ignore les outils marqués `local_only` (aujourd'hui : Claude Code). Activé automatiquement par la recette quand la variable d'environnement `CI` vaut `true`. |
| `--print` | Affiche la liste normalisée `binaire version attendue` (une ligne par outil retenu) et termine **sans exécuter aucun outil**. Les erreurs de configuration sont tout de même signalées. |
| `-h`, `--help` | Aide (module `argparse`). Une option inconnue donne le code 2. |

### Fonctionnement

1. Lecture de `mise.toml` et `rust-toolchain.toml`. Les clés de `mise.toml` sont normalisées (`aqua:astral-sh/uv` → `uv`, `npm:prettier` → `prettier`, `aqua:cli/cli` → `cli`).
2. Les seuls outils contrôlés sont ceux qui ont une entrée dans la table `TOOLS` du script. Une entrée de `TOOLS` absente de `mise.toml` est ignorée sans message.
3. Pour chaque outil, le binaire est lancé avec ses arguments (`--version` par défaut) via le `PATH` réel, avec un délai de 20 secondes (`TIMEOUT_SECONDS`). La sortie est lue sur stdout **et** stderr.
4. La version est extraite par une expression régulière propre à chaque outil (table `TOOLS`), qui doit contenir exactement un groupe : le numéro de version nu, sans `v`.

### Format de sortie

Une ligne par outil, dans l'ordre de `mise.toml` :

```
tool        expected  found     status
```

- `tool` : nom du **binaire** (`node`, `python`, `rustc`, `uv`, `just`, `terraform`, `gitleaks`, `actionlint`, `ruff`, `taplo`, `prettier`, `shfmt`, `shellcheck`, `gh`, `claude`), pas la clé mise.
- `expected` : version de `mise.toml`.
- `found` : version trouvée, ou `-` si elle est absente.
- `status` : `ok`, `mismatch`, ou `missing` suivi d'un détail entre parenthèses :
  - `missing (not found in PATH)` : binaire absent du `PATH` ;
  - `missing (timeout after 20s)` ;
  - `missing (unparseable output)` : sortie vide ou non reconnue ;
  - `missing (cannot run (NomException))` : fichier non exécutable ou autre erreur d'exécution.

Les messages d'erreur de configuration vont sur **stderr**, préfixés par `error:` :

- `error: cannot load configuration: …` : fichier absent ou TOML invalide (`mise.toml` ou `rust-toolchain.toml`), ou entrée `mise.toml` illisible (ni chaîne ni table avec `version`) ;
- `error: mise.toml: several entries map to tool '…'` : deux clés `mise.toml` normalisées vers le même outil ;
- `error: tool '…' in mise.toml has no entry in TOOLS` : outil épinglé sans spécification de vérification (il faut l'ajouter à `TOOLS` et à la fixture de test) ;
- `error: rust-toolchain.toml channel '…' differs from mise.toml rust '…'`.

### Codes de retour

| Code | Sens |
|---|---|
| `0` | Tous les outils retenus sont `ok`, configuration cohérente. |
| `1` | Au moins un outil `missing` ou `mismatch`, ou erreur de configuration. Un échec ne bloque pas la vérification des autres outils. |
| `2` | Erreur d'usage (option inconnue) ; code émis par `argparse`. |

Avec `--print`, le code vaut `1` si la configuration est incohérente, `0` sinon ; aucun outil n'est lancé.

### Outils « local seulement »

`claude-code` (binaire `claude`) est marqué `local_only`. Il est contrôlé en local et **ignoré avec `--ci`**. En CI, un Claude Code absent ou en mauvaise version ne fait donc pas échouer la vérification.

## Formatage : `tools/fmt.py`

Recettes du `justfile` :

```
just fmt        # python3 tools/fmt.py --write
just fmt-check  # python3 tools/fmt.py --check
```

`tools/fmt.py` est la **seule source** de la correspondance extension → formateur (constantes `FORMATTERS` et `EXTENSIONS`). Le Markdown est exclu ([0012](../decisions/0012-markdown-hors-formatage.md)) : `README.md` et `docs/` ne sont jamais réécrits par l'outil.

Le script se lance depuis n'importe quel répertoire (`REPO_ROOT` est déduit de sa position). Il exige exactement une des options `--write` (réécrit les fichiers) ou `--check` (signale sans rien modifier).

### Correspondance extension → formateur

| Extension | Formateur | `--write` | `--check` |
|---|---|---|---|
| `.rs` | rustfmt | `rustfmt <fichiers>` | `rustfmt --check <fichiers>` |
| `.py` | ruff | `ruff format <fichiers>` | `ruff format --check <fichiers>` |
| `.toml` | taplo | `taplo fmt <fichiers>` | `taplo fmt --check <fichiers>` |
| `.tf` | terraform | `terraform fmt <fichiers>` | `terraform fmt -check -diff <fichiers>` |
| `.sh` | shfmt | `shfmt -i 2 -ci -w <fichiers>` | `shfmt -i 2 -ci -d <fichiers>` |
| `.json`, `.yaml`, `.yml`, `.js`, `.ts`, `.html`, `.css` | prettier | `prettier --write --config <racine>/.prettierrc.json <fichiers>` | `prettier --check --config <racine>/.prettierrc.json <fichiers>` |

- `.yml` a été ajouté à la table du plan PP (les workflows GitHub sont en `.yml`) ; il est traité comme `.yaml`.
- Extensions comparées en minuscules ; seule la dernière extension compte (`a.tar.json` → prettier, `a.py.md` → aucun formateur).
- Les formateurs sont lancés via `mise exec --` depuis la racine du dépôt, pour que les versions de `mise.toml` et les fichiers de configuration de la racine s'appliquent. Les commandes sont des listes d'arguments, jamais des chaînes passées au shell. Un chemin qui commence par `-` est préfixé par `./`.
- prettier reçoit **toujours** `--config <racine>/.prettierrc.json` (champ `config_file` de `Formatter`, argument `root` de `build_command`) : sa recherche de configuration vers le haut est alors désactivée, donc un `prettier.config.js` (que prettier exécute) placé près d'un fichier formaté n'est jamais chargé. `.editorconfig` reste lu (pas de code exécutable). Vérifié par `PrettierConfigIsolationTest` (voir ci-dessous).
- Un formateur est lancé **une seule fois** avec tous ses fichiers ; délai de 600 secondes (`TIMEOUT_SECONDS`). Tous les formateurs sont lancés même si l'un échoue.

### Fichiers traités

- **Sans chemin** : fichiers suivis par Git (`git ls-files -z`) qui existent encore sur le disque, sauf ceux de `tools/tests/fixtures/format/` (`EXCLUDED_DIRS`), puis filtrés par extension.
- **Avec chemins** : chemins relatifs au répertoire courant, résolus. Aucune exclusion. Une extension sans formateur est ignorée sans message. Un chemin inexistant produit `error: not a file: …` ; les autres chemins sont traités quand même.

### Sortie et codes de retour

Message d'un formateur en échec : `error: <formateur> needs formatting (exit N, K file(s))` en `--check`, `… failed` en `--write`. Une absence du binaire produit `error: cannot run 'mise' (not in PATH)`. La dernière ligne est une synthèse : `fmt write: N file(s), M formatter(s), ok` (ou `FAILED`), avec `check` à la place de `write` en mode `--check`.

| Code | Sens |
|---|---|
| `0` | Tout est formaté (`--check`), ou le formatage a réussi (`--write`). |
| `1` | Fichier non formaté (`--check`), formateur en échec ou absent, délai dépassé, chemin inexistant, liste des fichiers Git impossible. |
| `2` | Erreur d'usage (option absente, incompatible ou inconnue) ; code émis par `argparse`. |

`terraform fmt -check` renvoie **3** (et non 1) quand un fichier n'est pas formaté. `fmt.py` ne distingue pas les codes non nuls : il affiche `needs formatting` et renvoie `1`. La recette `just tf-check` appelle directement `terraform fmt -check -recursive` et échoue donc avec le code 3.

### Configuration des formateurs

Fichiers à la racine du dépôt, lus par les formateurs :

| Fichier | Réglages principaux |
|---|---|
| [`ruff.toml`](../../ruff.toml) | `line-length = 88`, `indent-width = 4`, `target-version = "py314"` (version de `mise.toml`), `quote-style = "double"`, indentation par espaces, `line-ending = "lf"`. Le fichier ne contient que des réglages de formatage (aucune sélection de règles de lint ; `ruff check` appliquerait ses règles par défaut). |
| [`taplo.toml`](../../taplo.toml) | `indent_string = "  "` (deux espaces), `column_width = 88`, `reorder_keys`, `reorder_arrays` et `align_entries` à `false`, `array_auto_expand` et `array_auto_collapse` à `true`, `trailing_newline = true`. |
| [`.prettierrc.json`](../../.prettierrc.json) | `printWidth = 88`, `tabWidth = 2`, `useTabs = false`, `endOfLine = "lf"`. |
| [`.prettierignore`](../../.prettierignore) | `*.md` (Markdown exclu, [0012](../decisions/0012-markdown-hors-formatage.md)). |
| [`rustfmt.toml`](../../rustfmt.toml) | `edition = "2024"`, `max_width = 100`, `newline_style = "Unix"`. **À reconfirmer en P1**, quand le premier crate arrivera. |
| [`.editorconfig`](../../.editorconfig) | UTF-8, fins de ligne `lf`, newline final, suppression des espaces en fin de ligne, indentation par espaces ; 2 espaces par défaut, 4 pour `*.py` et `*.rs`, 2 pour `*.sh` avec `switch_case_indent = true` (`fmt.py` passe aussi `-i 2 -ci` à shfmt explicitement), 4 pour le `justfile`. `*.md` : `trim_trailing_whitespace = false` (les doubles espaces de fin de ligne sont conservés). Son en-tête indique qu'il est aussi lu par shfmt et prettier. |
| [`.gitattributes`](../../.gitattributes) | `* text=auto eol=lf`. |

### Recettes `just` de contrôle

| Recette | Contenu |
|---|---|
| `fmt` | `python3 tools/fmt.py --write`, puis `just --fmt --unstable` (formate le `justfile`). |
| `fmt-check` | `python3 tools/fmt.py --check`, puis `just --fmt --check --unstable` (vérifie le `justfile`). |
| `docs-links` | `python3 tools/check_links.py` |
| `verify-pp *ARGS` | `bash tools/verify_pp.sh <sous-commande>` (voir plus bas). |
| `hooks-install` | `git config core.hooksPath .githooks` (action locale ; appelée par `setup`). Voir [`hooks-git.md`](hooks-git.md). |
| `pre-commit` | `gitleaks git --pre-commit --staged --redact`, puis `just docs-links` (appelée par le hook Git). |
| `secrets-scan` | `gitleaks git --redact` sur tout l'historique. |
| `lint` | `versions`, `tools-test`, `fmt-check`, `docs-links`, `secrets-scan`, `tf-check`. |
| `check` | `lint` seul pour l'instant (P1 y ajoutera tests, non-régression, invariants, mini-partie). |

`lint` n'inclut pas encore `actionlint` (étape E8) : le commentaire du `justfile` le rappelle. `secrets-scan` y figure depuis l'étape E7 et appelle `gitleaks` du `PATH` (donc `mise exec -- just lint` si mise n'est pas activé dans le shell). `tf-check` vérifie `terraform fmt -check -recursive` puis `terraform validate` dans `infra/terraform/`.

## Hook de formatage à l'édition

Le hook `PostToolUse` de `.claude/settings.json` lance `tools/hooks/format_on_edit.py` après chaque `Write`, `Edit` ou `MultiEdit` de Claude Code. Il appelle `tools/fmt.py --write <fichier>` sur le seul fichier touché, ne bloque jamais la session, refuse de formater tant que la configuration des outils (`mise.toml`, `mise.local.toml`, `.prettierrc.json`, `rust-toolchain.toml`) diffère de `HEAD`, et se désactive avec `NTL_FORMAT_HOOK=off`. Comportement, journal et limites : [`hook-format-on-edit.md`](hook-format-on-edit.md).

## `just tools-test` : tests des outils

```
python3 -m unittest discover -s tools/tests
```

- Fichiers : `tools/tests/__init__.py` (vide), `tools/tests/test_check_tool_versions.py`, `tools/tests/test_fmt.py` et `tools/tests/test_git_hooks.py` (hook Git `pre-commit` avec un faux `mise`, voir [`hooks-git.md`](hooks-git.md)) et `tools/tests/test_format_on_edit.py` (surtout hermétique : `subprocess.run` et `subprocess.Popen` sont remplacés par des faux ; quelques tests utilisent le vrai `git` dans un dépôt jetable ou un vrai processus enfant ; voir [`hook-format-on-edit.md`](hook-format-on-edit.md)).
- **Hermétiques** pour `test_check_tool_versions.py` : `subprocess.run` est remplacé par un faux (`fake_run`) ; aucun outil réel n'est exécuté. La configuration est écrite dans un répertoire temporaire, et `REPO_ROOT` est redirigé vers lui (`MainTests.setUp`).
- Classes de `test_check_tool_versions.py` : `ParseVersionTests`, `HelpersTests`, `CompareTests`, `FormatLineTests`, `RustToolchainTests`, `RunVersionTests`, `MainTests`.
- Classes de `test_fmt.py` : `FormatterSelectionTest`, `PathFilteringTest`, `BuildCommandTest`, `RunFormatterTest`, `ResolveExplicitTest`, `MainTest` (hermétiques : aucun formateur n'est exécuté), `FixtureIntegrationTest` (une sous-épreuve par fixture, ignorée avec un message si `mise` ou le formateur manque ; disponibilité mise en cache, un seul `mise exec` par formateur) et `PrettierConfigIsolationTest` (un `prettier.config.js` piégé, qui écrit un fichier témoin, est placé dans un dossier temporaire à côté d'un `.js` : sans `--config` il s'exécute — contrôle —, avec la commande de `fmt.py` il ne s'exécute pas ; ignoré si `mise` ou prettier manque).
- `FixtureIntegrationTest` **n'est pas hermétique** : il lance les vrais formateurs sur les fixtures lorsque `mise exec -- <outil> --version` réussit pour l'outil concerné, et passe ce cas sinon. Il est sauté entièrement si aucun formateur n'est disponible.

### Fixtures de formatage

`tools/tests/fixtures/format/` contient onze fichiers mal formatés **volontairement**, un par extension : `bad.css`, `bad.html`, `bad.js`, `bad.json`, `bad.py`, `bad.rs`, `bad.sh`, `bad.tf`, `bad.toml`, `bad.ts`, `bad.yaml`. Il n'y a pas de `bad.yml`. Chacun doit être signalé comme non formaté par `--check`. Ce dossier est exclu de `just fmt` et de `just fmt-check` sans chemin explicite.
- Données de test (en tête du fichier) :
  - `FIXTURES` : sorties réelles de `--version` des versions épinglées, relevées le 2026-11-07, indexées par nom de binaire ;
  - `FIXTURE_VERSIONS` : version attendue pour chaque fixture ;
  - `MISE_TOML` et `TOOLCHAIN_TOML` : copies de la configuration utilisées par les tests.
- Le test `test_every_tool_has_a_fixture` impose qu'un outil ajouté à `TOOLS` ait une fixture.
- `MISE_TOML` des tests est une **copie** de `mise.toml` : rien ne vérifie automatiquement qu'elle reste identique. Elle se met à jour à la main avec la montée de version.

## `tools/verify_pp.sh`

Point d'entrée du jalon PP (script Bash, `set -euo pipefail`). Syntaxe :

```
tools/verify_pp.sh <sous-commande> [arguments]
```

| Sous-commande | Effet |
|---|---|
| `versions` | Lance `python3 tools/check_tool_versions.py` avec les arguments transmis (`--ci`, `--print`…). |
| `format` | Partie automatique du critère C2 (hook de formatage) : voir ci-dessous. |
| `secrets` | Critère C1 (hook Git `pre-commit` et gitleaks) dans un dépôt temporaire : voir [`hooks-git.md`](hooks-git.md). |

Codes de retour :

- `2` : aucune sous-commande, ou sous-commande inconnue (message d'usage sur stderr) ;
- sinon, le code de retour de `check_tool_versions.py` (`0`, `1`, ou `2` pour une option inconnue).

La recette `just verify-pp <sous-commande> [arguments]` lance `bash tools/verify_pp.sh "$@"` (`set positional-arguments` dans le `justfile` : les arguments gardent leurs frontières).

### Sous-commande `format`

Crée un dossier temporaire `.verify-pp-format.XXXXXX` **à la racine du dépôt** (le hook ignore ce qui est hors du projet ou ignoré par Git, donc ni `/tmp` ni `.cache/`), supprimé à la sortie par un `trap EXIT`. Puis :

1. pour `bad.py`, `bad.toml`, `bad.tf`, `bad.sh`, `bad.yaml`, `bad.json`, `bad.rs` (copies des fixtures) : vérifie que `fmt.py --check` échoue avant, envoie au hook un JSON `PostToolUse` simulé, vérifie le code 0, l'absence de sortie sur stdout, puis que `fmt.py --check` réussit ;
2. un fichier `.md` mal formaté reste identique octet pour octet ;
3. avec `NTL_FORMAT_HOOK=off`, un fichier mal formaté reste inchangé ;
4. garde de la configuration : avec un `mise.local.toml` vide créé temporairement à la racine (ignoré par Git, mais présent), le hook ne touche pas un fichier mal formaté et écrit une ligne `formatting refused` dans le journal ; le fichier est supprimé aussitôt (et à la sortie, par le `trap`) ;
5. des entrées absurdes (stdin vide, `not json`, `{`, `[]`, `file_path` numérique, fichier inexistant) donnent le code 0 sans sortie.

**Saut propre** : si `mise.toml`, `mise.local.toml`, `.prettierrc.json` ou `rust-toolchain.toml` diffère de `HEAD` (modifié, non suivi, ignoré mais présent), le hook refuserait de formater et le test ne pourrait pas réussir : la sous-commande affiche `SKIP C2 (automatic part)` avec la liste des fichiers et sort avec le code 0. Il faut alors valider ou annuler ces changements puis relancer pour obtenir une vraie vérification.

Sortie finale : `OK C2 (automatic part)` et code 0, sinon `FAILED C2 (automatic part)` et code 1. Les entrées JSON invalides ajoutent des lignes à `.cache/hooks/format.log` du dépôt (ignoré par Git). Le test de bout en bout dans Claude Code reste manuel.

La sous-commande `secrets` est décrite dans [`hooks-git.md`](hooks-git.md). D'autres sous-commandes seront ajoutées au fil des étapes du jalon PP. Le script est un point d'entrée distinct de `just versions`, qui n'appelle pas le script shell.

## Procédure de mise à jour d'une version

Toute montée de version se fait dans une **pull request dédiée** ([0011](../decisions/0011-politique-versions-exactes.md)) :

1. Modifier la version dans `mise.toml`.
2. Si c'est Rust : modifier aussi `channel` dans `rust-toolchain.toml` (il doit rester égal à `rust` de `mise.toml`).
3. Si le format de sortie de `--version` de l'outil change : mettre à jour l'expression régulière de la table `TOOLS` (`tools/check_tool_versions.py`), la fixture de sortie réelle et `FIXTURE_VERSIONS` dans `tools/tests/test_check_tool_versions.py`, et la copie `MISE_TOML` si la clé ou la version change.
4. Lancer `just versions` (et `CI=true just versions` pour le mode CI) : tous les outils doivent être `ok`.
5. Lancer `just tools-test`.
6. Consulter ou compléter la note de recherche (sources, dates) dans [`docs/recherches/`](../recherches/README.md) ; une note de plus de trois mois sur un sujet qui évolue vite est à revérifier avant usage.

Ajouter un outil épinglé demande aussi une entrée dans `TOOLS` et une fixture, sinon `just versions` échoue (erreur « has no entry in TOOLS ») ou le test `test_every_tool_has_a_fixture` échoue.

Une montée de version d'un formateur (`ruff`, `taplo`, `prettier`, `shfmt`, `terraform`, Rust) peut changer le formatage produit : après la montée, lancer `just fmt-check` et, si des fichiers sont signalés, `just fmt` dans la même pull request, avec les fichiers reformatés. Le test `FixtureIntegrationTest` vérifie seulement que chaque fixture est détectée, pas la forme exacte du formatage.

## Commit « formatage initial »

Commit `5f37321` « Formatage initial du dépôt (just fmt) », séparé des suivants pour que leurs diffs restent lisibles. Il ne modifie que trois fichiers : `tools/check_links.py` (une ligne), `tools/hooks/session_start.py` (18 lignes) et `web/viewer/prototype/index.html` (1728 lignes modifiées).

## Points ouverts

- **`rustfmt.toml`** (`edition = "2024"`, `max_width = 100`) : à reconfirmer en P1, quand le premier crate sera créé.
- **CI** : le job `ci-cpu` (`.github/workflows/ci.yml`) n'exécute aujourd'hui que `python3 tools/check_links.py`, et `just check` seulement si `Cargo.toml` existe. Le workflow n'installe pas mise, donc `just fmt-check` et `just versions` ne tournent pas en CI à la date de cette page. Le plan PP prévoit ces étapes dans l'étape E9 (« CI alignée sur mise ») ; à vérifier à ce moment.
- **Hook de formatage à l'édition** : le test de bout en bout dans Claude Code (critère C2 manuel, risque R8) a été fait le 2026-11-07 (`MultiEdit` non testé) ; voir les résultats et les limites dans [`hook-format-on-edit.md`](hook-format-on-edit.md).
- **Vérification du dépôt** : que `just fmt-check` renvoie 0 sur l'état actuel n'est pas consigné par cette page ; le plan PP le demande comme critère d'acceptation de E5.

## Liens

- Politique : [0011, versions exactes partout](../decisions/0011-politique-versions-exactes.md), [0012, Markdown hors formatage](../decisions/0012-markdown-hors-formatage.md)
- Sources et dates des versions : [`docs/recherches/2026-11-05-outillage-pp.md`](../recherches/2026-11-05-outillage-pp.md)
- Hooks Git et gitleaks : [`hooks-git.md`](hooks-git.md)
- Jalon PP (étape E5 : formatage ; E4 : versions ; E7 : hooks Git) : [`docs/plans/PP.md`](../plans/PP.md)
- Infrastructure et CI : [`ci-cd.md`](ci-cd.md)
