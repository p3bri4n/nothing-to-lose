# Hooks Git avant commit et recherche de secrets (gitleaks)

*Mise à jour : 2026-11-07 (création, étape E7 du plan PP, voir [`../plans/PP.md`](../plans/PP.md) §E7, décisions D1 et D2, risques R5 et R13)*

Décrit le code **tel qu'il existe**. Le hook protège contre deux erreurs au moment du commit : un secret (jeton, clé) ajouté par mégarde, et un lien cassé dans la documentation. Le hook de formatage de Claude Code est une autre chose : voir [`hook-format-on-edit.md`](hook-format-on-edit.md).

## Fichiers

| Fichier | Rôle |
|---|---|
| [`.githooks/pre-commit`](../../.githooks/pre-commit) | Script Bash exécutable (mode `100755`), appelé par Git avant chaque commit. |
| [`.gitleaks.toml`](../../.gitleaks.toml) | Configuration de gitleaks : `[extend] useDefault = true`, aucune liste blanche. |
| `.gitleaksignore` | Absent à la date de cette page : aucun faux positif (voir plus bas). |
| [`justfile`](../../justfile) | Recettes `hooks-install`, `pre-commit`, `secrets-scan`. |
| [`tools/verify_pp.sh`](../../tools/verify_pp.sh) | Sous-commande `secrets` (critère C1). |
| [`tools/tests/test_git_hooks.py`](../../tools/tests/test_git_hooks.py) | Tests unitaires du hook (hermétiques). |

Le binaire gitleaks est celui de `mise.toml` (`aqua:gitleaks/gitleaks`, version exacte) : même version en local et, plus tard, en CI.

## Recettes `just`

| Recette | Contenu |
|---|---|
| `hooks-install` | `git config core.hooksPath .githooks`. Action **locale**, une fois par clone ; appelée par `just setup`. |
| `pre-commit` | `gitleaks git --pre-commit --staged --redact` (changements indexés), puis `just docs-links`. |
| `secrets-scan` | `gitleaks git --redact` : tout l'historique du dépôt. Membre de `lint`. |

`pre-commit` et `secrets-scan` appellent `gitleaks` tel quel : il doit être dans le `PATH`, ce que garantit `mise exec --` (le hook l'utilise) ou un shell où mise est activé. `--redact` masque la valeur du secret dans la sortie : on ne la voit jamais dans le terminal ni dans les journaux.

## Fonctionnement du hook

1. Il se place à la racine du dépôt (`git rev-parse --show-toplevel`).
2. Il cherche `mise` dans le `PATH`, sinon dans `~/.local/bin/mise`.
3. Il vérifie que `mise exec -- gitleaks version` répond.
4. Il lance `mise exec -- just pre-commit` (le code de retour est celui de la recette).

### Fermé par défaut

Si `mise` est introuvable, ou si gitleaks n'est pas disponible via mise, **le commit est refusé** avec un message qui dit quoi faire (`just setup`, `mise trust`). Un hook qui se désactiverait en silence donnerait une fausse impression de protection. Les messages commencent par `pre-commit:` et rappellent le contournement d'urgence.

Le chemin du dépôt peut contenir des espaces : tous les chemins sont entre guillemets, et la vérification automatique utilise un dépôt dont le chemin contient un espace. Un chemin contenant « : » n'est pas testé (voir « Limites connues »).

## Installation

```
just setup          # mise install, puis just hooks-install
# ou seulement :
just hooks-install  # git config core.hooksPath .githooks
```

`core.hooksPath` est une configuration **locale** du clone : elle n'est pas versionnée. Un clone neuf n'a pas de hook tant que `just hooks-install` n'a pas été lancée. La CI, elle, relance `secrets-scan` sans dépendre du poste du développeur (job `ci-cpu`, étape E9 : mise installe gitleaks, historique complet avec `fetch-depth: 0`).

## Contourner le hook : `git commit --no-verify`

`--no-verify` désactive le hook : le commit part sans aucune vérification. **Réservé à l'utilisateur, en cas d'urgence réelle** : le message de refus du hook ne le suggère plus, et le garde-fou Bash des agents refuse `--no-verify` et `-n` ([`garde-fous-bash.md`](garde-fous-bash.md)). Conséquences :

- un secret engagé ainsi **est dans l'historique** ; le détecter ne l'en retire pas. Lancer `just secrets-scan` tout de suite, et si un vrai secret est trouvé : le **révoquer** (le considérer comme compromis), puis réécrire l'historique local **avant** tout `push` ;
- une fois poussé sur un dépôt public, un secret reste visible (références de PR, caches) même après suppression : seule la révocation compte ;
- la vérification automatique `just verify-pp secrets` montre ce scénario : un commit `--no-verify` passe, puis `secrets-scan` le détecte.

## Faux positifs et `.gitleaksignore`

Premier passage sur l'historique, le 2026-11-07 (16 commits, avant l'activation du hook) : `gitleaks git --redact` (version 8.30.1) ne trouve **aucun** secret, et `gitleaks dir . --redact` non plus sur l'arbre de travail. Le `export GITHUB_TOKEN=...` de [`ci-cd.md`](ci-cd.md) n'est pas signalé : la valeur `...` n'a pas la forme d'un jeton. Il n'y a donc **pas de `.gitleaksignore`**.

Règles si un faux positif apparaît (risque R13) :

- jamais d'exception par dossier ou par motif large dans `.gitleaks.toml` ;
- ajouter l'**empreinte** précise du résultat (ligne `commit:fichier:règle:ligne` affichée par gitleaks dans le champ `Fingerprint`) dans `.gitleaksignore`, avec un commentaire (`#`) qui dit pourquoi c'est faux ;
- s'il s'agit d'un vrai secret : le signaler, le révoquer, ne jamais l'ignorer.

## Vérification automatique : `just verify-pp secrets` (C1)

`tools/verify_pp.sh secrets` travaille dans un dépôt temporaire (`mktemp -d`, nom contenant un espace) qui contient une copie de `.githooks/`, `.gitleaks.toml`, `justfile`, `mise.toml` et `tools/`, avec `MISE_TRUSTED_CONFIG_PATHS` qui pointe dessus et `core.hooksPath` activé. La configuration Git globale et système est neutralisée pour la durée du test. Le faux jeton est **généré à l'exécution** (préfixe `ghp_` suivi de 36 caractères alphanumériques aléatoires) ; il n'est écrit que dans le dépôt temporaire, jamais affiché, jamais dans le dépôt réel. Un `trap EXIT` supprime tout.

Contrôles, dans l'ordre :

1. commit de base accepté par le hook ;
2. `secrets-scan` réussit sur un historique propre ;
3. le commit qui contient le jeton est bloqué par gitleaks (`leaks found`), aucun commit n'est créé, et le jeton n'apparaît pas dans la sortie ;
4. un commit témoin (sans secret) est accepté ;
5. un lien cassé (`docs/broken.md`) bloque le commit, et la sortie nomme le lien ;
6. fermé par défaut : avec un `HOME` vide et `PATH=/usr/bin:/bin`, le commit est refusé (`mise not found`) ; sauté avec un message si `mise` est installé dans ces dossiers (la sortie finale est alors `OK C1 (partial: closed-by-default check skipped)`) ;
7. `git commit --no-verify` laisse passer le jeton, puis `secrets-scan` le détecte (code non nul, jeton absent de la sortie).

Sortie finale : `OK C1` (ou `OK C1 (partial: ...)` si le contrôle 6 est sauté) et code 0, sinon `FAILED C1` et code 1. Le chemin du dépôt temporaire ne doit pas contenir « : » (`MISE_TRUSTED_CONFIG_PATHS` est une liste séparée par « : ») : sinon la commande échoue avec un message qui demande de régler `TMPDIR`.

## Tests unitaires

`tools/tests/test_git_hooks.py` (lancé par `just tools-test`). Hermétique : le vrai `mise` est remplacé par un script factice qui journalise ses arguments. Vérifie : hook exécutable, shebang, syntaxe (`bash -n`), mode `100755` dans l'index Git (sauté tant que le hook n'est pas suivi), `.gitleaks.toml` (extension des règles par défaut, aucune liste blanche), recettes du `justfile` ; et, dans un dépôt jetable dont le chemin contient un espace : commit refusé sans mise, refusé si gitleaks est indisponible, accepté avec les appels `exec -- gitleaks version` puis `exec -- just pre-commit`, repli sur `~/.local/bin/mise`, refus quand seul `just pre-commit` échoue (le journal du faux mise contient bien cet appel), message de refus sans `--no-verify`, contournement par `--no-verify`.

## Limites connues

- Le hook ne couvre que les commits faits avec ce clone : `--no-verify`, un autre clone sans `just hooks-install` ou une modification faite depuis l'interface web y échappent. La CI (`secrets-scan` dans `ci-cpu`) est le filet de sécurité.
- gitleaks détecte des motifs connus (règles par défaut) : un secret sans forme reconnaissable (mot de passe libre) n'est pas vu.
- gitleaks est « feature complete » : ses mainteneurs ne publient plus que des correctifs de sécurité. Un successeur, betterleaks, existe (voir [`../recherches/2026-11-05-outillage-pp.md`](../recherches/2026-11-05-outillage-pp.md) §4 et la décision 0008). La décision n'est pas rouverte ; à réévaluer si gitleaks cesse d'être maintenu.
- Les chemins contenant « : » ne sont pas testés : le hook ne dépend pas de `MISE_TRUSTED_CONFIG_PATHS`, mais `just verify-pp secrets` oui (liste séparée par « : »), d'où la garde ci-dessus. Un essai empirique avec mise 2026.11.0 n'a pas été concluant (le dossier était déjà considéré comme sûr).
- `mise exec` coûte un lancement de mise à chaque commit.
- Le hook ne vérifie pas le formatage (c'est `just fmt-check`, dans `lint`).
- `just hooks-install` n'a pas été lancée sur le dépôt réel par l'implémentation de E7 : c'est une action locale de l'utilisateur.
