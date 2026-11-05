# 0007 — Hooks Git : scripts maison dans `.githooks/`

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : le jalon PP prévoit des hooks Git avant commit (détection de secrets, liens de la documentation). Il faut choisir comment les écrire et les installer, sans ajouter de dépendance et sans dupliquer la logique entre le poste local et la CI.
- **Options présentées** :
  1. Scripts maison dans `.githooks/`, activés par `core.hooksPath` — aucune dépendance, une seule source de versions, logique dans des recettes `just` réutilisées par la CI.
  2. Framework `pre-commit` — écarté ; motifs détaillés non consignés dans le compte rendu.
  3. `lefthook` — écarté ; motifs détaillés non consignés dans le compte rendu.
- **Recommandation des agents** : non consignée dans le compte rendu de la session.
- **Décision de l'utilisateur** : scripts maison dans `.githooks/`, activés par `core.hooksPath`. Raison : aucune dépendance, une seule source de versions, logique dans des recettes `just` réutilisées par la CI.
- **Conséquences** :
  - les hooks Git sont des scripts du dépôt (`.githooks/`), pas un outil externe ;
  - la logique des contrôles est dans des recettes `just`, appelées à la fois par les hooks et par la CI ;
  - la mise en route (activation de `core.hooksPath`) doit être documentée dans le dépôt lors de l'implémentation de PP.
- **Documents mis à jour** : `docs/decisions/README.md`, `docs/conception/16-jalons.md`, `docs/conception/17-questions-ouvertes.md`.
