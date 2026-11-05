# 2026-11-05 — Préparation de l'environnement (PP), après-midi

- **Jalon** : PP (préparation de l'environnement), en cours.
- **Objectif de la session** : planifier PP, figer l'outillage (mise, versions exactes), préparer Terraform et la CI, puis enregistrer les décisions de l'utilisateur sur le circuit Git, le nom et l'accroche.

## Fait
- Planification de PP avec `architecte` : [`docs/plans/PP.md`](../plans/PP.md), étapes E0 à E12. L'étape sandbox prévue initialement est retirée (voir [0015](../decisions/0015-sandbox-reporte-apres-pp.md)). Nouvelle étape E3 : passage du ruleset en `bypass_mode = "pull_request"` après le premier push.
- E0 (recherche et vérifications) par `chercheur-web` : [`docs/recherches/2026-11-05-outillage-pp.md`](../recherches/2026-11-05-outillage-pp.md).
- E1 faite et vérifiée. `mise install` a réussi (lancé par l'utilisateur). Versions contrôlées avec `mise exec` : rustc et cargo 1.99.1 (avec rustfmt, clippy et la cible wasm32), just 1.59.0, terraform 1.17.1, gitleaks 8.30.1, node 24.22.2, python 3.14.10, gh 2.103.3, claude 2.1.318. Fichiers : `mise.toml`, `rust-toolchain.toml`, `.gitignore`, `justfile` (shell bash strict, recette `setup`).
- E2 faite, relue par `architecte` (OK avec réserves). Contenu : action `jdx/mise-action@*` autorisée, label `jalon:PP`, `.terraform.lock.hcl` (plateformes linux_amd64 et darwin_arm64). Remplacement de l'attribut obsolète `vulnerability_alerts` par la ressource `github_repository_vulnerability_alerts` (« E2 bis », accepté par l'utilisateur). `terraform fmt -check` et `terraform validate` passent sans avertissement.
- Renommage du jeu en « Nothing To Lose » (identifiant `nothing-to-lose`) et mise à jour de la base documentaire.
- Commit `50eae26` sur `main`, en local : rien n'est poussé.
- Hook `SessionStart` ajouté à la demande de l'utilisateur, hors périmètre de PP (`tools/hooks/session_start.py`, configuré dans `.claude/settings.json`) : il affiche à l'ouverture de Claude Code le dernier journal, ses prochaines étapes et l'état Git. Documentation : [`docs/technique/hook-session-start.md`](../technique/hook-session-start.md).
- Contrôles : `gitleaks` sur l'index, aucun secret détecté. `tools/check_links.py` : 0 lien cassé.

## Résultats
- `just check` : non applicable (aucun code de simulation ; la recette renvoie « à venir (P1) »).
- `just eval` : non applicable.
- `python3 tools/check_links.py` : 0 lien cassé.
- Vérifications des versions d'outils : voir « Fait » (E1).

## Décisions
Décisions structurantes posées à l'utilisateur, enregistrées dans `docs/decisions/` :
- [0007](../decisions/0007-hooks-git-scripts-maison.md) : hooks Git en scripts maison.
- [0008](../decisions/0008-gitleaks-binaire-fige.md) : gitleaks 8.30.1 via mise (le successeur Betterleaks est écarté).
- [0009](../decisions/0009-outils-ci-mise-action.md) : `jdx/mise-action` en CI.
- [0010](../decisions/0010-liste-controle-pr.md) : liste de contrôle de PR bloquante dans `ci-cpu`.
- [0011](../decisions/0011-politique-versions-exactes.md) : versions exactes partout (Node 24.22.2 plutôt que 26 ; Python 3.14.10 plutôt que 3.15).
- [0012](../decisions/0012-markdown-hors-formatage.md) : Markdown exclu du formatage automatique.
- [0013](../decisions/0013-identite-agents-fusion.md) : jeton à granularité fine pour les agents ; bypass de PR après le premier push ; fusion réservée à l'utilisateur.
- [0014](../decisions/0014-sequencement-pp.md) : `tf-apply` et premier push pendant PP, juste après E2.
- [0015](../decisions/0015-sandbox-reporte-apres-pp.md) : sandbox reporté après PP (l'utilisateur utilise Claudeus, github.com/p3bri4n/claudeus).
- [0016](../decisions/0016-nom-nothing-to-lose.md) : nom « Nothing To Lose », Toulouse seulement (remplace [0005](../decisions/0005-nom-say-again.md)).
- [0017](../decisions/0017-accroche-le-speech.md) : speech officiel, avec corrections de fautes de frappe (remplace [0006](../decisions/0006-accroche-lead-or-fade.md)).
- [0018](../decisions/0018-image-principale-key-art.md) : image principale `docs/assets/key-art.png`.
- [0019](../decisions/0019-accroche-command-humanity-last-hope.md) : accroche courte « Command humanity's last hope », sous-titre du key art ; la signature française « commandez avec brio ! » reste dans la description.

Choix mineurs pris en autonomie :
- Verrou Terraform : plateformes du verrou Terraform : darwin_arm64 ajoutée en plus de linux_amd64.
- `rust` déclaré à la fois dans `mise.toml` et dans `rust-toolchain.toml` : mise ne lit ce dernier que sur opt-in.
- Image copiée dans `docs/assets/`.
- Correction de « combattant » en « combattants » dans le speech.

## Problèmes et points ouverts
- Provenance et droits de `key-art.png` non documentés : à régler avant toute publication.
- Graphie officielle de l'accroche (capitales sur l'image) non fixée.
- Direction artistique non tranchée : le style réaliste du key art diverge du diorama low-poly de [`15-rendu-viewer.md`](../conception/15-rendu-viewer.md).
- Sécurité (revue d'E2) :
  - réglage d'approbation des workflows de forks (« Require approval for all external contributors ») à poser comme décision structurante avant l'enregistrement du runner GPU (P2) ;
  - vérifier si le provider Terraform 6.x sait le gérer ;
  - la garde de `gpu-eval.yml` est dans un fichier qu'un fork peut modifier.
- Les actions des workflows ne sont pas encore épinglées par SHA (prévu en E8).
- Non vérifié par la recherche E0 : comportement des hooks Claude Code en mode `bypassPermissions` (à tester) ; premier push vers un dépôt vide couvert par un ruleset.
- Claudeus : incompatibilités probables avec le chemin du dépôt (caractères `:` et espaces) et absence de mise (voir [0015](../decisions/0015-sandbox-reporte-apres-pp.md)).
- Documents historiques (0005, 0006, entrée de conception du matin) mentionnent encore « Say Again » et « Lead or Fade ». C'est volontaire.

## Prochaines étapes
1. Actions de l'utilisateur, dans un shell où mise est activé (`docs/plans/PP.md` §3.2) :
   - copier `infra/terraform/terraform.tfvars.example` en `terraform.tfvars` ;
   - placer le jeton d'administration dans `GITHUB_TOKEN` (shell seulement) ;
   - `just tf-init`, puis `just tf-plan` et relire le plan (uniquement des créations : dépôt `nothing-to-lose`, check `ci-cpu`) ;
   - `just tf-apply` ;
   - `git remote add origin …` puis `git push -u origin main` ;
   - `gh auth login`.
2. Ensuite, E3 (première PR : `bypass_mode = "pull_request"`), puis un nouveau `tf-apply` par l'utilisateur. Puis E4 à E12, une PR par étape (regroupements possibles, voir `docs/plans/PP.md` §4 et risque R17).
3. Créer le jeton à granularité fine des agents après le `tf-apply`.
4. Tester le hook `SessionStart` à la prochaine ouverture de Claude Code (affichage de `systemMessage` non vérifié, voir [`docs/technique/hook-session-start.md`](../technique/hook-session-start.md)). Si le message n'apparaît pas, demander « où en est-on ? » pour vérifier le contexte injecté.
