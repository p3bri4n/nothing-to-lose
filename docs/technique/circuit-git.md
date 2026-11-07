# Circuit Git des agents

*Mise à jour : 2026-11-07 (création, étape E10 du plan PP, voir [`../plans/PP.md`](../plans/PP.md) §E10 ; identité des agents et fusion réécrites pour E10b : décisions [0013](../decisions/0013-identite-agents-fusion.md) et [0021](../decisions/0021-fusion-compte-machine-agents.md), jeton classique à portée `repo` : [0024](../decisions/0024-jeton-compte-machine-classique.md) ; garde-fou : [0022](../decisions/0022-panne-garde-bash.md), [0023](../decisions/0023-perimetre-garde-bash.md), [0028](../decisions/0028-garde-bash-identifiants-github.md) ; revue du propriétaire : [0025](../decisions/0025-barriere-serveur-codeowners.md) ; isolement des identifiants : [0026](../decisions/0026-isolement-identifiants-claudeus.md) ; pas de portée `workflow` : [0027](../decisions/0027-portee-workflow-jamais.md))*

Décrit le circuit **tel qu'il existe** : ce qu'un agent fait pour livrer une tâche, ce qui lui est interdit et pourquoi, et ce qui le contrôle. Le détail du garde-fou Bash est dans [`garde-fous-bash.md`](garde-fous-bash.md) ; les hooks Git dans [`hooks-git.md`](hooks-git.md) ; la CI dans [`ci-cd.md`](ci-cd.md) ; le modèle de pull request dans [`modeles-github.md`](modeles-github.md).

Règle de base : **les agents ne fusionnent jamais**. Ils s'arrêtent à la pull request ouverte et l'utilisateur fusionne (squash, décision D8 du plan, [0013](../decisions/0013-identite-agents-fusion.md)).

## Le circuit, étape par étape

1. **Branche depuis `main` à jour.** Mettre `main` à jour, puis créer la branche de travail :

   ```bash
   git switch main
   git pull --ff-only origin main
   git switch -c <jalon>/<sujet-court>      # par exemple pp/circuit-git
   ```

   Le jalon est `PP`, `P0` à `P5`, ou le nom de l'étape du plan.

2. **Commits en français.** Chaque commit passe les hooks Git (voir plus bas). Ne jamais contourner un hook : `--no-verify` et `-n` sont refusés (voir « Interdits »).

3. **Pousser la branche de travail.**

   ```bash
   git push -u origin HEAD
   ```

   Ce push est autorisé depuis n'importe quelle branche **sauf** `main` et `master`. Le garde-fou refuse tout push dont la cible est `main` ou `master`.

4. **Ouvrir la pull request.** Le corps est écrit dans un fichier, à partir de [`.github/pull_request_template.md`](../../.github/pull_request_template.md) :

   ```bash
   gh pr create --title "<titre en français>" --body-file <fichier-du-corps>
   ```

   Remplir les sections du modèle (« Résumé », « Jalon », « Ticket lié »). Dans la section **« Liste de contrôle »**, les sept cases sont **toutes cochées**. Un point qui ne s'applique pas reste coché et suivi de « — sans objet », par exemple :

   ```
   - [x] décision structurante posée à l'utilisateur, ou « sans objet » — sans objet
   ```

   Une case décochée fait échouer le contrôle de la liste, même si le point ne s'applique pas : il faut la cocher et écrire « — sans objet ». Les sept points sont listés dans [`modeles-github.md`](modeles-github.md).

5. **Attendre les contrôles requis.**

   ```bash
   gh pr checks --watch --required
   ```

   Le check obligatoire est `ci-cpu`. Si le contrôle de la liste de contrôle échoue, corriger le corps de la PR : **modifier la description** déclenche une nouvelle exécution (« Re-run jobs » rejoue l'ancien corps et échoue de nouveau).

6. **Prévenir l'utilisateur.** Indiquer le numéro et le lien de la pull request, et l'état des contrôles. L'utilisateur relit et fusionne lui-même.

## Contrôles locaux avant la pull request

| Commande | Rôle |
|---|---|
| `just check` | Contrôle complet ; à ce jour (PP) il se réduit à `just lint` |
| `just lint` | `versions`, `tools-test`, `fmt-check`, `docs-links`, `secrets-scan`, `actionlint`, `tf-check` |
| `just fmt` / `just fmt-check` | Formater / vérifier le formatage (Markdown exclu, décision D7) |
| `just docs-links` | Liens relatifs de la documentation |

Ces contrôles sont refaits à l'identique par `ci-cpu`.

## Hooks qui s'appliquent au travail d'un agent

| Hook | Déclencheur | Rôle | Documentation |
|---|---|---|---|
| `pre-commit` (Git, `.githooks/pre-commit`) | `git commit` | gitleaks sur les changements indexés, puis liens de la documentation (`just pre-commit`). Fermé par défaut : sans `mise` ou `gitleaks`, le commit est refusé. | [`hooks-git.md`](hooks-git.md) |
| Formatage à l'édition (`PostToolUse`, `tools/hooks/format_on_edit.py`) | `Write`, `Edit`, `MultiEdit` | Formate le fichier touché avec `tools/fmt.py`. Ne bloque jamais. | [`hook-format-on-edit.md`](hook-format-on-edit.md) |
| Garde-fou Bash (`PreToolUse`, `tools/hooks/guard_bash.py`) | chaque commande `Bash` | Refuse les contournements du circuit (voir « Interdits »). Code 2 en cas de refus. | [`garde-fous-bash.md`](garde-fous-bash.md) |

`just hooks-install` active les hooks Git du dépôt (une fois par clone, configuration locale).

## Interdits aux agents, et pourquoi

| Interdit | Pourquoi | Protection |
|---|---|---|
| `git commit --no-verify`, `git commit -n` (et les groupes de drapeaux contenant `n`, comme `-an`) | Désactive gitleaks et la vérification des liens (R4). Seul l'utilisateur peut contourner un hook, en cas d'urgence réelle. | Règle `deny`, puis garde-fou (`no-verify`) |
| `--no-verify` sur `git push`, `git merge`, `git rebase` | Même raison : désactive leur hook | Garde-fou |
| `git push --force`, `-f`, `--force-with-lease`, refspec `+…`, `--mirror`, `--delete`, `--prune`, `--all` | Réécrit ou supprime l'historique partagé ; `--all` pousserait aussi `main` | Règles `deny` (formes directes), garde-fou (`push-force`, `push-mirror`, `push-delete`, `push-all`), ruleset (force-push et suppression bloqués côté serveur) |
| Tout push vers `main` ou `master` (`HEAD:main`, `refs/heads/main`, `git push` sans cible sur `main`…) | Contourne la pull request | Règles `deny`, garde-fou (`push-main`), ruleset (push direct bloqué côté serveur) |
| `gh pr merge` (toutes variantes, `--auto` compris), `gh api …/pulls/<n>/merge`, mutations GraphQL de fusion | Seul l'utilisateur fusionne (D8, [0013](../decisions/0013-identite-agents-fusion.md)) | Règle `deny` (`gh pr merge`), garde-fou (`gh-pr-merge`, `gh-api`). Barrière côté serveur depuis E10b : 1 approbation d'un propriétaire du code (CODEOWNERS, [0025](../decisions/0025-barriere-serveur-codeowners.md)) ; sur l'hôte, protection intérimaire contre l'erreur d'un agent ([0026](../decisions/0026-isolement-identifiants-claudeus.md)) (voir « Identité des agents et fusion ») |
| Désactiver les hooks Git (`core.hooksPath`), écrire `alias.*`, `include.path`, `remote.*.push`, `push.default` | Désactive les hooks ; masque une commande ; redirige ce que pousse un push | Garde-fou (`hooks-path`, `git-config`) |
| `gh repo delete`, `edit`, `archive`, `rename`, `gh secret` et `gh variable` en écriture, `gh alias set` | La configuration GitHub passe par Terraform, jamais par l'interface ou la CLI (décision [0001](../decisions/0001-terraform-pour-github.md)) | Règle `deny` (`gh repo delete`), garde-fou (`gh-admin`) |
| `terraform apply`, `destroy`, `import`, `state`, `just tf-apply` | Réservé à l'utilisateur | Règles `deny` |
| `gh auth token\|login\|logout\|switch\|refresh`, `gh auth status --show-token`, affecter ou retirer `GH_TOKEN` / `GITHUB_TOKEN` (et variantes `ENTERPRISE`) | Les agents agissent avec le compte machine, rien d'autre ; ces commandes manipuleraient ou afficheraient les identifiants | Garde-fou (`gh-auth`, `gh-token-env`), **palliatif partiel** : voir la limite ci-dessous |

**Règle sur le jeton** : le jeton GitHub des agents (jeton classique à portée `repo`, [0024](../decisions/0024-jeton-compte-machine-classique.md)) n'a que la portée `repo` ; **jamais `workflow`** ([0027](../decisions/0027-portee-workflow-jamais.md) : l'agent prépare un changement de workflow, l'utilisateur le pousse), ni `admin:*`, `delete_repo` ou autre portée. Un jeton classique n'a pas de permission *Actions* séparée : la règle « jamais *Actions* en écriture » ne s'applique donc plus au jeton lui-même. `gpu-eval.yml` reste protégé par sa garde `github.repository_owner == github.actor` (le compte machine est refusé) et par le rôle *Write* du compte, qui ne gère pas les paramètres du dépôt.

**Hors périmètre du garde-fou, par décision de l'utilisateur** (2026-11-07, [0023](../decisions/0023-perimetre-garde-bash.md)) : `git reset --hard origin…` et `git clean -fdx` ne sont pas refusés. Les modifications de `.git/`, `.githooks/` ou `.claude/settings.json` par `Edit` ou `Write` ne le sont pas non plus : ce garde-fou est reporté à la refonte des agents.

Le détail de la syntaxe reconnue (enveloppes `env`, `bash -c`, `eval`, options globales `git -c`, `git -C`, etc.) et les limites connues du garde-fou sont dans [`garde-fous-bash.md`](garde-fous-bash.md).

## Identité des agents et fusion

Décision [0021](../decisions/0021-fusion-compte-machine-agents.md) (étape E10b) : les agents travaillent avec un **compte machine GitHub** distinct du propriétaire. Procédure complète pour l'utilisateur : [`compte-machine-agents.md`](compte-machine-agents.md).

- **Compte** : invité sur le dépôt par Terraform (variable `agents_account`, `infra/terraform/collaborator.tf`) avec le rôle *Write* (permission `push`), jamais *admin* ni *maintain*.
- **Jeton** : celui **du compte machine**, jamais celui du propriétaire (le jeton U5 est supprimé), fourni par `GH_TOKEN` (par exemple `~/.config/nothing-to-lose/agents.env`, `chmod 600`, hors du dépôt). C'est un **jeton classique à portée `repo`**, de durée courte (30 jours) : un jeton à granularité fine ne peut pas viser un dépôt personnel dont le compte est collaborateur ([0024](../decisions/0024-jeton-compte-machine-classique.md), procédure (e) de [`compte-machine-agents.md`](compte-machine-agents.md)). Le compte n'a accès à aucun autre dépôt ni organisation.
- **Barrière côté serveur** : le ruleset exige **1 approbation d'un propriétaire du code** (`required_approving_review_count = 1`, `require_code_owner_review = true`, [`.github/CODEOWNERS`](../../.github/CODEOWNERS) : le propriétaire du dépôt ; [0025](../decisions/0025-barriere-serveur-codeowners.md)) ; `require_last_push_approval` et `dismiss_stale_reviews_on_push` sont actifs. Le compte machine n'a pas de contournement, ne peut pas approuver sa propre pull request et n'est pas propriétaire du code : ses approbations ne comptent pas, il ne peut pas fusionner. Le propriétaire approuve, ou fusionne par le contournement du rôle *admin* (`bypass_mode = "pull_request"`). Ses propres pull requests passent par ce contournement.
- **Limite de la barrière sur l'hôte** : les agents tournent sous le même compte Unix que l'utilisateur, dont les identifiants (connexion `gh`, clé SSH, `GITHUB_TOKEN` d'administration, `terraform.tfvars`) restent à leur portée. Sur l'hôte, la barrière ne protège donc que contre l'erreur d'un agent. **Cible : agents seulement dans Claudeus** (sans `~/.config/gh` ni `~/.ssh`, `GH_TOKEN` du compte machine injecté), où elle est réelle ([0026](../decisions/0026-isolement-identifiants-claudeus.md), détail dans la section « Limites » de [`compte-machine-agents.md`](compte-machine-agents.md)). Mesures intérimaires : environnement nettoyé au lancement, avertissement `SessionStart`, garde-fou `gh-auth` / `gh-token-env`. Le rôle *Write* permet aussi tags et releases publics, push forcé sur d'autres branches que `main` et résolution de conversations.
- **Limite** : une fois la pull request approuvée par le propriétaire et les contrôles verts, tout compte *Write* peut la fusionner, le compte machine compris. Le propriétaire approuve donc au moment de fusionner, et ne doit jamais approuver une pull request d'agent sans la fusionner dans la foulée. Le hook local (`gh pr merge`, `gh api …/merge`) reste la première barrière ; le ruleset est la seconde, côté serveur.
- **Poussées** : les agents poussent avec l'identité du compte machine (remote HTTPS et `gh auth setup-git`), pas avec la clé SSH du propriétaire.
- **Vérification** : `just verify-pp merge-barrier --agents-account <compte>` (lecture seule, lancé par l'utilisateur).

**Avant que l'utilisateur ait appliqué E10b** (`tf-apply`, compte créé, jeton remplacé) : l'ancien jeton U5 du propriétaire reste utilisé, le ruleset exige 0 approbation et **la fusion n'est protégée que par le garde-fou local et la discipline des agents**.

## Protections côté dépôt

- **Ruleset de `main`** (Terraform, [`ci-cd.md`](ci-cd.md)) : passage par une pull request avec une approbation d'un propriétaire du code, check `ci-cpu` obligatoire et à jour, historique linéaire, ni suppression ni force-push. `bypass_mode = "pull_request"` pour le rôle admin : le contournement ne vaut que par une pull request.
- **`ci-cpu`** est le check obligatoire. Son nom ne doit pas changer sans mettre à jour `required_ci_check` dans Terraform, dans le même changement (risque R12). Le job contient le contrôle bloquant de la liste de contrôle, en dernière étape.
- **`gpu-eval.yml`** n'est jamais déclenché par `pull_request` (dépôt public). Il ne tourne que sur push vers `main` ou lancement manuel.
- **Terraform** est la seule voie de modification de la configuration GitHub.

## Essai manuel du 2026-11-07

Essai fait dans la session principale. Les quatre commandes suivantes ont été **refusées par le garde-fou**, avec une explication en français :

| Commande demandée | Résultat |
|---|---|
| `git commit --no-verify` | refusée |
| `git -c x=y commit -an` | refusée |
| `gh pr merge 99999 --auto --squash` | refusée |
| `git push --force --dry-run origin HEAD:main` | refusée |

**Non confirmé (R7, [`../plans/PP.md`](../plans/PP.md))** : le comportement du garde-fou sous `--dangerously-skip-permissions`, mode par défaut de Claudeus. La documentation consultée ne dit pas si les hooks `PreToolUse` s'exécutent dans ce mode. Procédure à faire à la main (voir [`garde-fous-bash.md`](garde-fous-bash.md), « Comportement avec `--dangerously-skip-permissions` ») : demander un `git commit --allow-empty --no-verify -m test` sur une branche jetable, vérifier le refus, la ligne `BLOCKED rule=no-verify` dans `.cache/hooks/guard.log` et l'absence de commit, puis consigner la version de Claude Code, le mode et le résultat. Tant que ce n'est pas fait, ne compter dans ce mode que sur les règles `deny`, le jeton limité et le ruleset.

## Liens

- Plan : [`../plans/PP.md`](../plans/PP.md) §E10, décisions D8 et risques R4, R6, R7, R12.
- Décisions : [0013](../decisions/0013-identite-agents-fusion.md) (fusion par l'utilisateur), [0021](../decisions/0021-fusion-compte-machine-agents.md) (compte machine, E10b ; procédure : [`compte-machine-agents.md`](compte-machine-agents.md)), [0024](../decisions/0024-jeton-compte-machine-classique.md) (jeton classique à portée `repo`), [0025](../decisions/0025-barriere-serveur-codeowners.md) (CODEOWNERS), [0026](../decisions/0026-isolement-identifiants-claudeus.md) (isolement des identifiants, Claudeus), [0027](../decisions/0027-portee-workflow-jamais.md) (pas de portée `workflow`), [0022](../decisions/0022-panne-garde-bash.md) (panne du garde-fou), [0023](../decisions/0023-perimetre-garde-bash.md) (périmètre du garde-fou), [0028](../decisions/0028-garde-bash-identifiants-github.md) (identifiants GitHub dans le garde-fou).
- Garde-fou Bash : [`garde-fous-bash.md`](garde-fous-bash.md). Hooks Git : [`hooks-git.md`](hooks-git.md). CI et Terraform : [`ci-cd.md`](ci-cd.md). Modèles : [`modeles-github.md`](modeles-github.md).
