# Garde-fous Bash des agents : hook `PreToolUse` et règles `deny`

*Mise à jour : 2026-11-07 (création, étape E10 du plan PP, voir [`../plans/PP.md`](../plans/PP.md) §E10, la décision D8 ([0013](../decisions/0013-identite-agents-fusion.md)) et les risques R6 et R7 ; corrections de la revue d'architecte d'E10 ; panne du garde-fou : décision [0022](../decisions/0022-panne-garde-bash.md), périmètre : [0023](../decisions/0023-perimetre-garde-bash.md))*

Décrit le code **tel qu'il existe**. Le hook `tools/hooks/guard_bash.py` refuse les commandes Bash qui contourneraient le circuit Git du projet : hooks Git désactivés, push forcé ou vers `main`, fusion d'une pull request par un agent, modification de la configuration du dépôt GitHub. Les autres hooks de Claude Code sont décrits dans [`hook-format-on-edit.md`](hook-format-on-edit.md) et [`hook-session-start.md`](hook-session-start.md) ; les hooks Git dans [`hooks-git.md`](hooks-git.md).

**Ce n'est pas une barrière étanche.** C'est une analyse textuelle de la ligne de commande : elle arrête les erreurs et les raccourcis courants, pas un agent qui chercherait activement à la contourner (voir « Limites connues »). La vraie défense est ailleurs (voir « Défense en profondeur »).

## Fichiers

| Élément | Où | Détail |
|---|---|---|
| Hook | `tools/hooks/guard_bash.py` | Python standard, sans dépendance. Lit le JSON `PreToolUse` sur stdin. |
| Configuration | `.claude/settings.json`, `hooks.PreToolUse` | Matcher `Bash`, commande `python3 "$CLAUDE_PROJECT_DIR/tools/hooks/guard_bash.py"`, `timeout` de 10 s, synchrone (le budget des lectures `git` du hook est de 6 s, voir plus bas). **Pas de `\|\| true`** : le code de sortie 2 doit parvenir à Claude Code. |
| Règles `deny` | `.claude/settings.json`, `permissions.deny` | En plus de celles d'origine (Terraform, `just tf-apply`, lecture des `*.tfvars` et `*.tfstate`) : `Bash(git commit --no-verify:*)`, `Bash(git commit -n:*)`, `Bash(git push --force:*)`, `Bash(git push -f:*)`, `Bash(gh pr merge:*)`, `Bash(gh repo delete:*)`, puis, pour le push vers `main` et `master`, des formes exactes (`Bash(git push origin main)`, `Bash(git push -u origin main)`, `Bash(git push origin HEAD:main)`, et les mêmes pour `master`) et des formes larges (`Bash(git push * main)`, `Bash(git push * HEAD:main)`, `Bash(git push * refs/heads/main)`, `Bash(git push * *:main)`, `Bash(git push * *:refs/heads/main)`, et les mêmes pour `master`). **Ce ne sont pas une frontière de sécurité** : de simples motifs de texte, ils ne voient ni `git -C . push origin main`, ni `git -c x=y push origin main`, ni `git 'push' origin main` (limite documentée par Claude Code, voir [la note de recherche](../recherches/2026-11-07-garde-fous-git-gh.md) §2) ; le hook est la protection principale. `Bash(git push *)` n'est volontairement **pas** utilisé : il interdirait aussi le push légitime de la branche de travail. Le comportement exact des motifs avec `*` au milieu (`git push * main`) vient de la documentation et n'a pas été essayé dans Claude Code. |
| Journal | `.cache/hooks/guard.log` | Même convention que `format.log` (voir plus bas). Le hook `SessionStart` en compte les lignes `hook error` ([`hook-session-start.md`](hook-session-start.md)). |
| Tests | `tools/tests/test_guard_bash.py` | Hermétiques (voir « Vérification »). |

## Contrat du hook

| Situation | Code de sortie | stdout | stderr | Journal |
|---|---|---|---|---|
| Commande autorisée | 0 | vide | vide | rien |
| Commande interdite | **2** | vide | explication en français : règle, raison, commande analysée (300 caractères au plus), renvoi vers cette page | `BLOCKED rule=… command=…` |
| **Panne** (JSON invalide ou entrée vide, `tool_input.command` absent ou non textuel, exception interne y compris `RecursionError`) et le texte brut de l'entrée contient `git` ou `gh` comme mot | **2** | vide | « garde-fou en erreur, commande git/gh refusée par prudence, prévenez l'utilisateur », la cause, renvoi vers cette page et le journal | `hook error: … command refused (git/gh)` |
| **Panne** et le texte brut ne contient ni `git` ni `gh` comme mot | 0 | vide | vide | `hook error: … command allowed` |
| Commande vide ou blanche | 0 | vide | vide | rien |
| Impossible de lire stdin | 0 | vide | vide | `hook error: cannot read stdin …` |
| Branche courante ou cible de push illisible lors d'un `git push` sans cible explicite | **2** (règle `push-unknown-branch`) | vide | explication en français | `current branch unknown …` ou `push target unknown …`, puis `BLOCKED rule=push-unknown-branch …` |

### Décision U2 (0022) : en cas de panne, refus pour `git` et `gh`, passage pour le reste, événement visible

Décision de l'utilisateur du 2026-11-07, fiche [0022](../decisions/0022-panne-garde-bash.md). Si le garde-fou lui-même échoue (JSON invalide, commande absente, exception), il regarde le **texte brut de l'entrée** :

- il contient `git` ou `gh` comme mot (expression `\b(git|gh)\b`, donc aussi `.git` ou `git-dir`, pas `github` ni `digit`) : la commande est **refusée** (code 2) avec le message « garde-fou en erreur, commande git/gh refusée par prudence, prévenez l'utilisateur » ;
- sinon : la commande passe (code 0).

Dans les deux cas une ligne `hook error: …` est écrite dans `guard.log`. Raison du choix : le circuit Git reste protégé pendant la panne, le reste du travail continue (un refus total bloquerait tous les agents sur un défaut du hook). Contrepartie : une commande `git` légitime peut être refusée tant que le hook est en panne ; il faut alors **prévenir l'utilisateur**, qui lit le journal. Pour que la panne ne passe pas inaperçue, le hook `SessionStart` affiche à l'ouverture de session le nombre de lignes `hook error` de `.cache/hooks/guard.log` quand il est supérieur à 0 ([`hook-session-start.md`](hook-session-start.md)) ; il ne lit pas `guard.log.1`. Une ligne de ce genre ressemble à :

```
2026-11-07T20:52:10+01:00 hook error: RuntimeError('boom'), command refused (git/gh)
```

Ce que cette règle **ne couvre pas** : un script `guard_bash.py` qui ne démarre pas du tout (erreur de syntaxe, `python3` absent) sort avec un code différent de 2, que Claude Code traite comme une erreur non bloquante ; c'est ce qui fait de `just tools-test` et de `just lint` des contrôles indispensables après toute modification du script.

Le journal est borné comme `format.log` : au-delà d'environ 1 Mo (`LOG_MAX_BYTES`), il est renommé en `guard.log.1` (l'éventuel précédent est remplacé). Les lignes sont sur une seule ligne, datées avec le fuseau horaire. Si le journal lui-même ne peut pas être écrit, l'erreur est ignorée.

Il **n'existe volontairement aucune variable d'environnement** qui désactive le garde-fou (contrairement à `NTL_FORMAT_HOOK=off` pour le formatage) : l'utilisateur peut retirer le hook de `.claude/settings.json`, un agent ne doit pas pouvoir l'éteindre.

### Règle générale : une forme inconnue sur une commande sensible est refusée

Quand le hook ne peut pas savoir ce que fera une commande sensible, il refuse au lieu de deviner (cohérent avec la décision U2). Concrètement :

- imbrication de plus de 12 niveaux (`$(…)`, `bash -c`, `eval`) : règle `too-complex` ;
- `git push` sans cible explicite (ou avec une cible calculée, `git push origin "$BRANCH"`) alors que la branche courante, ou la cible que Git lui donne, ne peut pas être lue (pas de dépôt, délai dépassé, lecture en échec, changement de branche calculé sur la même ligne) : règle `push-unknown-branch` ;
- `gh api` dont la requête GraphQL est lue dans un fichier (`-F query=@f`, `--input`) ou calculée, ou écriture vers un endpoint calculé : règle `gh-api-opaque` (« mettez la requête en ligne ») ;
- une commande `git` ou `gh` quand le hook lui-même est en panne (ci-dessus).

Autorisé quand même : une commande sensible dans une forme qui ne peut pas atteindre un point sensible (`git push origin feature`, `gh api` en `GET`).

## Règles

### `git commit` : `no-verify`

Refusé : `--no-verify` (et ses abréviations acceptées par Git, à partir de `--no-v`), `-n`, et tout groupe de drapeaux courts contenant `n` (`-an`, `-nm "x"`, `-sn`).

Le hook lit les options comme Git le fait : une option qui prend une valeur (`-m`, `-F`, `-C`, `-c`, `-t`, `--message`, `--file`, `--author`, `--fixup`…) consomme le mot suivant ou le reste du groupe, et `--` termine les options. D'où les **faux positifs écartés** :

| Commande | Verdict | Pourquoi |
|---|---|---|
| `git commit -m "fix -n option"` | autorisée | `-n` est dans la valeur de `-m` |
| `git commit -mn`, `git commit --message -n` | autorisées | « n » est le message |
| `git commit -m x -- -n` | autorisée | après `--`, des chemins |
| `git commit --amend`, `--amend --no-edit`, `-S`, `-SKEYID`, `--signoff`, `-s`, `--no-gpg-sign`, `--gpg-sign` | autorisées | aucun ne désactive un hook |
| `git commit -m "$(cat <<'EOF' … git commit --no-verify … EOF)"` | autorisée | le corps d'un heredoc est du texte |

`--no-verify` est aussi refusé pour `git push`, `git merge` et `git rebase` (ils désactivent leur hook respectif). `-n` n'y est **pas** examiné : il signifie `--dry-run` pour `push` et `--no-stat` pour `merge` et `rebase`.

`git rebase -x CMD` / `--exec CMD` / `--exec=CMD` (aussi dans un groupe, `-ix CMD`, et en abréviation `--ex`) : la valeur est un script shell, elle est **analysée comme une commande** (`git rebase -x 'git push --force' main` est refusé, `git rebase -x 'make test' main` est autorisé). Les autres commandes Git qui exécutent un texte (`git submodule foreach`, `git bisect run`, `git filter-branch`, `git difftool`, `git mergetool`) ne sont **pas** suivies (voir « Limites connues »).

### `git push` : `push-force`, `push-mirror`, `push-delete`, `push-all`, `push-main`

| Règle | Refusé |
|---|---|
| `push-force` | `--force`, `-f` (aussi dans un groupe : `-fu`, `-uf`), toute option commençant par `--force` (`--force-with-lease`, `--force-with-lease=…`, `--force-if-includes`) ou abréviation (`--forc`), refspec commençant par `+` |
| `push-mirror` | `--mirror` |
| `push-delete` | `--delete`, `-d`, `--prune`, refspec `:branche` |
| `push-all` | `--all` et son synonyme `--branches` (depuis Git 2.41), abréviations comprises (`--al`, `--b`) : elles poussent aussi `main` |
| `push-main` | cible `main` ou `master`, écrite avec ou sans `refs/heads/` ou `heads/` : `git push origin main`, `HEAD:main`, `HEAD:refs/heads/main`, `HEAD:heads/main`, `refs/heads/main`, `heads/main`, `feature:main`, refspec avec `*` (générique, peut atteindre `main`), **et** les pushs dont la cible est la branche courante quand elle est `main` ou `master` : `git push`, `git push origin`, `git push -u origin HEAD`, `git push origin HEAD`, **et** un `git push` sans refspec dont la cible configurée est `main` ou `master` (voir ci-dessous) |
| `push-unknown-branch` | `git push` sans cible explicite (sans refspec, `HEAD`, `@`, ou cible calculée) alors que la branche courante ou la cible configurée est **inconnue** |

Pour les pushs sans cible explicite, le hook lit `git branch --show-current` dans le dossier de travail de la commande (`cwd` du JSON du hook, à défaut le dossier du projet), en suivant les options `git -C dir` placées avant la sous-commande. Un seul appel par liste de dossiers distincte. Pour un push **sans refspec**, il lit en plus `git for-each-ref --format=%(push) refs/heads/<branche>` : la référence de suivi que Git mettra à jour (selon `push.default`, la branche amont et `remote.pushDefault`) ; si c'est `refs/remotes/<dépôt>/main` ou `master` (par exemple une branche dont l'amont est `origin/main` avec `push.default = upstream`), le push est refusé. (La variante `%(push:remoteref)` n'a rien affiché dans tous les essais faits avec Git 2.53.0 ; elle n'est donc pas utilisée.)

**Budget de temps (M8)** : chaque lecture `git` est limitée à 3 s (`GIT_TIMEOUT_SECONDS`) et **toutes les lectures d'une exécution ensemble à 6 s** (`GIT_BUDGET_SECONDS`, le `timeout` du hook est de 10 s). Passé ce budget, plus aucune lecture n'est lancée : la réponse est « inconnu ».

**Fermé par défaut** : si la branche courante ou la cible configurée est inconnue (pas de dépôt, lecture en échec ou trop longue, budget dépensé), un push sans cible explicite est **refusé** (`push-unknown-branch`) ; `git push -u origin <nom-de-la-branche>` reste autorisé. Seule une tête détachée (`git branch --show-current` affiche une ligne vide sans erreur) n'est pas « inconnue » : Git refuse de lui-même ce push. Une **cible calculée** (`git push origin "$BRANCH"`, `git push origin $(…)`, `HEAD:$X`) est jugée comme `HEAD` : refusée si la branche courante est `main`, `master` ou inconnue, autorisée sinon. De même, un `git switch`/`git checkout` vers une branche calculée (`git switch $B && git push`) rend la branche inconnue pour la suite de la ligne.

Si la même ligne de commande change de branche avant le push (`git switch main && git push origin HEAD`, `git switch -c travail && git push -u origin HEAD`), le hook raisonne sur la branche annoncée par la ligne, pas sur celle du disque au moment de l'analyse.

Autorisés, entre autres : `git push -u origin HEAD` depuis une branche autre que `main`, `git push origin e10-circuit-git-agents`, `git push origin HEAD:feature`, `git push --tags`, `git push --dry-run`, `git push -n origin HEAD` (`-n` y est `--dry-run`). Choix assumé : `git push origin main:autre` (branche locale `main` poussée vers une autre branche distante) n'est pas refusé, la cible n'étant pas `main`.

### Options globales de `git` placées avant la sous-commande

`git -c k=v …`, `git -C dir …`, `--git-dir`, `--work-tree`, `--namespace`, `--super-prefix`, `--attr-source`, `--config-env` et les drapeaux comme `--no-pager` sont **ignorés pour trouver la sous-commande** : `git -c x=y commit --no-verify` est refusé.

### Clés de configuration Git interdites : `hooks-path` et `git-config`

Une seule fonction (`_forbidden_config_key`) décide quelles clés un agent ne peut pas définir ; elle est utilisée par `git -c`, `--config-env` (les deux écritures), les affectations `GIT_CONFIG_*` (`GIT_CONFIG_KEY_n`, `GIT_CONFIG_PARAMETERS`, après `env`, devant une commande ou dans `export`) et les écritures de `git config`. Clés interdites (insensible à la casse) :

| Clé | Règle | Pourquoi |
|---|---|---|
| `core.hooksPath` | `hooks-path` | désactive les hooks Git du dépôt |
| `alias.*` | `git-config` | masque une commande à l'analyse (`git ci` pour `git commit -n`) |
| `include.path`, `includeIf.*` | `git-config` | charge un autre fichier de configuration qui contiendrait ces clés |
| `remote.*.push`, `remote.*.mirror` | `git-config` | redirige ou élargit ce qu'un push envoie |
| `push.default` | `git-config` | change ce que pousse un `git push` sans refspec |

Les écritures de `git config` couvertes : `git config <clé> <valeur>`, `--add`, `--replace-all`, `--unset`, `--unset-all`, `--rename-section`, `--remove-section` (les noms sont des sections), les sous-commandes `set`, `unset`, `rename-section`, `remove-section`, avec toute option de portée (`--global`, `--file …`…). Seule la **clé** est examinée, pas la valeur.

**Autorisé : lire** (`git config <clé>`, `--get`, `--get-all`, `--get-regexp`, `--list`, `get`, `list`) et écrire toute autre clé (`user.name`, `remote.origin.url`…). `git commit --no-gpg-sign` n'est pas interdit. L'activation des hooks du dépôt se fait par `just hooks-install` (la recette n'est pas analysée : seul `just …` apparaît dans la commande).

**Hors d'atteinte, volontairement** : les clés qui font lancer un programme à Git (`core.editor`, `core.sshCommand`, `core.pager`, `core.fsmonitor`, `diff.external`, `credential.helper`, `gpg.program`, `sequence.editor`…). Le programme est inconnu du garde-fou, et ces clés ont des usages légitimes (`git -c core.pager=cat log`). C'est une limite documentée, pas un oubli. `git commit --no-gpg-sign` n'est pas interdit. L'activation des hooks du dépôt se fait par `just hooks-install` (la recette n'est pas analysée : seul `just …` apparaît dans la commande).

### GitHub CLI : `gh-pr-merge`, `gh-admin`, `gh-api`

| Règle | Refusé |
|---|---|
| `gh-pr-merge` | `gh pr merge`, toute variante (`--auto`, `--admin`, `--squash`, `--rebase`, `-R dépôt` ou `--repo` avant ou après `pr`). Seule l'aide est autorisée : `gh pr merge --help` ou `-h` (une valeur d'option qui ressemble à l'aide, `--body --help`, reste refusée) |
| `gh-admin` | `gh repo delete`, `edit`, `archive`, `unarchive`, `rename`, `deploy-key`, `autolink` ; `gh secret set\|delete\|remove` ; `gh variable set\|delete\|remove` ; `gh alias set\|import` (un alias contournerait le texte `pr merge`) |
| `gh-api` | voir ci-dessous |
| `gh-api-opaque` | `gh api` impossible à juger (voir ci-dessous) |

`gh api` : la méthode est lue dans `-X`, `-XPUT`, `--method`, `--method=`, sans tenir compte de la casse (`-X=DELETE` est aussi compris) ; sans méthode explicite, elle vaut `POST` si un corps est donné (`-f`, `-F`, `--field`, `--raw-field`, `--input`), sinon `GET`. L'URL peut être complète (`https://api.github.com/…`) ou commencer par `/`. Refusés (toute méthode sauf `GET` et `HEAD`, sauf mention contraire) :

| Cible | Méthodes |
|---|---|
| `repos/<o>/<r>/pulls/<n>/merge` | `PUT`, `POST`, `PATCH`, `DELETE` |
| `repos/<o>/<r>/git/refs…` | `DELETE`, `PUT`, `PATCH` (la création d'une référence par `POST` reste permise) |
| `repos/<o>/<r>/merges` (fusion d'une branche dans une autre), `repos/<o>/<r>/contents/…` (écriture ou suppression de fichiers sur une branche) | toute méthode sauf `GET` |
| `repos/<o>/<r>` (le dépôt lui-même), `repos/<o>/<r>/rulesets…`, `orgs/<o>/rulesets…` | toute méthode sauf `GET` |
| `repos/<o>/<r>/branches/<b>/protection…` et `…/rename` | toute méthode sauf `GET` |
| `repos/<o>/<r>/actions/secrets\|variables\|permissions…`, `repos/<o>/<r>/environments…` | toute méthode sauf `GET` |
| `graphql` | un champ contenant une mutation de la liste `GRAPHQL_FORBIDDEN` : `mergePullRequest`, `enablePullRequestAutoMerge`, `enqueuePullRequest`, `mergeBranch`, `createCommitOnBranch`, `deleteRef`, `updateRef`, `deleteRepository`, `archiveRepository`, `updateRepository`, `create\|update\|deleteBranchProtectionRule`, `create\|update\|deleteRepositoryRuleset` |

**Règle `gh-api-opaque`** (la requête ne peut pas être jugée, donc refus, message « mettez la requête en ligne ») :

- `gh api graphql` avec `--input`, ou avec une valeur de `-F`/`--field` qui commence par `@` après le `=` (`-F query=@q.graphql`), ou avec une valeur contenant une substitution `$(…)` ou `` `…` `` (`-f query="$(cat q.graphql)"`, même pour un autre champ : `-F owner=$(…)` est refusé aussi) ;
- une méthode autre que `GET`/`HEAD` vers un endpoint qui contient une substitution ou **commence** par `$` (`gh api -X POST "$URL"`). Un `$N` au milieu (`repos/o/r/issues/$N/comments`) n'est pas refusé.

La liste est volontairement **raisonnable, pas exhaustive** : elle couvre la fusion, les références, les rulesets, la protection de branche, les secrets et variables, et le dépôt lui-même. La configuration GitHub passe par Terraform ([`ci-cd.md`](ci-cd.md)).

Autorisés, entre autres : `gh pr create`, `gh pr checks --watch [--required]`, `gh pr view`, `gh pr list`, `gh pr comment`, `gh run view`, `gh repo view`, `gh api` en lecture (`GET`), `gh api -X POST repos/<o>/<r>/issues/<n>/comments`.

**Hors périmètre, par décision de l'utilisateur** (2026-11-07, fiche [0023](../decisions/0023-perimetre-garde-bash.md)) : `git reset --hard origin…` et `git clean -fdx` ne sont pas refusés par ce garde-fou. C'est une décision explicite, et non un choix de session. Tout refus de ces commandes serait une décision nouvelle, à poser à l'utilisateur.

## Comment la commande est analysée

Le hook ne cherche pas un motif dans le texte brut (ce qui bloquerait `echo "git commit --no-verify"`). Un petit analyseur de shell (`_Parser`) découpe la ligne en **commandes simples** :

- séparateurs `;`, `&&`, `||`, `|`, `&`, saut de ligne, parenthèses et accolades ; commentaires ; continuation de ligne par `\` ;
- guillemets simples, doubles, `$'…'` et échappements : les opérateurs placés entre guillemets ne séparent rien, les mots sont rendus sans leurs guillemets (`"git" commit '-n'` est `git commit -n`) ; dans `$'…'`, les échappements `\xHH`, `\NNN` (octal), `\uHHHH`, `\UHHHHHHHH`, `\cx`, `\n`, `\t`, `\a`, `\b`, `\e`, `\f`, `\r`, `\v`, `\\`, `\'`, `\"` sont **décodés** (`$'\x67it'` est `git`), un échappement inconnu reste tel quel, et la valeur s'arrête à un NUL comme dans bash ;
- substitutions `$(…)`, `` `…` ``, `<(…)` et `>(…)`, y compris dans des guillemets doubles et dans un heredoc non protégé ; chacune est analysée comme des commandes à part (le mot qui les contient reçoit une valeur inconnue) ; le contenu des guillemets simples n'est jamais analysé ;
- redirections (`>`, `>>`, `2>&1`, `&>`, `<`) ignorées comme mots ; heredocs (`<<EOF`, `<<-EOF`, `<<'EOF'`) et here-strings (`<<<`) : leur texte n'est **pas** une commande, sauf s'il est donné à un shell (`bash <<EOF`, `bash <<< "…"`, `sh -s`) ou s'il contient une substitution dans un heredoc non protégé ;
- tolérant : un guillemet non fermé s'arrête en fin de texte, l'analyseur ne lève jamais d'erreur sur une entrée malformée.

Pour chaque commande simple, le hook retire les mots-clés (`if`, `then`, `do`, `while`, `!`, `{`…) et les affectations `VAR=valeur`, puis **suit les enveloppes** : `env` (dont `-S`, `-u`, `-i`), `sudo`, `doas`, `time`, `command` (sauf `-v` et `-V`, qui décrivent), `builtin`, `exec`, `nohup`, `nice`, `ionice`, `timeout`, `setsid`, `stdbuf`, `chronic`, `xargs`, `coproc` (avec ou sans nom : `coproc git push -f`, `coproc NOM { git push -f; }`), `mise exec -- …`, ainsi que `bash|sh|zsh|dash|ksh|ash -c '…'` (avec options : `-lc`, `-e -c`, `-o pipefail -c`) et `eval …`, récursivement. Le nom de la commande est réduit à son nom de fichier (`/usr/bin/git`, `\git`). `function NOM { … }` : les deux premiers mots sont retirés et le corps est analysé (la définition est refusée si elle contient une commande interdite, puisqu'elle sera appelée plus tard). `git rebase -x/--exec` : voir « `git commit` ».

## Choix de l'analyseur maison

Le hook utilise son propre analyseur de shell (`_Parser`, environ 250 lignes, bibliothèque standard seule) plutôt qu'une bibliothèque. Décision technique mineure, prise en autonomie ; raisons (écartés **sur dossier, sans essai**) :

- **`shlex`** : ne découpe que des mots. Il ne connaît ni `;`, `&&`, `|` comme séparateurs de commandes (sans `punctuation_chars`, et même avec), ni `$(…)`, ni les heredocs, ni `$'…'`, et `shlex.split` **lève une exception** sur un guillemet non fermé alors que le hook ne doit jamais lever sur une entrée malformée.
- **`bashlex`** : dépendance externe (non incluse dans Python) à installer pour le `python3` système avec lequel Claude Code lance le hook (ni mise ni environnement virtuel à cet endroit) ; un analyseur strict échoue sur la syntaxe qu'il ne gère pas, et on devrait de toute façon écrire un repli.
- **`tree-sitter` (grammaire bash)** : dépendance binaire compilée, plus lourde encore à installer et à épingler pour un hook qui tourne à chaque commande Bash ; mêmes exigences de repli.

Un analyseur maison tolérant (il ne lève jamais, un guillemet non fermé s'arrête en fin de texte) a un défaut : ses erreurs sont les nôtres, d'où une table de près de 500 cas et un test de robustesse à graine fixe (concaténations aléatoires de jetons : jamais d'exception, toujours terminé). La règle « forme inconnue sur commande sensible = refus » (voir plus haut) borne le risque quand l'analyseur ne comprend pas.

## Versions vérifiées

Les tables d'options (`git push`, `git config`, `git rebase`, `gh api`) ont été relues contre les aides en ligne de commande de :

- `git version 2.53.0` (`git push -h`, `git config -h`, `git rebase -h`) ;
- `gh version 2.103.3 (2026-10-26)` (`gh api --help`).

`git push --branches` (synonyme de `--all`) existe depuis Git 2.41.0 ([note de recherche](../recherches/2026-11-07-garde-fous-git-gh.md) §1). Une version plus récente de `git` ou de `gh` peut ajouter une option ou une abréviation que le hook ne connaît pas : refaire cette relecture après une mise à jour majeure.

## Défense en profondeur

Le hook est la **première** barrière, pas la dernière :

1. **Règles `deny` de `.claude/settings.json`** : motifs de texte, appliqués par Claude Code avant tout hook, dans tous les modes (la recherche du 2026-11-05 cite la documentation : « Deny rules block in every mode, including bypassPermissions », voir [la note de recherche](../recherches/2026-11-05-outillage-pp.md)). Ils couvrent les formes directes, pas une frontière de sécurité.
2. **Hook `PreToolUse`** (ce document) : formes indirectes (options globales de `git`, enveloppes, sous-shells, `bash -c`…).
3. **Jeton des agents (U5)** : jeton à granularité fine, limité au dépôt, durée courte, variable `GH_TOKEN` rangée hors du dépôt (`chmod 600`) ; le plan PP (R6) rappelle qu'un jeton du propriétaire hérite du contournement administrateur du ruleset, d'où la limitation de ses droits ([0013](../decisions/0013-identite-agents-fusion.md)). **Il ne protège pas la fusion** : l'API de fusion (`PUT /repos/{o}/{r}/pulls/{n}/merge`) demande « Contents: write » côté jeton ([note de recherche](../recherches/2026-11-07-garde-fous-git-gh.md) §3, non vérifié par un appel réel), permission que le jeton U5 possède.
4. **Ruleset de `main`** (Terraform, `infra/terraform/ruleset.tf`) : le push direct vers `main` (règle de pull request avec `bypass_mode = "pull_request"` : le contournement administrateur ne vaut que par pull request), le push forcé (`non_fast_forward`) et la suppression de `main` (`deletion`) sont **bloqués côté serveur**, même si le hook est contourné ou en panne. Le check `ci-cpu` est obligatoire.
5. **Hook Git `pre-commit`** ([`hooks-git.md`](hooks-git.md)) : gitleaks et liens de la documentation ; c'est lui que `--no-verify` et `core.hooksPath` visent, et la CI refait les mêmes contrôles.

**Pour la fusion d'une pull request, il n'y a aucune barrière côté serveur à ce jour.** Le ruleset exige 0 approbation (`required_approving_review_count = 0`) et l'API de fusion est ouverte au jeton U5 (« Contents: write ») : seuls le hook local (`gh pr merge`, `gh api …/merge`, mutations GraphQL) et la discipline des agents empêchent un agent de fusionner. Une barrière côté serveur (compte machine pour les agents avec le rôle *Write*, une approbation requise, l'utilisateur fusionne comme administrateur) est prévue en **E10b**, décision de l'utilisateur du 2026-11-07 ([0021](../decisions/0021-fusion-compte-machine-agents.md)). Tant que E10b n'est pas appliqué (`tf-apply` par l'utilisateur), le texte ci-dessus fait foi, pas le point 4 pour la fusion.

## Limites connues

Une analyse textuelle ne voit pas ce qui n'est pas écrit dans la commande. **Non couvert** :

- **Scripts et fichiers** : `bash script.sh`, `./deploy.sh`, `source x`, `make`, `just <recette>` (par exemple une recette qui appellerait `gh pr merge`). Le contenu du fichier n'est pas lu. Aussi `source <(…)` et `bash <(…)` (le texte produit par la substitution de processus n'est pas connu), et `busybox sh -c '…'` (`busybox` n'est pas dans la liste des interpréteurs).
- **Alias et fonctions** : un alias de shell (`alias git='git commit -n'`) ; `git config alias.*` est refusé en écriture (règle `git-config`) mais un alias déjà présent dans `~/.gitconfig` ou le dépôt, ou ajouté par un fichier modifié autrement, n'est pas vu. (`gh alias set` est refusé.)
- **Variables et expansions** : `git commit $FLAGS`, `$CMD` (la commande ou l'option est inconnue), expansions d'accolades (`git commit {-n,-m}`). Une cible de push calculée (`git push origin "$BRANCH"`) est en revanche jugée comme `HEAD` (voir « Règles »). `printf -- -n | xargs git commit` : `xargs` complète la commande avec un argument venu de l'entrée standard, que l'analyse ne voit pas.
- **Programmes qui appellent Git ou GitHub** : `python3 -c "import subprocess; …"`, `node -e`, `perl`, `curl -X PUT https://api.github.com/repos/…/pulls/7/merge -H "Authorization: …"`, `wget`, bibliothèques Git. Un appel direct à l'API REST par `curl` n'est pas vu ; seul le jeton limité (point 3) et le ruleset (point 4) l'arrêtent.
- **Texte envoyé à un shell par un tube** : `echo "git commit -n" | bash`, `curl … | sh`. Seuls les heredocs et here-strings donnés directement à un shell sont suivis.
- **Commandes distantes ou lancées par un autre programme** : `ssh hôte 'git …'`, `watch`, `flock`, `script -c`, `find -exec git … {} +`, `docker exec`.
- **Syntaxes rares** : `case … esac` complexes, noms d'abréviation d'option autres que ceux listés. Un **heredoc faussement lu** : `$((1<<2))` (arithmétique) peut être pris pour un début de heredoc `<<2` ; le texte qui suit jusqu'au délimiteur est alors traité comme le corps d'un heredoc (donc ignoré) au lieu de commandes. Faux négatif possible, jamais de faux refus.
- **Commandes Git qui exécutent un texte** (hors `git rebase -x/--exec`, suivi) : `git submodule foreach CMD`, `git bisect run CMD`, `git filter-branch --env-filter|--tree-filter|--msg-filter… CMD`, `git difftool`/`mergetool`, `git instaweb`, `git -c core.editor=… commit` (clés qui lancent un programme : `core.editor`, `core.sshCommand`, `core.pager`, `core.fsmonitor`, `diff.external`, `credential.helper`, `gpg.program`…). Le texte ou le programme est inconnu du garde-fou.
- **Fichiers modifiés sans passer par une commande Bash analysée** : un `Edit`/`Write` (ou `sed -i`, `tee`, `echo >>`, `cp`) sur `.git/config`, `.git/hooks/`, `.githooks/`, `~/.gitconfig`, `~/.config/gh/config.yml` (alias `gh`, éditeur…) ou `.claude/settings.json` change le comportement de Git, de `gh` ou du garde-fou lui-même, et le texte de la commande ne contient aucune règle interdite. Un garde-fou sur les outils `Edit` et `Write` (chemins protégés) est **reporté à la refonte des agents**, hors d'E10 (décision [0023](../decisions/0023-perimetre-garde-bash.md)). Autres variables d'environnement qui chargent de la configuration (`GIT_CONFIG_GLOBAL=fichier`, `GIT_CONFIG_SYSTEM`) : non examinées, seul le contenu de `GIT_CONFIG_KEY_n`/`GIT_CONFIG_PARAMETERS` l'est. Un `push.default = matching` déjà présent dans une configuration existante n'est pas détecté non plus (il pousserait aussi `main` si elle existe des deux côtés).
- **Autres moyens d'écraser un historique ou de contourner une règle** : `git update-ref -d refs/heads/main`, `git remote set-url`, `git send-pack`, `git reset --hard` suivi d'un push forcé par autre chose que `git push`.
- **Changement de branche invisible** : `cd autre-dépôt && git push` (la branche est lue dans le dossier de la commande, pas dans celui où mène le `cd`) ; un changement de branche fait par un script ou une commande non analysée avant le push.
- **Faux positifs connus** (assumés, par prudence) : `git push` sans cible depuis un dossier où la branche ne se lit pas ; `gh api graphql … -F owner=$(…)` (toute substitution dans une valeur de `gh api graphql`) ; une écriture `gh api` vers `repos/…/contents/…` ou `…/merges` ; `gh api -X POST repos/o/r/issues/$(…)/comments` (endpoint contenant une substitution) ; `git config --unset alias.x` (suppression d'une clé interdite) ; `git switch $B` suivi d'un `git push` sans cible ; `git -c push.default=… push` ; un mot `git` ou `gh` quelconque dans une entrée refusée à cause d'une panne du hook.
- Les faux négatifs ci-dessus sont acceptés ; les faux positifs sont évités autant que possible, mais un cas rare peut exister (une commande écrite avec des guillemets non fermés, par exemple). Un refus est toujours expliqué en français.

## Comportement avec `--dangerously-skip-permissions` : à confirmer

Le plan (E10, R7) fait du hook la principale protection dans Claudeus, qui lance les agents avec `--dangerously-skip-permissions`. D'après la note de recherche du 2026-11-05, les règles `deny` s'appliquent dans tous les modes ; en revanche, **la documentation consultée ne dit pas explicitement si les hooks `PreToolUse` continuent de s'exécuter dans ce mode** (confiance faible). **Cela n'a pas été vérifié.** À faire à la main, sans lien avec les tests automatiques :

1. dans une session lancée avec `--dangerously-skip-permissions`, demander à Claude `git commit --allow-empty --no-verify -m test` (sur une branche de travail, à annuler ensuite) ;
2. vérifier que la commande est refusée avec le message en français, que `.cache/hooks/guard.log` contient une ligne `BLOCKED rule=no-verify …`, et que `git log` ne montre aucun commit ;
3. refaire l'essai en mode normal ; consigner le résultat (version de Claude Code, mode, résultat) dans cette page et dans le journal, et reporter l'écart dans le risque R7 du plan si le hook ne s'exécute pas.

Tant que ce n'est pas fait, considérer le hook comme **non confirmé** sous `--dangerously-skip-permissions`, et ne compter dans ce mode que sur les règles `deny`, le jeton limité et le ruleset.

Sous-agents : d'après la note [`2026-11-07-securite-hook-formatage.md`](../recherches/2026-11-07-securite-hook-formatage.md), les hooks de `.claude/settings.json` s'appliquent aussi aux appels d'outils des sous-agents (`PreToolUse` compris). Non vérifié en pratique pour ce hook.

## Vérification

```
python3 -m unittest tools.tests.test_guard_bash    # ou just tools-test (tout)
just lint
```

`tools/tests/test_guard_bash.py` est hermétique : la branche courante est fournie par une fausse fonction, les journaux vont dans un dossier temporaire. `tools/tests/test_session_start.py` vérifie le compte des lignes `hook error` affiché à l'ouverture de session. Le premier contient :

- `RuleTableTest` : une table de près de 300 commandes refusées (avec la règle attendue) et de plus de 200 commandes autorisées, avec un cas au moins par correction de la revue d'architecte (`gh api graphql` opaque, endpoint calculé, `heads/main`, `--branches`, clés de configuration, `$'\x67it'`, `coproc`, `function`, `git rebase -x`, `gh pr merge --help`, `repos/…/merges` et `contents`, `-X=DELETE`), dont les variantes d'E10 (`git -c x=y commit --no-verify`, `git commit -an`, `git commit -nm "x"`, `gh pr merge --auto`, `gh pr merge 7 --squash`, `cd x && gh pr merge`, `bash -c "git push --force"`, `git push origin HEAD:main`), les textes qui ne font que citer une commande interdite, des chemins avec espaces et « : », des entrées vides ou malformées ;
- `CurrentBranchTest` et `PushTargetTest` : branche courante, `git -C`, cache de la lecture, changement de branche dans la ligne, branche inconnue = refus, cible calculée, cible configurée d'un push sans refspec ;
- `ConfigKeyTest`, `AnsiCQuotingTest`, `HelpTest` : la fonction unique des clés interdites et ses quatre canaux, le décodage de `$'…'`, l'aide de `gh pr merge` ;
- `GitReaderTest` : le budget de temps partagé des lectures `git` (horloge simulée) ;
- `RobustnessTest` : concaténations aléatoires de jetons à graine fixe (3 000 lignes et 500 entrées brutes) : jamais d'exception, toujours terminé, code de sortie 0 ou 2 ; entrées très longues ;
- `TokenizerTest` et `WrapperTest` : l'analyseur et les enveloppes ;
- `LogTest` : codes de sortie, message en français, journal (blocage, JSON invalide, commande absente, exception interne, rotation, troncature), et le comportement de panne : refus pour `git`/`gh`, passage sinon ;
- `RealGitTest` : lecture de la branche et de la cible de push avec le vrai `git` dans un dépôt jetable avec un dépôt distant nu (sauté sans `git`) ;
- `ScriptProcessTest` : le script lancé comme par Claude Code (code de sortie, stdout vide, stderr en français) ;
- `SettingsTest` : le hook `PreToolUse` existe, sans `|| true` ; `PostToolUse` et `SessionStart` sont conservés ; les `deny` d'origine sont conservés et les nouveaux présents (dont ceux du push vers `main`/`master`, et l'absence de `Bash(git push *)`) ; le `timeout` couvre le budget des lectures `git`.

**Non testé en réel dans Claude Code** : ni le refus d'une vraie commande (essai manuel d'E10 : demander `git commit --no-verify` et constater le refus), ni le comportement sous `--dangerously-skip-permissions` (voir plus haut).

## Étendre ou modifier les règles

Toute modification du périmètre (nouvelle commande interdite, règle retirée) est une décision à poser à l'utilisateur. Techniquement : ajouter un `Violation` et une fonction `_check_…` dans `guard_bash.py`, ajouter les cas refusés **et** autorisés aux tables de `test_guard_bash.py`, et mettre à jour cette page. Les constantes (`PROTECTED_BRANCHES`, `GRAPHQL_FORBIDDEN`, `GH_REPO`, `GH_FORBIDDEN`, `WRAPPERS`, `MAX_DEPTH`, `GIT_TIMEOUT_SECONDS`, `GIT_BUDGET_SECONDS`) sont en tête ou près de leur règle. Le `timeout` de `.claude/settings.json` (10 s) doit rester supérieur à `GIT_BUDGET_SECONDS` plus une marge (un test le vérifie). Les clés de configuration interdites sont toutes dans `_forbidden_config_key`.
