# Compte machine des agents

*Mise à jour : 2026-11-07 (création, étape E10b du plan PP, décision [0021](../decisions/0021-fusion-compte-machine-agents.md) ; révisée après la revue d'architecte : revue du propriétaire du code (CODEOWNERS), ordre des étapes, environnement nettoyé, limites ; jeton classique à portée `repo` : [0024](../decisions/0024-jeton-compte-machine-classique.md) ; règle « seul l'utilisateur fusionne » : [0013](../decisions/0013-identite-agents-fusion.md) ; revue du propriétaire du code : [0025](../decisions/0025-barriere-serveur-codeowners.md) ; isolement dans Claudeus : [0026](../decisions/0026-isolement-identifiants-claudeus.md) ; jamais la portée `workflow` : [0027](../decisions/0027-portee-workflow-jamais.md) ; garde-fou sur les identifiants : [0028](../decisions/0028-garde-bash-identifiants-github.md) ; sandbox reporté après PP : [0015](../decisions/0015-sandbox-reporte-apres-pp.md))*

Procédure **pour l'utilisateur** : créer le compte machine des agents, l'inviter sur le dépôt, lui donner un jeton, vérifier la barrière de fusion. Les agents ne font rien de cela (`terraform apply` leur est interdit, et ils n'ont pas accès au compte). Le circuit des agents est décrit dans [`circuit-git.md`](circuit-git.md) ; Terraform dans [`ci-cd.md`](ci-cd.md).

## Ce que cela change

- **Avant (E10)** : les agents utilisent le jeton U5 du compte propriétaire. Le ruleset exige 0 approbation : rien côté serveur n'empêche un agent de fusionner (seuls le hook local et la discipline des agents s'y opposent).
- **Après (E10b)** : les agents utilisent un **compte GitHub distinct** (rôle *Write* sur le dépôt, jamais administrateur). Le ruleset de la branche par défaut exige **1 approbation d'un propriétaire du code** (`required_approving_review_count = 1`, `require_code_owner_review = true`, fichier [`.github/CODEOWNERS`](../../.github/CODEOWNERS) : `* @p3bri4n`). Le compte machine :
  - n'a **pas** de contournement du ruleset (seul le rôle *admin* en a un, en mode `pull_request`) ;
  - **ne peut pas approuver sa propre pull request** (règle de GitHub) ;
  - n'est **pas propriétaire du code** : ses approbations, sur n'importe quelle pull request, **ne comptent pas** ;
  - ne peut donc pas fusionner une pull request tant que le propriétaire ne l'a pas approuvée ou fusionnée par contournement.

Particularités de cette barrière :

- **Les pull requests du propriétaire** ne se fusionnent que par le **contournement** : il ne peut pas approuver la sienne, et personne d'autre n'est propriétaire du code. C'est le comportement voulu.
- Une fois la pull request approuvée par le propriétaire et les contrôles verts, la fusion est ouverte à **tout compte avec le rôle *Write***, le compte machine compris. Le propriétaire n'approuve donc **qu'au moment de fusionner** : il ne doit **jamais** approuver une pull request d'agent sans la fusionner dans la foulée (fusion par contournement sans approbation, ou approbation immédiatement suivie de la fusion).
- Le ruleset active `dismiss_stale_reviews_on_push` et `require_last_push_approval` : un push après l'approbation la périme, et le dernier push doit être approuvé par un autre que son auteur. Ce n'est pas un substitut à la relecture : le propriétaire relit avant de fusionner.
- Le rôle *Write* permet de lancer à la main un workflow (`workflow_dispatch`) : `gpu-eval.yml` s'en protège par `github.repository_owner == github.actor` (le compte machine est refusé), mais tout nouveau workflow manuel doit avoir la même garde.

## Limites (à lire avant de s'y fier)

**Sur l'hôte, la barrière ne protège que contre l'erreur d'un agent, pas contre un agent qui chercherait à la contourner.**

- Les agents s'exécutent aujourd'hui sous **le même compte Unix que l'utilisateur**. Les identifiants du propriétaire restent donc **à portée** : la connexion `gh` (`~/.config/gh/hosts.yml`, ou le trousseau), la clé SSH (`~/.ssh`, agent SSH), un `GITHUB_TOKEN` d'administration resté dans le shell, `infra/terraform/terraform.tfvars` et l'état Terraform. Un agent qui les lit peut agir comme le propriétaire, approuver et fusionner.
- Le garde-fou Bash ([`garde-fous-bash.md`](garde-fous-bash.md)) refuse `gh auth token`, `gh auth login`, l'affectation ou le retrait de `GH_TOKEN` et `GITHUB_TOKEN`, etc. C'est un **palliatif partiel** : il ne voit ni `curl`, ni la lecture directe d'un fichier, ni un script, ni un programme tiers.
- **Cible (décision de l'utilisateur) : les agents ne tournent que dans Claudeus**, un conteneur sans `~/.config/gh` ni `~/.ssh`, avec le seul `GH_TOKEN` du compte machine injecté. Dans ce cadre la barrière est réelle : l'agent n'a aucun identifiant du propriétaire à utiliser. Le sandbox est reporté après PP ([0015](../decisions/0015-sandbox-reporte-apres-pp.md)) ; en attendant l'adaptation de Claudeus, les mesures **intérimaires sur l'hôte** sont : un environnement nettoyé au lancement (étape (f)), l'avertissement du hook `SessionStart` et le garde-fou Bash.
- Le rôle *Write* donne aussi au compte machine, en plus des branches et des pull requests : la création de **tags et de releases publics**, le **push forcé sur d'autres branches que la branche par défaut** (le ruleset ne protège que celle-ci ; le garde-fou Bash refuse le push forcé, mais pas un `curl`), et la **résolution des conversations** de revue (le ruleset exige qu'elles soient résolues : un agent peut résoudre celles qu'un relecteur a ouvertes). Aucune de ces actions ne fusionne dans la branche par défaut.
- Le jeton **n'a jamais la portée `workflow`** (voir (e)). Un agent qui doit modifier `.github/workflows/` prépare le changement et le fournit à l'utilisateur, qui le pousse lui-même avec son propre compte ([0027](../decisions/0027-portee-workflow-jamais.md)). La recherche signale une exception de GitHub (fichier identique déjà présent sur une autre branche) : non testée, elle ne change pas cette règle.

## Procédure

Ordre des opérations : l'étape 0 et les étapes (a) à (e) ne changent rien pour les agents ; le ruleset à approbation ne s'applique qu'après la fusion de la pull request E10b (étape (c)). Voir (c) pour la raison.

### (0) Avant E10b : le plan Terraform doit être propre

Sur `main` à jour, **avant** de fusionner la pull request E10b, depuis un shell de l'utilisateur :

```bash
export GITHUB_TOKEN=...     # jeton d'administration, voir ci-cd.md
just tf-plan
```

Le plan doit annoncer **zéro changement** (« No changes »). S'il annonce une dérive :

- si elle est **légitime** (un réglage changé volontairement sur GitHub, une valeur que Terraform ne devrait pas toucher) : la comprendre, puis soit l'intégrer dans les fichiers `.tf` par une pull request séparée, soit la laisser et le noter dans le journal ; ne pas poursuivre tant que l'on ne sait pas l'expliquer ;
- si elle est **inexpliquée** : ne rien appliquer, la signaler à l'architecte. Une dérive inexpliquée est un signal de sécurité (réglage modifié hors Terraform).

Ne jamais enchaîner sur (c) avec un plan qui contient autre chose que ce qui est décrit plus bas.

### (a) Créer le compte machine GitHub

- Les conditions d'utilisation de GitHub permettent **un compte machine gratuit** (« machine account ») par personne, à condition qu'il soit créé par une personne (pas par un script) et que son propriétaire en reste responsable. À relire sur les conditions en vigueur au moment de la création.
- Utiliser une **adresse e-mail dédiée ou un alias** (pas l'adresse du compte propriétaire) et un mot de passe unique.
- Activer l'**authentification à deux facteurs** (application d'authentification ; garder les codes de récupération hors du dépôt).
- Choisir un identifiant explicite, par exemple `ntl-agents`. Ne rien d'autre n'est accordé à ce compte : **aucun autre dépôt, aucune organisation**.

### (b) Renseigner `agents_account` dans `terraform.tfvars`

Dans `infra/terraform/terraform.tfvars` (ignoré par Git), voir l'exemple dans `terraform.tfvars.example` :

```hcl
agents_account = "ntl-agents"
```

Vide (valeur par défaut) = aucun compte invité. La valeur doit être un identifiant GitHub valide et différent du propriétaire (contrôlé par Terraform).

### (c) Fusionner E10b, puis appliquer (utilisateur seul)

**L'ordre compte.** Tant que le ruleset exige 0 approbation, la pull request E10b elle-même se fusionne normalement. Si l'on appliquait le ruleset à une approbation **avant** de la fusionner, ce serait la barrière qu'elle introduit qui bloquerait sa propre fusion (et il faudrait passer par le contournement). Donc :

1. **Fusionner la pull request E10b** (le ruleset est encore à 0 approbation : fusion ordinaire, par l'utilisateur).
2. Mettre `main` à jour localement : `git switch main && git pull --ff-only origin main`.
3. Depuis `main` à jour, avec `agents_account` renseigné (b) :

   ```bash
   export GITHUB_TOKEN=...     # jeton d'administration, voir ci-cd.md
   just tf-plan                # à relire
   just tf-apply               # réservé à l'utilisateur
   ```

Le plan doit montrer exactement :

- `github_repository_collaborator.agents[0]` créé (`+`), avec `permission = "push"` ;
- `github_repository_ruleset.default_branch` **modifié en place** (`~`) : `required_approving_review_count` de `0` à `1`, `require_last_push_approval` et `require_code_owner_review` à `true`. Rien d'autre, et **aucun changement de `bypass_actors`**.

Si le ruleset apparaît **remplacé** (`-/+`, « must be replaced ») ou si les `bypass_actors` changent, ne pas appliquer : un remplacement ouvre une fenêtre sans protection. Si le plan montre autre chose, ne pas appliquer non plus. `tf-apply` envoie l'invitation (le dépôt est personnel : le provider impose `push`).

### (d) Accepter l'invitation depuis le compte machine

Connecté **au compte machine** (navigateur séparé ou fenêtre privée) : ouvrir l'invitation reçue par e-mail, ou `https://github.com/<propriétaire>/nothing-to-lose/invitations`, puis l'accepter. L'invitation expire au bout de 7 jours ; `terraform apply` la renvoie si besoin. Tant qu'elle n'est pas acceptée, `just verify-pp merge-barrier` signale un rôle `read`/`none`.

### (e) Créer le jeton du compte machine

Connecté au compte machine : *Settings → Developer settings → Personal access tokens*.

Le jeton est un **jeton classique** (*Tokens (classic)*), et non à granularité fine : décision [0024](../decisions/0024-jeton-compte-machine-classique.md), qui précise [0021](../decisions/0021-fusion-compte-machine-agents.md). La raison : un jeton à granularité fine ne peut pas viser un dépôt personnel dont le compte est seulement collaborateur ([note de recherche, §5](../recherches/2026-11-07-garde-fous-git-gh.md)).

Réglages à cocher, et rien d'autre :

- **Note** : `nothing-to-lose agents` (libellé libre) ;
- **Expiration** : 30 jours (durée courte ; noter la date de renouvellement) ;
- **Portées** : `repo` **seulement**. **Jamais `workflow`** (décision de l'utilisateur) : un jeton qui peut modifier `.github/workflows/` permettrait à un agent de réécrire `ci.yml` (le check obligatoire) ou de créer un workflow qui s'exécute avec les secrets du dépôt. L'agent prépare le changement de workflow, l'**utilisateur le pousse** avec son propre compte. Jamais non plus `admin:*`, `delete_repo`, `write:packages`, `user`, `gist`, ni aucune autre portée.

La portée `repo` est un **plafond** sur tous les dépôts auxquels le compte a accès, pas un filtre sur ce dépôt. C'est acceptable **uniquement parce que** le compte machine n'a accès à aucun autre dépôt ni organisation (voir (a)), que son rôle sur celui-ci est *Write*, pas *admin*, et qu'il ne sert à rien d'autre que les agents de ce dépôt. Ne jamais inviter ce compte ailleurs.

La règle « jamais *Actions* en écriture » ne peut pas être appliquée par le jeton lui-même (un jeton classique n'a pas cette granularité). La protection de `gpu-eval.yml` repose sur sa garde `github.repository_owner == github.actor` (voir plus haut) et sur le rôle *Write* du compte, qui ne gère pas les paramètres du dépôt (inférence de la recherche, non testée).

Copier le jeton une seule fois, directement dans le fichier de l'étape suivante.

**Dès que le jeton du compte machine est créé et vérifié** (`env -u GH_TOKEN gh auth status` échoue, `gh api user --jq .login` affiche le compte machine, voir (f)), **révoquer l'ancien jeton U5** du compte propriétaire : *Developer settings → Personal access tokens*, bouton *Delete*. Ne pas attendre la fin de la procédure : tant qu'il existe, un agent qui le retrouve contourne tout. Retirer aussi le `GH_TOKEN` du propriétaire de tous les anciens fichiers `agents.env`, profils de shell et de la configuration de Claudeus.

### (f) Ranger le jeton et lancer Claude Code avec un environnement nettoyé

```bash
mkdir -p ~/.config/nothing-to-lose
umask 077
printf 'GH_TOKEN=%s\n' '<jeton>' > ~/.config/nothing-to-lose/agents.env
chmod 600 ~/.config/nothing-to-lose/agents.env
```

Lancer Claude Code dans un sous-shell qui **retire** les variables d'identité du propriétaire puis charge le fichier (rien ne reste dans le shell de l'utilisateur) :

```bash
( unset GITHUB_TOKEN GH_ENTERPRISE_TOKEN GITHUB_ENTERPRISE_TOKEN SSH_AUTH_SOCK; set -a; . ~/.config/nothing-to-lose/agents.env; set +a; exec claude )
```

`GITHUB_TOKEN` (jeton d'administration de Terraform) ne doit pas être présent du tout : `gh` lit `GH_TOKEN` en premier, mais le jeton d'administration n'a rien à faire dans l'environnement des agents. `SSH_AUTH_SOCK` retiré évite que l'agent SSH du propriétaire serve à pousser.

**Vérification** dans l'environnement des agents (le hook `SessionStart` avertit déjà si `GITHUB_TOKEN` est présent ou `GH_TOKEN` absent) :

```bash
env -u GH_TOKEN gh auth status     # doit ÉCHOUER : aucune connexion gh stockée ne doit rester derrière GH_TOKEN
gh api user --jq .login            # doit afficher le compte machine
```

Si la première commande réussit, `gh` dispose d'une connexion stockée (`~/.config/gh`, celle du propriétaire sur l'hôte) : un agent qui retire `GH_TOKEN` retombe sur elle. C'est la limite de l'hôte décrite plus haut ; dans Claudeus cette commande échoue.

Points d'attention :

- **Les agents doivent pousser avec l'identité du compte machine, pas avec la clé SSH du propriétaire.** Si le `remote` est en SSH (cas du premier `push`, voir [`ci-cd.md`](ci-cd.md)), les branches seraient poussées par le propriétaire : il serait alors « auteur du dernier push », ne pourrait plus approuver (`require_last_push_approval`) et devrait toujours passer par le contournement. Utiliser un `remote` HTTPS et l'assistant d'identification de `gh`, qui lit `GH_TOKEN` : `git remote set-url origin https://github.com/<propriétaire>/nothing-to-lose.git` et `gh auth setup-git` (action locale de l'utilisateur ; **non vérifiée**, à contrôler avec l'essai (h) : l'auteur du push doit être le compte machine). Dans un conteneur sans clé SSH du propriétaire, le problème ne se pose pas.
- **`gh auth setup-git` écrit dans la configuration globale (`~/.gitconfig`)** : l'assistant d'identification de `gh` s'applique alors aussi aux `git push` HTTPS de l'**utilisateur**, hors des agents. Si `GH_TOKEN` n'est pas défini dans son shell, `gh` se rabat sur sa connexion stockée : l'effet est inoffensif, mais à savoir. Pour l'éviter, utiliser une configuration locale au dépôt à la place (`git config --local credential.https://github.com.helper '!gh auth git-credential'`, **non vérifiée**).
- Configurer l'identité Git des commits (`user.name`, `user.email`) à la guise de l'utilisateur ; GitHub fonde ses règles sur le compte qui pousse, pas sur cette identité.

### (g) Vérifier la barrière côté serveur

Depuis un shell **de l'utilisateur** (avec son jeton, pas celui des agents) :

```bash
just verify-pp merge-barrier --agents-account ntl-agents
# ou : AGENTS_ACCOUNT=ntl-agents just verify-pp merge-barrier
```

Lecture seule (requêtes `GET` via `gh api`). Contrôles, sur les rulesets de la branche par défaut qui exigent une approbation : approbations ≥ 1 ; approbations périmées écartées (`dismiss_stale_reviews_on_push` ou `require_last_push_approval`) ; `require_code_owner_review` actif ; **liste blanche stricte** des acteurs de contournement (le seul accepté : rôle *admin* en mode `pull_request`, les modes `always` et `exempt` échouent) ; présence de `.github/CODEOWNERS` ; rôle du compte machine = `write` (pas `admin`, pas `maintain` ; un rôle `read`/`none` suggère une invitation non acceptée). Codes de retour : `0` tout passe, `1` un contrôle échoue, `3` contrôle impossible (jeton sans droit de lecture : la sortie le dit). Détails : [`outillage.md`](outillage.md).

### (h) Essais avant de s'y fier

1. Faire ouvrir par un agent une pull request triviale (changement de documentation), checks verts, conversations résolues.
2. Vérifier l'état : `gh pr view <n> --json mergeStateStatus,reviewDecision,author` doit montrer l'auteur `ntl-agents`, `reviewDecision = REVIEW_REQUIRED` et `mergeStateStatus = BLOCKED` (API REST : `mergeable_state = "blocked"`). **Non vérifié** : la valeur de `mergeStateStatus` peut dépendre de qui la lit, le propriétaire (qui peut contourner) pouvant voir un autre état que le compte machine ; la lire avec le jeton du compte machine.
3. **Essai négatif.** Avant de le faire, vérifier que **l'approbation est la seule exigence manquante** : CI verte (`ci-cpu`), branche à jour avec `main`, conversations résolues. Sinon le refus ne prouverait rien (il pourrait venir d'une autre règle). Puis, depuis un shell de l'utilisateur avec le jeton du compte machine : `GH_TOKEN=$(...) gh api -X PUT repos/<propriétaire>/nothing-to-lose/pulls/<n>/merge -f merge_method=squash` doit être **refusé** (405), et le **message d'erreur doit mentionner la revue** (« review »/« approving review is required »). Un autre message (CI, branche) invalide l'essai : corriger la cause et recommencer. Si la requête réussissait, la barrière est défaillante : la PR serait fusionnée (sans danger si elle est triviale), puis signaler le défaut (ne pas continuer l'usage des agents sur ce dépôt).
4. L'utilisateur fusionne : soit en contournant (case « merge without waiting for requirements » / `gh pr merge --admin --squash <n>` avec **son** jeton), soit en approuvant puis en fusionnant.
5. **Essai du contournement administrateur** sur une PR triviale **avant de s'y fier** : ouvrir une pull request triviale **du propriétaire** (elle ne peut pas être approuvée), vérifier qu'elle est bloquée, puis la fusionner par contournement. **Non vérifié** : le comportement exact du contournement `pull_request` pour un administrateur (bouton, `--admin`, API) sur ce dépôt. **Voie de secours** si le contournement ne fonctionne pas : le propriétaire ne doit pas rester bloqué ; repasser **temporairement** `required_approving_review_count` à `0` dans `ruleset.tf` par Terraform (`tf-plan`, puis `tf-apply` par l'utilisateur), fusionner, puis rétablir. C'est une décision structurante, à noter dans le journal.
6. Contrôler au passage, sur la page de la PR ou dans l'onglet *Commits*, que le push de la branche vient bien du compte machine (voir (f)).

### (i) Conséquences pratiques

- Les **pull requests des agents sont ouvertes par le compte machine** (auteur ≠ propriétaire). Leurs branches sont poussées par ce compte.
- L'**utilisateur** les approuve (au moment de fusionner) ou les fusionne en **contournant** le ruleset. Il reste seul à fusionner (D8, [0013](../decisions/0013-identite-agents-fusion.md)).
- Les **propres pull requests de l'utilisateur** : il ne peut pas approuver la sienne et personne d'autre n'est propriétaire du code ; elles passent par le **contournement** (`bypass_mode = "pull_request"`, rôle *admin*). C'est le comportement voulu.
- Les `issues` et commentaires créés par les agents apparaissent sous le nom du compte machine.
- Un changement de **workflow** (`.github/workflows/`) ne peut pas être poussé par le compte machine (pas de portée `workflow`) : l'agent prépare le changement, l'utilisateur le pousse.
- Renouveler le jeton avant son expiration (étape (e), puis mettre à jour `agents.env`) ; un jeton expiré se traduit par des erreurs `401` de `gh` côté agents.

## Annulation

Mettre `agents_account = ""` puis `just tf-plan` / `just tf-apply` retire le compte machine du dépôt (le compte GitHub lui-même n'est pas supprimé). Remettre `required_approving_review_count = 0` (ou `require_code_owner_review = false`) dans `ruleset.tf` relâche la barrière : c'est une décision structurante, à poser à l'utilisateur.

## Points non vérifiés

Ce qui n'a pas pu être contrôlé lors de l'écriture de cette page (aucun compte machine n'existe encore, `terraform apply` n'a pas été lancé) :

- que `terraform plan` produit exactement le changement décrit en (c) (le jeton disponible lors de l'implémentation n'avait pas les droits d'administration, le plan n'a pas pu aller au bout ; seuls `terraform validate` et le schéma du provider ont été contrôlés) ; en particulier que le ruleset est modifié en place et non remplacé ;
- que `require_code_owner_review` se comporte comme décrit avec un `CODEOWNERS` `* @p3bri4n` (le compte machine ne compte pas, le propriétaire peut contourner pour ses propres pull requests) ;
- la limite des jetons à granularité fine sur un dépôt personnel est documentée par GitHub (recherche §5, confiance élevée) mais n'a pas été testée sur ce dépôt ; c'est elle qui fonde le choix du jeton classique ([0024](../decisions/0024-jeton-compte-machine-classique.md)) ;
- le comportement exact du contournement `pull_request` pour l'administrateur (bouton, `--admin`, API de fusion) ;
- que l'API de fusion refuse bien le compte machine tant que la PR n'est pas approuvée, avec un message qui mentionne la revue (essai (h).3) ;
- la valeur de `mergeStateStatus` selon le lecteur ;
- l'identité du push avec un `remote` HTTPS et `gh auth setup-git`, et la variante de configuration locale au dépôt ;
- que le jeton classique sans portée `workflow` est bien refusé par GitHub quand il pousse un fichier de `.github/workflows/` (comportement documenté, non essayé ici).

## Liens

- Décisions : [0021](../decisions/0021-fusion-compte-machine-agents.md), [0025](../decisions/0025-barriere-serveur-codeowners.md) (CODEOWNERS), [0026](../decisions/0026-isolement-identifiants-claudeus.md) (Claudeus), [0027](../decisions/0027-portee-workflow-jamais.md) (pas de portée `workflow`), [0028](../decisions/0028-garde-bash-identifiants-github.md) (garde-fou), [0024](../decisions/0024-jeton-compte-machine-classique.md) (jeton classique à portée `repo`), [0013](../decisions/0013-identite-agents-fusion.md), [0015](../decisions/0015-sandbox-reporte-apres-pp.md) (sandbox reporté).
- Plan : [`../plans/PP.md`](../plans/PP.md) §E10, E10b, U5, D8.
- Circuit des agents : [`circuit-git.md`](circuit-git.md). Garde-fou Bash et défense en profondeur : [`garde-fous-bash.md`](garde-fous-bash.md). Terraform : [`ci-cd.md`](ci-cd.md). Vérification : [`outillage.md`](outillage.md).
- Recherche : [`../recherches/2026-11-07-garde-fous-git-gh.md`](../recherches/2026-11-07-garde-fous-git-gh.md).
