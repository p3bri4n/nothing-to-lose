# Hook PostToolUse : formatage automatique à l'édition

*Mise à jour : 2026-11-07 (résultats de l'essai de bout en bout de C2 ; création, étape E6 du plan PP, voir [`../plans/PP.md`](../plans/PP.md) §E6 et le risque R8 ; durcissement après la revue d'architecte : garde de la configuration, groupe de processus, configuration prettier imposée)*

## Rôle

Après chaque `Write`, `Edit` ou `MultiEdit` de Claude Code, le hook formate le fichier touché avec `tools/fmt.py --write`, pour que le dépôt reste conforme à `just fmt-check` sans effort. Il ne bloque jamais la session. Le hook de démarrage est décrit dans [`hook-session-start.md`](hook-session-start.md) ; la correspondance extension → formateur est dans [`outillage.md`](outillage.md).

## Fichiers et configuration

| Élément | Où | Détail |
|---|---|---|
| Script | `tools/hooks/format_on_edit.py` | Python standard. Charge `tools/fmt.py` par son chemin (`importlib.util.spec_from_file_location`, sans toucher à `sys.path`) pour la correspondance extension → formateur et l'exclusion des fixtures (source unique). |
| Configuration | `.claude/settings.json`, section `hooks.PostToolUse` | Matcher `Write\|Edit\|MultiEdit`, `timeout` de 30 s, synchrone (pas d'`async`). |
| Commande | `python3 "$CLAUDE_PROJECT_DIR/tools/hooks/format_on_edit.py" \|\| true` | Guillemets obligatoires : le chemin du dépôt peut contenir des espaces et un « : ». Le `\|\| true` garantit que le shell ne renvoie jamais un code d'erreur, même si Python lui-même ne démarre pas. |
| Tests | `tools/tests/test_format_on_edit.py` | `subprocess.run` et `subprocess.Popen` mockés ; quelques tests utilisent le vrai `git` (dépôt jetable) et un vrai processus enfant (arrêt du groupe de processus). |
| Vérification | `just verify-pp format` | Partie automatique du critère C2. |

## Comportement

Le hook lit sur stdin le JSON de l'événement et prend `tool_input.file_path`. Le fichier est **formaté** (appel de `python3 tools/fmt.py --write <chemin absolu>` depuis la racine du projet, liste d'arguments sans shell) sauf dans les cas suivants, où il ne fait rien, sans message (sauf mention contraire) :

| Cas ignoré | Détail |
|---|---|
| Variable `NTL_FORMAT_HOOK=off` | Insensible à la casse ; toute autre valeur laisse le hook actif. |
| Pas de `file_path` exploitable | JSON invalide, champ absent, vide, non textuel ou contenant un octet nul. |
| Hors du projet | Le chemin est résolu (liens symboliques et `..`) puis doit être sous `$CLAUDE_PROJECT_DIR` (lui-même résolu ; à défaut, le dépôt qui contient le script). Un chemin relatif est pris par rapport à la racine du projet. |
| Fichier inexistant ou qui n'est pas un fichier | |
| `.git` | Tout chemin dont un composant est `.git`, à n'importe quelle profondeur (constante `NEVER_TOUCH`). `.github` n'est pas concerné. |
| Dossier généré | `target/`, `node_modules/` et `.cache/` à n'importe quelle profondeur ; `runs/` et `shots/` à la racine seulement. |
| Fixtures de formatage | `tools/tests/fixtures/format/` (mal formatées volontairement). |
| Extension sans formateur | Dont le Markdown ([0012](../decisions/0012-markdown-hors-formatage.md)). |
| Ignoré par Git | `git check-ignore -q -- <chemin relatif>` (entrée standard fermée), délai de 3 s. Si Git ne peut pas répondre (code autre que 0 ou 1), le fichier est **ignoré et une ligne est écrite dans le journal**. |
| Configuration différente de `HEAD` | Voir « Sécurité » : **ligne écrite dans le journal** (`formatting refused, …`). |

Le hook n'écrit **rien sur stdout** (ni sur stderr) et sort **toujours avec le code 0**, y compris sur JSON invalide ou exception interne.

La logique de décision (`skip_reason`, `extract_file_path`, `is_disabled`) est pure ; l'exécution (résolution des chemins, Git, garde, formateur, journal) est séparée dans `resolve_in_project`, `is_git_ignored`, `config_guard_problem`, `format_file` et `log_line`. `run(stdin_text, env)` est le point d'entrée testable ; `main()` lit stdin.

### Délais

| Constante | Valeur | Rôle |
|---|---|---|
| `FORMAT_TIMEOUT_SECONDS` | 20 s | Durée maximale du formateur. |
| `GIT_TIMEOUT_SECONDS` | 3 s | Chaque appel à Git (`check-ignore`, puis `status` de la garde). |
| `REAP_TIMEOUT_SECONDS` | 2 s | Attente de la fin d'un formateur tué. |
| `SLOW_FORMAT_SECONDS` | 5 s | Au-delà, le formatage est consigné dans le journal. |

Pire cas : 3 + 3 + 20 + 2 = 28 s, sous les 30 s du `timeout` de `.claude/settings.json`. Un test (`SettingsTest`) lit ce `timeout` et vérifie `FORMAT_TIMEOUT_SECONDS + GIT_TIMEOUT_SECONDS + 3 <= timeout` ainsi que le cumul ci-dessus. Le formateur est lancé par `Popen(..., start_new_session=True)` : il est chef de son propre groupe de processus. Au dépassement du délai, le hook envoie `SIGKILL` à tout le groupe (`os.killpg`) — donc aussi à `mise`, à l'outil et à leurs petits-enfants —, attend la fin du processus, puis journalise `formatter timed out … process group killed`. Un test réel (`ProcessGroupKillTest`) vérifie qu'un petit-enfant `sleep` ne survit pas.

## Sécurité

Un formateur lancé par le hook exécute des outils dont la configuration peut contenir du code. Sans précaution, une modification de configuration faite par Claude (ou par un fichier récupéré ailleurs) serait exécutée au prochain formatage, sans que personne ne la relise.

**Configuration prettier imposée.** `tools/fmt.py` lance toujours prettier avec `--config <racine>/.prettierrc.json`. Avec cette option, prettier ne cherche plus de configuration en remontant l'arborescence : un `prettier.config.js` (que prettier exécute) posé dans le dossier d'un `.js` formaté n'est pas chargé. Vérifié le 2026-11-07 avec prettier 3.9.10 (`PrettierConfigIsolationTest`) : un `prettier.config.js` piégé qui écrit un fichier témoin **s'exécute** sans `--config` (contrôle) et **ne s'exécute pas** avec la commande de `fmt.py` (en écriture et en vérification). `.editorconfig` reste lu (il ne contient pas de code exécutable).

**Pas d'installation automatique.** Le formateur est lancé avec `MISE_EXEC_AUTO_INSTALL=false` : si `mise.toml` épingle une version absente, `mise exec` ne la télécharge pas pendant l'édition. Vérifié le 2026-11-07 avec mise 2026.11.0 (dossier temporaire, `mise.toml` propre à ce dossier épinglant `aqua:mvdan/sh = "0.0.1"`, version inexistante) : par défaut, mise tente l'installation (2,3 s, échec 404) ; avec `MISE_EXEC_AUTO_INSTALL=false` (comme avec `MISE_AUTO_INSTALL=false`), il affiche « is not installed and auto-install is disabled, so mise looks for shfmt on PATH instead » et n'installe rien. La note [`../recherches/2026-11-07-securite-hook-formatage.md`](../recherches/2026-11-07-securite-hook-formatage.md) donnait ce nom de variable en confiance moyenne ; l'essai la confirme pour cette version de mise. **Effet de bord observé** : en l'absence de la version épinglée, mise cherche l'outil dans le `PATH`, ce qui est un repli plutôt qu'une erreur.

**Garde de la configuration par rapport à `HEAD`.** Avant de formater, le hook compare à `HEAD` les fichiers `GUARDED_CONFIG_FILES` : `mise.toml`, `mise.local.toml`, `.prettierrc.json` et `rust-toolchain.toml`. Si l'un d'eux est modifié (dans l'index ou le disque), supprimé, non suivi, ou ignoré par Git mais présent (cas de `mise.local.toml`), **le hook ne formate rien**, écrit `formatting refused, configuration differs from HEAD (<fichiers>)` dans le journal et sort avec le code 0. Un fichier absent à la fois de `HEAD` et du disque est normal (typiquement `mise.local.toml`). Si Git ne peut pas répondre (pas de `HEAD`, délai dépassé), le hook refuse aussi : dans le doute, rien ne s'exécute. Le test se fait par un seul `git --no-optional-locks status --porcelain=v1 -z --ignored=matching --untracked-files=all -- <fichiers>` : une sortie non vide veut dire « différent ». Conséquence voulue : tant qu'une modification de ces fichiers n'est pas commitée (donc relue), plus aucun formatage automatique, y compris pour le fichier de configuration lui-même. Le plus simple pour reprendre est de valider ou d'annuler la modification.

**Risque résiduel et sa limite.**

- Le contenu de `HEAD` est de confiance : une configuration piégée **déjà commitée** sera exécutée. La garde ne protège que contre les changements non relus, pas contre une relecture manquée.
- Les autres fichiers que mise lit ne sont pas gardés : `.mise.toml`, `mise/config.toml`, `.config/mise.toml`, `.config/mise/config.toml`, `mise.<environnement>.toml`, `.tool-versions`, ainsi que tout fichier de mise situé dans un dossier parent de la racine du projet ou dans la configuration globale de l'utilisateur. Seuls les noms demandés sont gardés (décision de l'utilisateur) ; élargir la liste est un changement d'une ligne dans `GUARDED_CONFIG_FILES` (et dans `guarded_config_files` de `tools/verify_pp.sh`).
- La garde et le formatage ne sont pas atomiques : un processus extérieur qui modifie la configuration entre les deux n'est pas vu.
- Seul le hook est gardé. `just fmt` et `just fmt-check`, lancés explicitement, formatent avec la configuration présente sur le disque.
- Les fichiers de configuration non exécutables (`ruff.toml`, `taplo.toml`, `rustfmt.toml`, `.editorconfig`, `.prettierignore`) ne sont pas gardés : ils changent le style, pas ce qui s'exécute. Prettier ne charge de greffons que si `.prettierrc.json` les déclare (gardé).
- Le hook n'a pas été vérifié sous Windows (`os.killpg`, `python3`, `$CLAUDE_PROJECT_DIR`).

**Worktrees hors de la racine.** Un fichier en dehors de `$CLAUDE_PROJECT_DIR` n'est jamais formaté. Un worktree Git créé hors du dossier du dépôt (par exemple par un sous-agent isolé) n'est donc pas formaté par ce hook ; `just fmt` reste disponible.

**`mise` doit être dans le `PATH` de Claude Code.** Le formateur est lancé avec l'environnement de Claude Code (plus `MISE_EXEC_AUTO_INSTALL=false`). Si Claude Code est lancé depuis un environnement où `mise` n'est pas dans le `PATH` (lanceur graphique, IDE), `tools/fmt.py` ne le trouve pas : une ligne est écrite dans le journal et rien n'est formaté.

**Sous-agents.** D'après la documentation de Claude Code, les hooks de `.claude/settings.json` s'appliquent aussi aux appels d'outils des sous-agents ; le hook formate donc leurs écritures dans la racine du projet.

## Journal des erreurs

Fichier `.cache/hooks/format.log` à la racine du projet (dossier créé au besoin ; `.cache/` est ignoré par Git). Une ligne par incident, au format :

```
2026-11-07T16:27:18+01:00 tools/a.py: formatter failed (exit 1) error: ruff failed
```

Incidents consignés : formateur en échec (code de sortie et fin de sa sortie, 300 caractères au plus, sur une seule ligne), formateur introuvable ou non exécutable, délai dépassé (groupe de processus tué), formatage lent (plus de 5 s), `git check-ignore` en échec, **formatage refusé par la garde de la configuration**, JSON invalide ou exception inattendue (`hook error: …`, dont l'échec du chargement de `tools/fmt.py`). Si le journal lui-même ne peut pas être écrit, l'erreur est ignorée.

**Journal borné** : quand `format.log` dépasse environ 1 Mo (`LOG_MAX_BYTES`), il est renommé en `format.log.1` (l'éventuel `format.log.1` précédent est remplacé) et un nouveau fichier est commencé. Au plus deux fichiers, donc environ 2 Mo. Ils peuvent être supprimés à la main.

## Désactivation

`NTL_FORMAT_HOOK=off` dans l'environnement de Claude Code (par exemple `NTL_FORMAT_HOOK=off claude`, ou dans `.claude/settings.local.json`, section `env`). Le hook sort alors immédiatement.

## Test de bout en bout (manuel, critère C2 et risque R8)

À faire dans une session locale de Claude Code, avec une configuration propre (`just verify-pp format` n'affiche pas `SKIP`). Le fichier de sonde doit être **hors des dossiers ignorés** : `.cache/` est ignoré par Git et par le hook, donc le `.cache/verify-pp/e2e.py` cité par le plan ne convient pas. On utilise `e2e_format_probe.py` **à la racine du dépôt** (non ignoré, extension `.py`).

1. Demander à Claude d'écrire (outil `Write`) `e2e_format_probe.py` avec un contenu mal formaté, par exemple `x  =  [1,2,3]` sur une ligne, sans saut de ligne final.
2. Relire le fichier : il doit être reformaté (`x = [1, 2, 3]` et une fin de ligne), ce qui prouve que le matcher a déclenché le hook pour `Write`.
3. Demander une modification par l'outil `Edit` de ce fichier déjà reformaté par le hook (risque R8 : Claude Code doit accepter l'édition d'un fichier modifié sous ses pieds), puis vérifier que le résultat est formaté aussi.
4. Si le hook ne s'est pas déclenché : consulter `.cache/hooks/format.log` (refus de la garde, `mise` introuvable…).
5. Supprimer `e2e_format_probe.py`.

**Matcher.** `Write|Edit|MultiEdit` est lu par Claude Code comme une liste exacte de trois noms d'outils. La documentation consultée ne cite pas d'outil `MultiEdit` : si l'outil n'existe plus, ce nom est inoffensif. L'essai a confirmé `Write` et `Edit`, les seuls utiles.

### Résultats de l'essai de bout en bout (2026-11-07, session principale)

Essai fait en local, dans la session principale de Claude Code, avec le fichier de sonde `e2e_format_probe.py` :

- **`Write`** : le fichier écrit mal formaté a été reformaté par le hook (matcher confirmé pour `Write`).
- **`Edit` suivant, sans relecture** : une modification par `Edit` du fichier déjà reformaté par le hook, **sans le relire** entre-temps, a été **acceptée** par Claude Code. Le risque **R8** (refus d'éditer un fichier modifié sous les pieds de l'outil) **n'a pas été observé**.
- **Sous-agent `executant`** : le hook s'est déclenché aussi pour un fichier écrit par un sous-agent `executant`.
- **Journal** : aucun message d'erreur dans `.cache/hooks/format.log`.
- **`MultiEdit`** : **non testé** (l'outil n'est pas cité par la documentation consultée).
- **Prise en compte de la configuration** : le hook était actif **sans redémarrage de la session** après l'ajout de la section `hooks` à `.claude/settings.json`.

## Limites connues

- **Test de bout en bout** : fait le 2026-11-07 (voir ci-dessus) ; `MultiEdit` reste non testé, et R8 n'a été observé ni pour `Write` ni pour `Edit`.
- Le formatage passe par `mise exec --` (voir `tools/fmt.py`) : chaque édition coûte un lancement de mise, et un `mise` absent du `PATH` de Claude Code produit une ligne de journal au lieu d'un formatage.
- Un formateur qui échoue sur une erreur de syntaxe laisse le fichier tel quel et journalise l'échec ; Claude n'en est pas informé.
- Un seul fichier est traité par appel : les modifications faites par d'autres outils (`Bash`, `sed`) ne déclenchent pas le hook.
- Le hook est synchrone : jusqu'à 28 s d'attente au pire cas pour Claude Code (en pratique, quelques centaines de millisecondes).
- Sous Windows, `$CLAUDE_PROJECT_DIR`, `python3` et `os.killpg` n'ont pas été vérifiés.
