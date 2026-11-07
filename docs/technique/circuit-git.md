# Circuit Git des agents

*Mise à jour : 2026-11-07 (création, étape E10 du plan PP, voir [`../plans/PP.md`](../plans/PP.md) §E10 ; identité des agents : décisions [0013](../decisions/0013-identite-agents-fusion.md) et [0021](../decisions/0021-fusion-compte-machine-agents.md) ; garde-fou : [0022](../decisions/0022-panne-garde-bash.md), [0023](../decisions/0023-perimetre-garde-bash.md))*

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
| `gh pr merge` (toutes variantes, `--auto` compris), `gh api …/pulls/<n>/merge`, mutations GraphQL de fusion | Seul l'utilisateur fusionne (D8, [0013](../decisions/0013-identite-agents-fusion.md)) | Règle `deny` (`gh pr merge`), garde-fou (`gh-pr-merge`, `gh-api`). **Aucune barrière serveur à ce jour** (voir « Identité ») |
| Désactiver les hooks Git (`core.hooksPath`), écrire `alias.*`, `include.path`, `remote.*.push`, `push.default` | Désactive les hooks ; masque une commande ; redirige ce que pousse un push | Garde-fou (`hooks-path`, `git-config`) |
| `gh repo delete`, `edit`, `archive`, `rename`, `gh secret` et `gh variable` en écriture, `gh alias set` | La configuration GitHub passe par Terraform, jamais par l'interface ou la CLI (décision [0001](../decisions/0001-terraform-pour-github.md)) | Règle `deny` (`gh repo delete`), garde-fou (`gh-admin`) |
| `terraform apply`, `destroy`, `import`, `state`, `just tf-apply` | Réservé à l'utilisateur | Règles `deny` |

**Règle sur le jeton** : le jeton GitHub des agents ne doit **jamais** recevoir la permission *Actions* en écriture. Avec elle, il pourrait déclencher le `workflow_dispatch` de `gpu-eval.yml`, qui tourne sur le runner GPU auto-hébergé. La permission *Workflows* (modifier `.github/workflows/`) n'est accordée que si les agents modifient la CI, comme prévu par le plan (U5).

**Hors périmètre du garde-fou, par décision de l'utilisateur** (2026-11-07, [0023](../decisions/0023-perimetre-garde-bash.md)) : `git reset --hard origin…` et `git clean -fdx` ne sont pas refusés. Les modifications de `.git/`, `.githooks/` ou `.claude/settings.json` par `Edit` ou `Write` ne le sont pas non plus : ce garde-fou est reporté à la refonte des agents.

Le détail de la syntaxe reconnue (enveloppes `env`, `bash -c`, `eval`, options globales `git -c`, `git -C`, etc.) et les limites connues du garde-fou sont dans [`garde-fous-bash.md`](garde-fous-bash.md).

## Identité des agents et fusion

**Aujourd'hui (jusqu'à E10b)** : les agents utilisent le jeton U5, à granularité fine, limité au dépôt, de courte durée, fourni par la variable `GH_TOKEN` (par exemple dans `~/.config/nothing-to-lose/agents.env`, `chmod 600`, hors du dépôt). Le plan prévoit pour U5 *Contents*, *Pull requests* et *Issues* en écriture (*Workflows* seulement si les agents modifient la CI) : ces permissions suffisent à appeler l'API de fusion (non vérifié par un appel réel, voir [`garde-fous-bash.md`](garde-fous-bash.md), « Défense en profondeur »). **La fusion n'est donc protégée que par le garde-fou local et par la discipline des agents.** Le ruleset n'exige aucune approbation (`required_approving_review_count = 0`).

**Cible (E10b, [0021](../decisions/0021-fusion-compte-machine-agents.md))**, décision de l'utilisateur, PR séparée :

- un compte machine pour les agents, invité avec le rôle *Write* (jamais administrateur) ;
- un jeton à granularité fine **de ce compte** (*Contents*, *Pull requests*, *Issues* en écriture), qui remplace U5 ;
- `required_approving_review_count = 1` dans `infra/terraform/ruleset.tf` : un auteur ne peut pas approuver sa propre pull request, donc une pull request d'agent exige un autre acteur ;
- l'utilisateur fusionne comme administrateur, par `bypass_mode = "pull_request"`.

Actions de l'utilisateur pour E10b : créer le compte machine, accepter l'invitation, créer le jeton, lancer `just tf-apply`. Tant que E10b n'est pas appliqué, les mentions de U5 de ce document valent.

## Protections côté dépôt

- **Ruleset de `main`** (Terraform, [`ci-cd.md`](ci-cd.md)) : passage par une pull request, check `ci-cpu` obligatoire et à jour, historique linéaire, ni suppression ni force-push. `bypass_mode = "pull_request"` pour le rôle admin : le contournement ne vaut que par une pull request.
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
- Décisions : [0013](../decisions/0013-identite-agents-fusion.md) (fusion par l'utilisateur), [0021](../decisions/0021-fusion-compte-machine-agents.md) (compte machine, E10b), [0022](../decisions/0022-panne-garde-bash.md) (panne du garde-fou), [0023](../decisions/0023-perimetre-garde-bash.md) (périmètre du garde-fou).
- Garde-fou Bash : [`garde-fous-bash.md`](garde-fous-bash.md). Hooks Git : [`hooks-git.md`](hooks-git.md). CI et Terraform : [`ci-cd.md`](ci-cd.md). Modèles : [`modeles-github.md`](modeles-github.md).
