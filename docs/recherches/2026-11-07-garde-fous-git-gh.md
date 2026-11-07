# Garde-fous Git, Claude Code et GitHub : vérifications sourcées

Date de la recherche : 2026-11-07. Recherche faite par `chercheur-web` à partir de la documentation officielle quand elle était accessible, complétée par des sources secondaires quand indiqué. Aucune décision n'est prise ici : les faits sont rapportés pour la session principale et l'utilisateur.

Limite : aucun shell disponible pendant cette recherche, donc `git --version` n'a pas pu être lancé. La version installée sur la machine reste à vérifier.

## 1. Git

**Réponse courte.** Oui, `git push --branches` est un synonyme de `git push --all` (pousser toutes les branches sous `refs/heads/`). L'option a été ajoutée dans Git 2.41.0. Côté destination d'un refspec, `heads/main` se résout en `refs/heads/main` si cette référence existe sur le distant ; sinon le comportement dépend de la règle de préfixe décrite plus bas.

**Détails utiles.**
- Git 2.41.0 : les notes de version indiquent « `git push --all` gained an alias `git push --branches` ». Source : fichier `Documentation/RelNotes/2.41.0.adoc` du dépôt officiel (consulté sur raw.githubusercontent.com). Le patch original date du 6 mai 2023 (liste git, Teng Long). La date exacte de sortie de 2.41.0 n'a pas été confirmée par une source trouvée ; de mémoire, juin 2023, à vérifier.
- La page `git-push` (version la plus récente vue : 2.55.0, mise à jour indiquée 2026-06-29) liste `[--all | --branches | --mirror | --tags]` comme alternatives, et décrit `--branches` comme « Push all branches (i.e. refs under `refs/heads/`); cannot be used with other <refspec> ». La page ne dit pas explicitement « synonyme » ; c'est confirmé par les notes de version et le commit.
- Résolution de `<refname>` (page `gitrevisions`, version la plus récente vue : 2.56.0) : ordre `refs/<nom>`, puis `refs/tags/`, `refs/heads/`, `refs/remotes/`… `heads/main` correspond donc à `refs/heads/main`. La page cite `heads/master` comme équivalent de `refs/heads/master`. L'exemple n'est pas détaillé pour le cas exact (inférence sur les règles).
- Destination d'un refspec (page `git-push`) : l'ordre des règles est important.
  1. Si `<dst>` désigne sans ambiguïté une référence existante sur le distant, il est étendu à cette référence.
  2. Sinon, si `<src>` résout vers `refs/heads/` ou `refs/tags/`, ce préfixe est ajouté à `<dst>` (exemple de la doc : `main:other` devient `main:refs/heads/other`).
  3. Sinon, erreur si la résolution n'est pas univoque.
- Conséquence (inférence à partir de ces règles, non testée) : `git push origin HEAD:heads/main` pousse vers `refs/heads/main` si cette branche existe déjà sur le distant. Si elle n'existe pas encore, la règle 2 pourrait produire `refs/heads/heads/main`. Pour un usage de garde-fou, écrire `refs/heads/main` explicitement évite l'ambiguïté.

**Niveau de confiance.** Élevé pour la présence de `--branches` depuis 2.41.0 (notes de version officielles, lues directement). Élevé pour les règles de résolution (doc officielle). Moyen pour la conséquence sur `heads/main` absent côté distant (inférence).

**Sources.**
- [Git 2.41.0, notes de version (`Documentation/RelNotes/2.41.0.adoc`)](https://raw.githubusercontent.com/git/git/master/Documentation/RelNotes/2.41.0.adoc), version 2.41.0, date de sortie non confirmée (juin 2023 de mémoire).
- [Patch « push: introduce '--branches' option » (liste git, Teng Long)](https://public-inbox.org/git/20230506112740.61454-2-tenglong.tl@alibaba-inc.com/), 6 mai 2023.
- [Documentation `git-push`](https://git-scm.com/docs/git-push), dernière version vue 2.55.0 (2026-06-29).
- [Documentation `gitrevisions`](https://git-scm.com/docs/gitrevisions), dernière version vue 2.56.0.

## 2. Claude Code : règles de permission

**Réponse courte.** Pour un deny sur les pushes, `Bash(git push *)` est la règle la plus large et couvre les trois cas. Les motifs exacts (`Bash(git push origin main)`) ne couvrent que cette forme précise. Le `:*` final est une forme équivalente à ` *` ; un `:` placé au milieu de l'argument est un caractère littéral. Les règles `deny` s'appliquent en mode `bypassPermissions` (donc avec `--dangerously-skip-permissions`) et aux sous-agents. Les hooks PreToolUse s'exécutent avant la demande de permission ; le mode bypass ne les désactive pas d'après la documentation, mais ce point n'est pas écrit explicitement.

**Syntaxe des motifs** (page officielle « Configure permissions », consultée sans date affichée).
- Les règles Bash font correspondre le texte de la commande ; `*` remplace n'importe quel texte. Exemples de la doc : `Bash(git * main)` correspond à `git push origin main` ; `Bash(git push *)` correspond à `git push origin main`.
- Un motif sans `*` est une correspondance exacte : `Bash(git push origin main)` ne couvre ni `git push -u origin main` ni `git push origin HEAD:main`.
- `Bash(ls *)` (avec espace) couvre aussi `ls` seul. `Bash(ls:*)` est dit « équivalent » à `Bash(ls *)`.
- Le suffixe `:*` n'est reconnu qu'en fin de motif. Dans `Bash(git:* push)`, le `:` est littéral et ne correspond à aucune commande git. Un `:` au milieu d'un argument, comme dans `HEAD:main`, est donc un caractère littéral dans un motif exact.
- Piège non vérifié : `Bash(git push origin HEAD:*)` se lit comme `git push origin HEAD` suivi d'un espace et de n'importe quoi ; il ne couvrirait probablement pas `HEAD:main`. À tester avant usage.

**Les trois cas demandés (inférence à partir des règles, non testée sur une version précise).**
- `git push origin main` : `Bash(git push *)` ou `Bash(git * main)`.
- `git push -u origin main` : `Bash(git push *)` ; `Bash(git * main)` le couvre aussi, car `*` remplace « push -u origin ».
- `git push origin HEAD:main` : `Bash(git push *)` le couvre. `Bash(git * main)` ne le couvre pas (la commande finit par `HEAD:main`, pas par ` main`).

**Limites documentées.** La doc indique que `Bash(git push *)` ne couvre pas `git -C . push origin main`, `git -c push.default=current push origin main` ni `git 'push' origin main`. La règle n'est donc pas une frontière de sécurité ; elle couvre la forme que Claude produit habituellement. Un hook PreToolUse peut inspecter le texte complet de la commande.

**Sous-agents.** La page « Subagents » indique qu'une règle `Bash(git push *)` dans `permissions.deny` « applies to the main conversation and to subagents ». Les sous-agents héritent des règles de permission de la conversation principale.

**Mode `bypassPermissions` et `--dangerously-skip-permissions`.**
- Page « Permission modes » : « Deny rules block in every mode, including `bypassPermissions`. ... Allow rules have no effect in `bypassPermissions`. »
- La même page indique que `--dangerously-skip-permissions` est équivalent à `--permission-mode bypassPermissions`.
- Les sous-agents exécutés dans la conversation principale en bypass sont aussi en bypass (page « Subagents »).

**Hooks PreToolUse en mode bypass.**
- Page « Configure permissions » : « PreToolUse hooks run before the permission prompt, for every tool except EndConversation. » Et : « PreToolUse hook decisions don't bypass permission rules. Claude Code evaluates deny and ask rules regardless of what a PreToolUse hook returns ».
- Page « Hooks reference » : le champ d'entrée `permission_mode` peut valoir `bypassPermissions`. Les hooks s'exécutent aussi dans les sous-agents.
- Ce qui n'est pas écrit explicitement : que les hooks tournent en bypass. La conclusion (ils tournent) reste une inférence forte à partir de « run before the permission prompt ». À vérifier sur la version installée.
- Contradiction signalée : une issue GitHub ancienne (Claude Code 2.0.36, d'après une source secondaire) rapporte qu'un Edit/Write malgré une règle deny. Non résolue dans les sources vues ; à prendre comme signal de vigilance, pas comme état actuel.
- Version : la doc cite des fonctionnalités à partir de v2.1.267 pour les sous-agents, v2.1.295 pour `onFailure` des hooks, v2.1.314 pour la correspondance Monitor.

**Niveau de confiance.** Élevé pour la syntaxe des motifs et pour « deny blocks in every mode, including bypassPermissions » (doc officielle lue). Moyen pour l'exécution des hooks en bypass (doc qui implique sans l'écrire). Faible pour le comportement exact de `Bash(git push origin HEAD:*)` (non testé).

**Sources.**
- [Configure permissions (Claude Code)](https://code.claude.com/docs/en/permissions), pas de date affichée ; versions citées jusqu'à v2.1.314.
- [Permission modes (Claude Code)](https://code.claude.com/docs/en/permission-modes.md), pas de date affichée.
- [Subagents (Claude Code)](https://code.claude.com/docs/en/sub-agents), pas de date affichée.
- [Hooks reference (Claude Code)](https://code.claude.com/docs/en/hooks), pas de date affichée.
- [Automate actions with hooks (guide)](https://code.claude.com/docs/en/hooks-guide.md), pas de date affichée (lu, sans précision sur le mode bypass).
- Note : la page « Agent SDK permissions » redirige vers `platform.claude.com/docs/en/agent-sdk/permissions` ; non lue en entier. Une source secondaire (recherche) décrit le même ordre : hooks, puis ask, puis deny, puis mode.

## 3. GitHub : fusion d'une PR et rulesets

**Réponse courte.** Pour la fusion via l'API `PUT /repos/{owner}/{repo}/pulls/{n}/merge`, la doc officielle des permissions des jetons à granularité fine classe cet endpoint sous « Contents » (écriture), et non sous « Pull requests » (écriture). Un auteur de PR ne peut pas approuver sa propre PR ; avec `required_approving_review_count = 1`, il faut donc un autre relecteur, sauf contournement. Un actor en `bypass_mode = "pull_request"` peut contourner les règles sur les PR, donc fusionner sans approbation, selon la doc de l'API des rulesets.

**Détails utiles.**
- Permissions du jeton : la page « permissions required for fine-grained personal access tokens » liste sous « Repository permissions for Contents » les entrées en écriture `PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge`, `.../merge-async` et `GET .../merge-async/{uuid}`. Sous « Pull requests », seul `GET .../pulls/{pull_number}/merge` apparaît (lecture). Conclusion : « Contents: write » est requis ; « Pull requests: write » seul ne figure pas pour cet endpoint dans la table. Non vérifié en appel réel. La recherche secondaire suggère de confirmer avec l'en-tête `X-Accepted-GitHub-Permissions`.
- Auteur de PR : la doc « Approving a pull request with required reviews » indique : « Pull request authors cannot approve their own pull requests. » Ce n'est pas une option de ruleset, c'est une règle de la plateforme.
- Admins et contournement : la même page dit « Repository owners and administrators can merge a pull request even if it hasn't received an approving review. » Cette phrase ne précise pas si elle vaut aussi pour les rulesets ; la mécanique de contournement est décrite par la doc des rulesets.
- Paramètre `require_last_push_approval` (doc REST des rulesets, version d'API 2026-03-10) : « Whether the most recent reviewable push must be approved by someone other than the person who pushed it. »
- Paramètre `required_approving_review_count` : entier de 0 à 10, « The number of approving reviews that are required before a pull request can be merged. »
- Bypass (doc REST des rulesets, `bypass_actors`) : `bypass_mode` vaut `always` (défaut), `pull_request` (« an actor can only bypass rules on pull requests »), ou `exempt` (« rules will not be run for that actor and a bypass audit entry will not be created »). `actor_type` : `Integration`, `OrganizationAdmin`, `RepositoryRole`, `Team`, `DeployKey`, `User`.
- Ce que la doc ne dit pas clairement : si un admin sans entrée dans `bypass_actors` peut fusionner une PR sans approbation quand une règle active s'applique. La doc « about rulesets » indique que le contournement se donne par rôle, équipe ou GitHub App ; l'effet pour un administrateur du dépôt n'a pas été confirmé.
- Piège signalé par une source secondaire (non officielle) : un bot de la liste de bypass pourrait toujours avoir besoin d'approbation en mode `active`, et pas en `evaluate`. Une seule source ; à ne pas considérer comme établi.

**Niveau de confiance.** Élevé pour l'interdiction d'auto-approbation (doc officielle), élevé pour les valeurs `bypass_mode` et les paramètres (doc REST, version 2026-03-10). Moyen pour la permission « Contents: write » seule (table officielle, mais pas d'appel réel). Faible pour le comportement exact d'un admin sans entrée de bypass, et pour le cas `bypass_mode = "pull_request"` appliqué à la fusion (déduit de la description, non testé).

**Sources.**
- [Permissions required for fine-grained personal access tokens (GitHub Docs)](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens), pas de date affichée.
- [Merge a pull request (GitHub REST API, pulls)](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request), version d'API affichée 2026-03-10 ; la section utile n'a pas été trouvée dans la capture.
- [Repository rules / rulesets (GitHub REST API)](https://docs.github.com/en/rest/repos/rules), version d'API 2026-03-10.
- [Approving a pull request with required reviews (GitHub Docs)](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/approving-a-pull-request-with-required-reviews), pas de date affichée.
- [About rulesets (GitHub Docs)](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets), pas de date affichée.
- [Available rules for rulesets (GitHub Docs)](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets), pas de date affichée.
- Non obtenu : la documentation du provider Terraform `github_repository_ruleset` (page du registre non lisible), donc les noms exacts des attributs `bypass_actors` côté Terraform restent à vérifier dans le provider installé.

## Incertitudes à lever

1. Version de Git installée : `git --version` non lancé (pas de shell dans cette recherche).
2. Date exacte de sortie de Git 2.41.0 (non confirmée par une source trouvée).
3. Comportement réel de `Bash(git push *)` et des motifs `:*` sur la version de Claude Code installée (aucun test effectué).
4. Exécution des hooks PreToolUse en mode bypass : doc implicite, pas de test.
5. Permission réelle requise pour `PUT .../merge` : table officielle lue, pas d'appel réel ni vérification de `X-Accepted-GitHub-Permissions`.
6. Effet du bypass `pull_request` sur un administrateur du dépôt dans la configuration actuelle (à tester sur le dépôt, ou à vérifier dans `infra/terraform/`).
