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

## 4. Ajout du 2026-11-07 (étape E10b)

- **Jeton à granularité fine et dépôt d'un autre compte personnel.** La page [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) (lue le 2026-11-07, pas de date affichée) limite un jeton à granularité fine à **un seul propriétaire de ressources** (« The token will only be able to access resources owned by the selected resource owner ») et liste parmi ses limites : « Using fine-grained personal access token to contribute to repositories where the user is an outside or repository collaborator ». Conséquence probable pour E10b : un compte machine collaborateur d'un dépôt **personnel** d'un autre compte ne peut pas créer de jeton à granularité fine pour ce dépôt, et doit utiliser un jeton classique (portée `repo`). **Non vérifié par un essai réel** ; confiance moyenne (la page parle d'« outside collaborator » et pas explicitement des dépôts personnels).
- **Attributs Terraform** (provider `integrations/github` installé, `terraform providers schema -json`, 2026-11-07) : `github_repository_collaborator` (`repository`, `username`, `permission` ; « Must be 'push' for personal repositories », défaut `push`) ; `github_repository_ruleset` règle `pull_request` : `required_approving_review_count`, `dismiss_stale_reviews_on_push`, `require_last_push_approval`, `required_review_thread_resolution`.

## 5. Ajout du 2026-11-07 : jetons, collaborateurs et fusion (recherche complémentaire E10b)

Méthode : pages officielles `docs.github.com` et `github.blog` lues le 2026-11-07 avec un outil de résumé. Les citations ci-dessous sont des extraits fournis par cet outil, à relire dans le texte source avant de les citer dans une décision. Sauf mention contraire, les pages n'affichent pas de date de dernière mise à jour.

### Question 1 : un jeton à granularité fine peut-il être limité au dépôt de A ?

**Réponse courte.** Non, d'après la doc officielle lue le 2026-11-07. Un jeton à granularité fine ne couvre qu'un seul propriétaire de ressources, et la doc liste comme non pris en charge la contribution à « des dépôts où l'utilisateur est un outside collaborator ou un repository collaborator ». Un compte B simple collaborateur (Write) sur un dépôt personnel de A ne peut donc pas obtenir un jeton à granularité fine capable d'écrire sur ce dépôt. La doc ne dit pas explicitement si A apparaît dans la liste « Resource owner » de B ; le comportement d'interface n'a pas été testé.

**Limites exactes (page « Managing your personal access tokens », extraits).**
- Liste des limites : « Fine-grained personal access tokens do not support every feature of personal access tokens (classic). » Puis, notamment : « Using fine-grained personal access token to contribute to public repos where the user is not a member. » ; « Using fine-grained personal access token to contribute to repositories where the user is an outside or repository collaborator. » ; « Using fine-grained personal access token to access multiple organizations at once. » ; Packages ; Checks API ; Projects de compte utilisateur.
- Propriétaire : « Each token is limited to access resources owned by a single user or organization. » et « Under Resource owner, select a resource owner. The token will only be able to access resources owned by the selected resource owner. »
- Collaborateurs externes (page « Permissions required for fine-grained personal access tokens », extrait) : « Outside collaborators can only use personal access tokens (classic) to access organization repositories that they are a collaborator on. » Cette phrase vise les dépôts d'organisation ; la limite générale ci-dessus couvre les dépôts personnels.
- Approbation d'organisation (non applicable à un dépôt de compte personnel) : un jeton reste « pending » tant qu'un administrateur ne l'a pas validé et ne peut lire que les ressources publiques.

**Évolution récente.**
- Changelog officiel du 2025-03-18, « Fine-grained PATs are now generally available » : la liste des lacunes restantes inclut « Contributing to repositories where you're an outside collaborator or an unaffiliated open source contributor ». Date vérifiée (lue directement).
- La doc lue le 2026-11-07 contient toujours la même limite.
- Aucune entrée de changelog 2025-2026 annonçant sa levée n'a été trouvée. Une recherche a remonté une doc Enterprise Server 3.15 (date non vue) qui citait aussi la limite ; une autre recherche a affirmé à tort que la liste actuelle ne la contenait plus. Cette contradiction est levée en faveur de la limite, car la page elle-même a été lue le 2026-11-07.

**Niveau de confiance.** Élevé que la limite existe à la date de consultation (doc officielle lue, plus changelog de 2025-03-18). Élevé que la doc ne prévoit pas d'exception pour les dépôts personnels. Faible sur l'absence de changement non publié ou non détecté entre 2025-03 et 2026-11. Le point « A dans la liste Resource owner de B » reste non testé. La note « confiance moyenne » de la section 4 peut être relevée à élevé pour la limite elle-même.

### Question 2 : alternatives si le jeton fin n'est pas possible

**(a) Jeton classique, portée `repo`.**
- Doc « Scopes for OAuth apps » (pas de date) : `repo` « Grants full access to public and private repositories ». `workflow` « Grants the ability to add and update GitHub Actions workflow files. » Une exception existe : un fichier de workflow identique (même chemin, même contenu) déjà présent sur une autre branche du même dépôt peut être committé sans cette portée.
- Ce que `repo` donne concrètement à B : l'accès à **tous** les dépôts auxquels B a accès, pas seulement celui de A. Le rôle de B sur le dépôt de A (Write) borne ce qu'il peut faire. La portée est un plafond, pas un filtre par dépôt.
- Fusion : un collaborateur Write peut « Create, merge, and close pull requests in the repository » (page [Permission levels for a personal account repository](https://docs.github.com/en/account-and-profile/reference/permission-levels-for-a-personal-account-repository), pas de date). Donc `repo` suffit à fusionner une PR dont les règles sont satisfaites.
- Modifier des workflows sans `workflow` : refusé par le push (sauf l'exception ci-dessus). Un compte qui ne fait que pousser sans `workflow` ne peut donc pas modifier `.github/workflows/` (doc de la portée ; non testé).
- Administrer (rulesets, paramètres) : la doc des rôles d'organisation réserve « Manage branch protection rules and repository rulesets » au rôle Admin ; la page des rôles de compte personnel ne le dit pas explicitement. Inférence : un Write ne gère pas les rulesets, la portée `repo` seule n'y change rien. Non vérifié.
- Confiance : élevé pour la portée `repo` et `workflow` (doc officielle). Moyen pour l'effet « plafond, pas filtre » (déduit de la doc des portées et des rôles). Faible pour la gestion des rulesets par un Write sur compte personnel.

**(b) GitHub App installée sur le seul dépôt.**
- Choix du périmètre : « the user or organization owner who installed the app can decide what repositories the app can access » (page [Deciding when to build a GitHub App](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/deciding-when-to-build-a-github-app), pas de date). A installe l'app sur son compte et ne sélectionne que son dépôt. Un jeton d'installation peut être restreint à ce dépôt via les paramètres `repositories` ou `repository_ids` (page [Authenticating as a GitHub App installation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation), pas de date).
- Durée : « The installation access token will expire after 1 hour. »
- Identité : « API requests made by an app installation are attributed to the app. » Les PR créées sont donc attribuées au bot, pas à un compte humain.
- Permissions (page [Permissions required for GitHub Apps](https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps), pas de version affichée) : `PUT .../pulls/{pull_number}/merge` relève de « Repository permissions for Contents » en écriture ; `POST .../pulls` relève de « Pull requests » en écriture ; les rulesets en écriture relèvent de « Administration ». Donc, pour pousser, ouvrir une PR et fusionner, l'app a besoin de Contents: write et Pull requests: write. Les permissions pour gérer les rulesets (Administration: write) ne sont pas nécessaires au flux PR.
- Contournement du ruleset : une app est un acteur `Integration` (doc REST rulesets, version 2026-03-10). Elle ne contourne les règles que si elle figure dans `bypass_actors`. Sans entrée, le ruleset s'applique. Avec `bypass_mode = "pull_request"`, le contournement ne vaut que pour les règles sur les PR ; avec `exempt`, les règles ne sont plus exécutées pour cet acteur et aucune entrée d'audit n'est créée. Les paramètres de bypass sont donc à choisir explicitement ; le choix n'est pas fait ici.
- `required_approving_review_count` : une approbation venant d'une autre personne reste exigée, qu'il y ait une app ou non. La doc interdit seulement à l'auteur d'approuver sa propre PR ; le propriétaire A, qui approuve une PR ouverte par le bot, est une autre personne. Inférence : le nombre d'approbations requis n'a pas à changer. Non vérifié sur un dépôt réel : la doc ne dit pas explicitement qu'une PR créée par une app est traitée comme une PR de compte humain pour les approbations.
- Limites : une app tierce ou créée par A demande la création de l'app (non détaillée ici). Les jetons d'installation expirent après 1 heure, donc un script doit les renouveler. La doc « Deciding when » recommande l'app plutôt qu'un PAT pour les intégrations de longue durée, et les PAT pour les tests et scripts courts.
- Confiance : élevé pour l'installation par dépôt, l'expiration d'une heure, l'attribution au bot et les rubriques de permission. Moyen pour l'absence de contournement sans entrée de bypass (déduit de la doc des rulesets). Moyen pour l'effet sur `required_approving_review_count` (inférence). Faible sur l'effet exact des valeurs `bypass_mode` appliquées à une app (non testé).

**(c) Clé de déploiement SSH.**
- Doc « Managing deploy keys » (pas de date) : « Deploy keys only grant access to a single repository. » ; « Deploy keys are read-only by default, but you can give them write access when adding them to a repository. » ; « A deploy key with write access lets a deployment push to the repository. » ; « Deploy keys with write access can perform the same actions as an organization member with admin access. » ; « Deploy keys are credentials that don't have an expiry date. »
- Limite pour E10b : la doc ne dit pas qu'une clé de déploiement peut ouvrir une PR ou appeler l'API. Inférence forte : une clé SSH sert au transport Git, pas à l'API REST. Donc pas de PR, pas de fusion via API, à moins d'un autre jeton.
- Point de vigilance : la clé de déploiement avec écriture est décrite comme pouvant faire autant qu'un membre admin, et elle n'expire pas. Pour un dépôt personnel, la phrase « admin » ne se transpose pas forcément ; à lire comme un avertissement.
- Bypass : `DeployKey` existe comme `actor_type`, mais `bypass_mode = "pull_request"` ne s'applique pas aux clés de déploiement (doc REST rulesets).
- Confiance : élevé pour les permissions et l'absence d'expiration (doc lue). Moyen pour « pas de PR » (inférence sur ce que la doc ne dit pas).

**(d) Organisation gratuite.**
- Si le dépôt appartient à une organisation, la limite « outside collaborator » ne s'applique plus au compte machine s'il en est **membre** avec un rôle Write (la limite vise les collaborateurs externes ; un membre n'en est pas un). Inférence à partir de la définition de la doc ; non testé.
- Rôles d'organisation (page [Repository roles for an organization](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization), pas de date) : Write peut fusionner une PR ; « Manage branch protection rules and repository rulesets » est réservé à Admin.
- Fine-grained tokens pour une org : le propriétaire peut exiger une approbation, et le jeton reste « pending » jusqu'à validation.
- Rulesets : `actor_type = OrganizationAdmin` n'est pas applicable aux dépôts personnels (doc REST rulesets) ; il existe donc seulement pour une organisation.
- Non vérifié : les conditions de plan (gratuit ou non) pour les rulesets sur dépôt privé ou public. Le dépôt est public, donc a priori sans obstacle, mais la doc de tarification n'a pas été lue.
- Confiance : élevé pour les rôles et la limite « outside collaborator ». Moyen pour l'effet « membre et non collaborateur externe ». Faible pour les plans.

### Question 3 : une PR approuvée par A peut-elle être fusionnée par un compte Write ? Peut-on l'en empêcher autrement que par le ruleset ?

**Réponse courte.** Oui : un compte Write peut fusionner une PR, et une approbation de A satisfait `required_approving_review_count`. La doc ne fournit pas de réglage qui retire à un Write seul la permission de fusion tout en lui laissant le push : fusion et écriture vont ensemble. Le levier documenté est le ruleset (approbations, dernier push approuvé par un autre, liste de bypass).

**Détails.**
- Fusion par Write : « Create, merge, and close pull requests in the repository » (page permission levels pour compte personnel, pas de date). Rôles d'organisation : « Merge a pull request » autorisé pour Write, Maintain et Admin, pas pour Read ni Triage (page organisation).
- Approbation de A : rien dans les pages lues n'empêche un Write de fusionner une PR approuvée par un autre. Donc si le ruleset est satisfait, le compte machine peut fusionner.
- Pour que la fusion par le bot soit conditionnée à une relecture : `require_last_push_approval` (doc REST rulesets, 2026-03-10) : « Whether the most recent reviewable push must be approved by someone other than the person who pushed it. » Si le bot pousse un commit après l'approbation de A, A doit réapprouver. `dismiss_stale_reviews_on_push` complète le dispositif (attributs Terraform vus le 2026-11-07, voir section 4).
- Empêcher la fusion autrement : la permission « Contents: write » est exigée pour `PUT .../merge` (table des permissions d'app et de jeton fin). Une app qui peut pousser peut donc fusionner. Il n'a pas été trouvé de permission séparée « merge » qu'on pourrait ne pas accorder. Les seuls leviers documentés sont : ne pas mettre le compte dans `bypass_actors`, exiger des approbations, exiger que le dernier push soit approuvé, et exiger une PR (pas de push direct sur la branche protégée).
- Piège : l'approbation ne prouve que la relecture humaine ; si le bot est dans `bypass_actors` avec `bypass_mode = "pull_request"` ou `exempt`, l'approbation n'est plus exigée pour ce bot (doc REST rulesets). Une source secondaire évoque un comportement différent entre les modes `evaluate` et `active` ; non confirmé.

**Niveau de confiance.** Élevé pour : le Write peut fusionner (doc officielle, deux pages), `require_last_push_approval` (doc REST), `bypass_mode` (doc REST), la permission Contents pour la fusion (table officielle). Moyen pour l'absence de réglage de fusion séparé (absence trouvée dans les pages lues, pas exhaustive). Faible pour le comportement de `evaluate` contre `active` (source secondaire).

### Sources de la section 5

- [Managing your personal access tokens (GitHub Docs)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens), lu le 2026-11-07, pas de date affichée.
- [Permissions required for fine-grained personal access tokens (GitHub Docs)](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens), lu le 2026-11-07, pas de date affichée.
- [Permissions required for GitHub Apps (GitHub Docs)](https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps), lu le 2026-11-07, pas de version affichée.
- [Fine-grained PATs are now generally available (GitHub Changelog)](https://github.blog/changelog/2025-03-18-fine-grained-pats-are-now-generally-available/), 2025-03-18.
- [Scopes for OAuth apps (GitHub Docs)](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps), lu le 2026-11-07, pas de date affichée.
- [Deciding when to build a GitHub App (GitHub Docs)](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/deciding-when-to-build-a-github-app), lu le 2026-11-07, pas de date affichée.
- [Authenticating as a GitHub App installation (GitHub Docs)](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation), lu le 2026-11-07, pas de date affichée.
- [Managing deploy keys (GitHub Docs)](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys), lu le 2026-11-07, pas de date affichée.
- [Approving a pull request with required reviews (GitHub Docs)](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/approving-a-pull-request-with-required-reviews), lu le 2026-11-07, pas de date affichée.
- [About rulesets (GitHub Docs)](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets), lu le 2026-11-07, pas de date affichée.
- [REST API : repository rules (GitHub Docs)](https://docs.github.com/en/rest/repos/rules), version d'API 2026-03-10.
- [Repository roles for an organization (GitHub Docs)](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization), lu le 2026-11-07, pas de date affichée.
- [Permission levels for a personal account repository (GitHub Docs)](https://docs.github.com/en/account-and-profile/reference/permission-levels-for-a-personal-account-repository), lu le 2026-11-07, pas de date affichée.
- Secondaire, non retenue comme base : résultats de recherche renvoyant des pages Enterprise Server 3.12, 3.13 et 3.15 (versions anciennes ou de dates non vues), utilisées seulement pour signaler la limite « outside collaborator » déjà présente dans la doc GitHub.com.

### Incertitudes restantes (section 5)

1. Comportement réel de l'interface pour B : A apparaît-il dans « Resource owner » ? À tester avec un compte test.
2. Effet exact de `repo` sur un compte Write sans `workflow` : la doc des sous-portées de `repo` n'a pas été lue en détail.
3. Gestion des rulesets par un Write sur compte personnel : non dite explicitement dans la page lue.
4. Approbation d'une PR créée par une GitHub App : comptée comme une PR humaine ? Non vérifié.
5. Effet de `bypass_mode` sur une app et sur un administrateur de compte personnel : non testé ; la doc ne dit pas si le propriétaire du dépôt est contourné par défaut.
6. Conditions de plan pour les rulesets et les apps sur compte gratuit : non lues.
7. Absence de changement entre 2025-03 et 2026-11 : pas de changelog 2025-2026 trouvé sur le sujet ; la doc lue le 2026-11-07 reste la référence.
</content>
