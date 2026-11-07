# Outillage : versions des outils et vérification

*Mise à jour : 2026-11-07 (création)*

Décrit le code **tel qu'il existe** : source unique des versions, commande `just versions`, tests des outils, sous-commande `tools/verify_pp.sh versions`, procédure de mise à jour. La politique (versions exactes partout) est dans [0011](../decisions/0011-politique-versions-exactes.md). Les sources et dates des versions sont dans [la note de recherche](../recherches/2026-11-05-outillage-pp.md).

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
python tools/check_tool_versions.py [--ci si CI=true]
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

## `just tools-test` : tests des outils

```
python -m unittest discover -s tools/tests
```

- Fichiers : `tools/tests/__init__.py` (vide) et `tools/tests/test_check_tool_versions.py`.
- **Hermétiques** : `subprocess.run` est remplacé par un faux (`fake_run`) ; aucun outil réel n'est exécuté. La configuration est écrite dans un répertoire temporaire, et `REPO_ROOT` est redirigé vers lui (`MainTests.setUp`).
- Classes : `ParseVersionTests`, `HelpersTests`, `CompareTests`, `FormatLineTests`, `RustToolchainTests`, `RunVersionTests`, `MainTests`.
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
| `versions` | Lance `python tools/check_tool_versions.py` avec les arguments transmis (`--ci`, `--print`…). |

Codes de retour :

- `2` : aucune sous-commande, ou sous-commande inconnue (message d'usage sur stderr) ;
- sinon, le code de retour de `check_tool_versions.py` (`0`, `1`, ou `2` pour une option inconnue).

D'autres sous-commandes seront ajoutées au fil des étapes du jalon PP. Le script est un point d'entrée distinct de `just versions`, qui n'appelle pas le script shell.

## Procédure de mise à jour d'une version

Toute montée de version se fait dans une **pull request dédiée** ([0011](../decisions/0011-politique-versions-exactes.md)) :

1. Modifier la version dans `mise.toml`.
2. Si c'est Rust : modifier aussi `channel` dans `rust-toolchain.toml` (il doit rester égal à `rust` de `mise.toml`).
3. Si le format de sortie de `--version` de l'outil change : mettre à jour l'expression régulière de la table `TOOLS` (`tools/check_tool_versions.py`), la fixture de sortie réelle et `FIXTURE_VERSIONS` dans `tools/tests/test_check_tool_versions.py`, et la copie `MISE_TOML` si la clé ou la version change.
4. Lancer `just versions` (et `CI=true just versions` pour le mode CI) : tous les outils doivent être `ok`.
5. Lancer `just tools-test`.
6. Consulter ou compléter la note de recherche (sources, dates) dans [`docs/recherches/`](../recherches/README.md) ; une note de plus de trois mois sur un sujet qui évolue vite est à revérifier avant usage.

Ajouter un outil épinglé demande aussi une entrée dans `TOOLS` et une fixture, sinon `just versions` échoue (erreur « has no entry in TOOLS ») ou le test `test_every_tool_has_a_fixture` échoue.

## Liens

- Politique : [0011, versions exactes partout](../decisions/0011-politique-versions-exactes.md)
- Sources et dates des versions : [`docs/recherches/2026-11-05-outillage-pp.md`](../recherches/2026-11-05-outillage-pp.md)
- Jalon PP : [`docs/plans/PP.md`](../plans/PP.md)
- Infrastructure et CI : [`ci-cd.md`](ci-cd.md)
