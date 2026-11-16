# 0029 — Extraction de l'infrastructure agentique vers `jeanclaude` ; Claudeus limité à l'isolation

- **Date** : 2026-11-16
- **Statut** : décidée
- **Contexte** : le dépôt contient beaucoup d'infrastructure agentique et CI/CD qui n'a rien de spécifique au jeu : sous-agents et règles d'escalade, garde-fous Bash, circuit Git des agents, module Terraform de configuration GitHub (ruleset, compte machine, CODEOWNERS, barrière de fusion), modèles de journal et de décisions. Claudeus ([github.com/p3bri4n/claudeus](https://github.com/p3bri4n/claudeus)), l'outil de sandbox de l'utilisateur, ne fournit aujourd'hui que l'isolation : conteneur (sysbox), pare-feu de sortie avec `URL_whitelist.yml`, montage du seul dossier projet, injection de `GH_TOKEN` et de l'identité Git depuis `~/.config/claudeus/env`. La question est de savoir où loger cette infrastructure générique et comment la faire évoluer.
- **Options présentées** :
  1. Extraire maintenant — écartée.
  2. Extraire après E10b et E11, une fois Claudeus adapté et E11 vérifié — **retenue**.
  3. Extraire après E12 — écartée.
  4. Plugin Claude Code — écartée.
  5. Sous-module Git — écartée.
  6. Tout dans Claudeus — écartée.
  7. Rester dans ce dépôt — écartée.

  Les avantages et inconvénients détaillés de chaque option ne sont pas consignés dans le compte rendu de la décision.
- **Recommandation des agents** : privé au départ, le reste suivi (la décision retient la séquence et la livraison recommandées ; seule la visibilité diverge).
- **Décision de l'utilisateur** :
  1. **Périmètre de Claudeus : isolation uniquement** (conteneur, pare-feu, montages, injection des identifiants). Claudeus ne connaît aucun projet qui l'utilise. Il offre des points d'extension remplis par chaque projet : surcharge de la liste blanche par projet (`.claudeus/URL_whitelist.yml`), chemins montés en lecture seule (`.claudeus/readonly-paths`), profil d'identité par projet (`~/.config/claudeus/<profil>.env`). Ces noms de fichiers sont des propositions, pas des décisions.
  2. **Nouveau projet `jeanclaude`** : il héberge la méthode et l'infrastructure génériques (agents et règles d'escalade, hooks et garde-fous `guard_bash`, circuit Git, module Terraform : ruleset, compte machine, CODEOWNERS, barrière de fusion `verify-pp merge-barrier`, modèles de journal et de décisions).
  3. **Séquence** : après E10b (application du compte machine) et E11 (vérification finale, faite dans Claudeus adapté), puis extraction de ce qui est vérifié. Pas avant. L'adaptation de Claudeus (jeton classique selon [0024](0024-jeton-compte-machine-classique.md), liste blanche par projet, chemins en lecture seule, profil d'identité par projet) précède E11. **Sa date reste à fixer** par l'utilisateur.
  4. **Livraison** : modèle de dépôt avec resynchronisation à la demande (pas de plugin ni de sous-module). Chaque projet garde ses surcharges. `nothing-to-lose` reste consommateur de `jeanclaude`, avec ses éléments propres au jeu : déterminisme, pare-feu d'information, Laya, jalons.
  5. **Visibilité** : `jeanclaude` **public dès le départ**. Ce choix va à l'encontre de la recommandation des agents (privé au départ), retenu par l'utilisateur.
- **Conséquences** :
  - **Risque accepté à consigner** : un dépôt public expose dès le départ les détails des garde-fous, leurs contournements connus et la procédure des jetons. Avant publication, une relecture est requise : aucun secret, aucune donnée propre au jeu, limites documentées honnêtement.
  - **Position d'E12 non précisée** : le compte rendu de la décision place l'extraction après E10b et E11, et écarte « après E12 ». Il ne dit pas explicitement si E12 (documentation et journal) passe avant ou après l'extraction. À confirmer par l'utilisateur lors de la préparation de l'extraction.
  - **Incohérence connue à corriger dans Claudeus** : le README de Claudeus recommande un jeton d'accès personnel à granularité fine, alors que la décision [0024](0024-jeton-compte-machine-classique.md) impose un jeton classique à portée `repo` (voir aussi [0026](0026-isolement-identifiants-claudeus.md)). À corriger lors de l'adaptation de Claudeus.
  - Les mesures intérimaires sur l'hôte ([0026](0026-isolement-identifiants-claudeus.md)) restent en vigueur jusqu'à l'adaptation de Claudeus ; cette décision ne les modifie pas.
  - Les décisions qui portent sur l'infrastructure générique ([0013](0013-identite-agents-fusion.md), [0021](0021-fusion-compte-machine-agents.md), [0022](0022-panne-garde-bash.md), [0023](0023-perimetre-garde-bash.md), [0024](0024-jeton-compte-machine-classique.md) à [0028](0028-garde-bash-identifiants-github.md)) restent valables. Leur implémentation déplacée vers `jeanclaude` n'est pas encore décrite : le compte rendu de la décision ne précise pas le calendrier de migration des fichiers.
  - La spécification v2.1 des agents ([`docs/plans/refonte-agents-v2.1-specs.md`](../plans/refonte-agents-v2.1-specs.md), proposition non décidée) et son plan de migration devront tenir compte de l'extraction : les agents ne seront plus seulement dans ce dépôt.
  - Le jalon PP et son plan ([`docs/plans/PP.md`](../plans/PP.md)) ne sont pas réécrits ; seul un renvoi vers la présente fiche est ajouté à la section 10.
- **Documents mis à jour** : `docs/decisions/README.md` (index), `docs/decisions/0029-extraction-jeanclaude.md` (création), `docs/decisions/0015-sandbox-reporte-apres-pp.md` (note de précision, sans changer le report), `docs/conception/README.md` (décisions structurantes), `docs/conception/17-questions-ouvertes.md` (question de la date d'adaptation mise à jour, journal des décisions), `docs/plans/PP.md` (renvoi en section 10), `docs/plans/refonte-agents-v2.1-specs.md` (renvoi dans l'encadré de statut).
