# 0026 — Isolement des identifiants du propriétaire : agents dans Claudeus

- **Date** : 2026-11-07
- **Statut** : décidée
- **Contexte** : sur l'hôte, les agents tournent sous le même compte Unix que l'utilisateur. Les identifiants du propriétaire sont donc à leur portée : connexion `gh`, clé SSH, `GITHUB_TOKEN` d'administration (Terraform), `terraform.tfvars`. Un agent qui cherche ces identifiants peut les trouver, indépendamment des règles du garde-fou Bash. Le sandbox a été reporté après PP ([0015](0015-sandbox-reporte-apres-pp.md)).
- **Options présentées** :
  1. Option (a) : agents seulement dans Claudeus. Le conteneur n'a ni `~/.config/gh` ni `~/.ssh` ; le `GH_TOKEN` du compte machine est injecté. Avantage : isolement réel des identifiants du propriétaire. Inconvénient : dépend de l'adaptation de Claudeus, qui n'est pas datée.
  2. Option (b) : utilisateur Unix dédié aux agents, qui ne peut pas lire les fichiers du propriétaire. Avantage : isolement par le système, sans conteneur. Inconvénient : coût d'administration (outils, droits) non consigné dans le compte rendu de la session.
  3. Option (c) : environnement nettoyé et avertissement au démarrage, sur l'hôte. Avantage : immédiat, sans adaptation. Inconvénient : ne protège que contre l'erreur d'un agent, pas contre un agent qui cherche les identifiants.
- **Recommandation des agents** : option (c) maintenant, option (a) avant tout usage sans surveillance.
- **Décision de l'utilisateur** : **option (a)** comme cible.
- **Conséquences** :
  - le sandbox, reporté après PP par [0015](0015-sandbox-reporte-apres-pp.md), devient le **prérequis d'une barrière réelle** contre les agents. Le garde-fou Bash ([0022](0022-panne-garde-bash.md), [0023](0023-perimetre-garde-bash.md), [0028](0028-garde-bash-identifiants-github.md)) ne suffit pas à lui seul ;
  - **en attendant** l'adaptation de Claudeus, des mesures intérimaires sur l'hôte : environnement nettoyé (aucun `GITHUB_TOKEN` d'administration ni autre identifiant du propriétaire dans l'environnement des agents) et avertissement au démarrage. Ces mesures protègent contre l'erreur d'un agent, **pas** contre un agent qui cherche les identifiants sur le disque ;
  - [0015](0015-sandbox-reporte-apres-pp.md) est précisée par la présente décision, sans être modifiée ;
  - la **date** de l'adaptation de Claudeus reste à fixer par l'utilisateur. Un jalon doit la porter (question ouverte dans [17](../conception/17-questions-ouvertes.md)) ;
  - tant que cette adaptation n'est pas faite, la protection contre la fusion et le contournement repose sur le ruleset (approbation du propriétaire, [0025](0025-barriere-serveur-codeowners.md)) et non sur l'isolement des identifiants ;
  - le `GITHUB_TOKEN` d'administration ne doit jamais être dans l'environnement des agents (voir aussi [0013](0013-identite-agents-fusion.md)).
- **Documents mis à jour** : `docs/decisions/README.md` (index), `docs/decisions/0026-isolement-identifiants-claudeus.md` (création), `docs/decisions/0015-sandbox-reporte-apres-pp.md` (note de précision), `docs/decisions/0013-identite-agents-fusion.md`, `docs/conception/README.md`, `docs/conception/17-questions-ouvertes.md`.
