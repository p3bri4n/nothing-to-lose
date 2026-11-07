# 2026-11-07 — Amorçage Terraform et installation locale

- **Jalon** : PP (préparation de l'environnement), en cours : U2 (`tf-apply`) fait, premier push et E3 restent à faire.
- **Objectif de la session** : appliquer la configuration GitHub en Terraform (U2), corriger ce qui bloque le premier `apply`, puis finaliser l'installation locale de l'utilisateur.

## Fait
- Amorçage Terraform par l'utilisateur, avec un jeton GitHub classique de 7 jours (scopes `repo` et `workflow`) exporté dans `GITHUB_TOKEN` (shell seulement). Aucune valeur de jeton n'est consignée ici.
- `just tf-init`, puis `just tf-plan` relu avec l'utilisateur : 21 créations, 0 modification, 0 destruction. Contenu du plan : dépôt public `nothing-to-lose`, ruleset de la branche principale avec le check `ci-cpu` et le contournement administrateur `always` (volontaire avant E3), permissions des actions, 3 variables dont `DEPLOY_ENABLED=false` et `GPU_EVAL_ENABLED=false`, 12 labels, environnement `production` avec sa politique de déploiement, alertes de vulnérabilités, secret scanning et push protection.
- `just tf-apply` terminé avec succès.
- Installation locale de l'utilisateur :
  - `mise` installé ; `just` 1.59.0 (`aqua:casey/just`) n'était introuvable tant que `mise activate bash` n'était pas dans `~/.bashrc` (ajouté) ;
  - fonction `ntl` dans `~/.bashrc` : sous-shell qui charge `~/.config/nothing-to-lose/agents.env` (variable `GH_TOKEN`, droits 600), se place dans le dépôt et lance `mise exec -- claude` ;
  - un `agents.env` existe désormais. Son contenu n'a pas encore été vérifié.
- Fichiers modifiés dans l'arbre de travail (non commités) :
  - `justfile` : recette `tf-init` avec `terraform init -reconfigure` (voir « Décisions ») ;
  - `docs/technique/ci-cd.md` : paragraphe « Piège du premier `apply` » ajouté.

## Résultats
- `just tf-apply` : succès, après correction des deux pièges ci-dessous.
- Piège 1 : `terraform init` refusait avec « Backend configuration changed ». Le cache `.terraform/` datait du 5 novembre et pointait vers un autre chemin d'état, alors que l'état réel était vide. Correction : `-reconfigure` ajouté à `tf-init`.
- Piège 2 : le premier `apply` a échoué sur le label `bug` (`422 already_exists`), car GitHub crée des labels par défaut dans tout nouveau dépôt. Correction : suppression du label par défaut via l'API, puis nouvel `apply` (Terraform a repris là où il s'était arrêté).
- Incident de sécurité : une ligne `export GITHUB_TOKEN=…` en clair s'était retrouvée dans `~/.bashrc`. L'utilisateur l'a supprimée et a révoqué le jeton d'amorçage après l'`apply`. Aucune valeur n'est reproduite dans ce journal.
- Incident d'installation : le bloc de la fonction `ntl` a été collé avec des résidus d'écran et un `source ~/.bashrc` récursif (terminal bloqué). Réparé à la main par l'utilisateur.
- `just check` et `just eval` : non lancés, non applicables (aucun code de simulation touché).
- `python3 tools/check_links.py` : 0 lien cassé.

## Décisions
Aucune décision structurante tranchée aujourd'hui.

Demandes de l'utilisateur en cours, non tranchées :
- **Renommage du dossier du projet** (ancien nom « Guide Or Fade : Your command ») en `nothing-to-lose`. Un script de renommage est préparé hors du dépôt : il renomme le dossier, déplace l'historique Claude Code associé, corrige le chemin dans la fonction `ntl` et lance `mise trust`. Il doit être lancé Claude fermé.
- **Utilisation de Claudeus** (conteneurs sécurisés, github.com/p3bri4n/claudeus) à la place de `claude`. La décision [0015](../decisions/0015-sandbox-reporte-apres-pp.md) reste en vigueur. Ses quatre points non vérifiés doivent être traités avant tout usage réel : `mise` absent de l'image, montage et nom de conteneur avec le chemin du dépôt (réglés par le renommage), liste blanche réseau sans les domaines de `mise`, et `--dangerously-skip-permissions` utilisé par défaut, donc `guard_bash.py` (E10) requis avant tout usage réel.

Choix mineurs pris en autonomie :
- `-reconfigure` ajouté à `tf-init` : le cache `.terraform/` pointait vers un ancien chemin d'état. Accord de l'utilisateur.
- Suppression du label `bug` créé par défaut par GitHub : Terraform ne peut pas le créer s'il existe déjà.

## Problèmes et points ouverts
- **Fichier `infra/terraform/terraform.tfvars.example` supprimé** dans l'arbre de travail (non commité, raison non consignée). Or `docs/technique/ci-cd.md` (ligne 22) et `docs/plans/PP.md` le citent encore comme modèle à copier. À trancher : restauration ou mise à jour de la documentation.
- **Provenance de `key-art.png`** : l'utilisateur indique qu'elle est générée avec Gemini (Nano Banana 2). La provenance est donc connue, mais [0018](../decisions/0018-image-principale-key-art.md) et le point ouvert de l'entrée du 5 novembre disent encore « non documentée ». Les droits d'utilisation n'ont pas été vérifiés : l'utilisateur refuse cette vérification et garde l'image telle quelle. Ce point reste à documenter avant toute publication.
- État Terraform local, hors du dépôt (voir [0002](../decisions/0002-etat-terraform-local.md)) : sa sauvegarde chiffrée reste à la charge de l'utilisateur.
- Jeton des agents U5 : à créer (granularité fine, limité au dépôt, Contents, PR et Issues en écriture). Son emplacement dans `agents.env` est à vérifier.
- Graphie officielle de l'accroche (capitales sur l'image) non fixée.
- Direction artistique non tranchée : le style réaliste du key art diverge du diorama low-poly de [`15-rendu-viewer.md`](../conception/15-rendu-viewer.md).
- Sécurité (revue d'E2), inchangé :
  - réglage d'approbation des workflows de forks (« Require approval for all external contributors ») à poser comme décision structurante avant l'enregistrement du runner GPU (P2) ;
  - vérifier si le provider Terraform 6.x sait le gérer ;
  - la garde de `gpu-eval.yml` est dans un fichier qu'un fork peut modifier.
- Les actions des workflows ne sont pas encore épinglées par SHA (prévu en E8).
- Non vérifié : comportement des hooks Claude Code en mode `bypassPermissions` (à tester).
- Topic public `toulouse` du dépôt : signalé à l'utilisateur, non tranché.
- Anciens chemins : [0015](../decisions/0015-sandbox-reporte-apres-pp.md) et [`PP.md`](../plans/PP.md) (§ sandbox) citent « Guide Or Fade : Your command ». À corriger après le renommage.
- Documents historiques (0005, 0006, entrée de conception du matin) mentionnent encore « Say Again » et « Lead or Fade ». C'est volontaire.

## Prochaines étapes
1. Lancer le script de renommage (Claude fermé), rouvrir le projet via `ntl`, puis corriger les mentions de l'ancien chemin dans le dépôt.
2. Premier push : `git remote add origin …` puis `git push -u origin main` (commandes dans `docs/technique/ci-cd.md`). Puis `gh auth login`.
3. Créer le jeton des agents (U5) et vérifier le contenu de `agents.env`.
4. E3 : première PR avec `bypass_mode = "pull_request"`, puis un nouvel `tf-apply` par l'utilisateur (avec un jeton Terraform à granularité fine). Puis E4 à E12, une PR par étape.
5. Trancher : restauration de `terraform.tfvars.example` ou mise à jour des références, et mise à jour de la provenance dans 0018.
6. Examiner le dépôt Claudeus en lecture seule, pour lister les adaptations nécessaires avant d'en faire l'outil de travail (demande à instruire, voir « Décisions »).
7. Tester le hook `SessionStart` à la prochaine ouverture de Claude Code (affichage de `systemMessage` non vérifié, voir [`docs/technique/hook-session-start.md`](../technique/hook-session-start.md)).
