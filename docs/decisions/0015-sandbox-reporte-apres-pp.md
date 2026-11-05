# 0015 — Sandbox reporté après PP

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : le jalon PP prévoyait une image Docker du sandbox contenant les outils figés. L'utilisateur dispose déjà de son propre outil de sandbox, Claudeus (github.com/p3bri4n/claudeus).
- **Options présentées** : non consignées dans le compte rendu de la session (décision prise directement par l'utilisateur).
- **Recommandation des agents** : non consignée dans le compte rendu de la session.
- **Décision de l'utilisateur** :
  - le sandbox est reporté après PP ; l'utilisateur utilise Claudeus ;
  - PP ne fournit pas d'image Docker ;
  - le critère de PP sur les versions d'outils (critère C4) est limité au local et à la CI.
- **Points à traiter plus tard** (relevés lors de la décision, non vérifiés) :
  - Claudeus n'installe pas mise : son image (node:20 + apt) est commune à tous les projets ;
  - son montage `-v "$PROJECT_DIR":/workspace` et son nom de conteneur `--name claudeus-<dossier>` échouent probablement avec le chemin du dépôt « Guide Or Fade : Your command » ;
  - sa liste blanche réseau ne contient pas les domaines de téléchargement de mise ;
  - il tourne par défaut avec `--dangerously-skip-permissions`.
- **Conséquences** :
  - le jalon PP ne comprend plus d'image du sandbox ; le critère de cohérence des versions porte sur le local et la CI ;
  - les points ci-dessus sont à traiter avant d'utiliser Claudeus pour le développement du projet.
- **Documents mis à jour** : `docs/decisions/README.md`, `docs/conception/16-jalons.md`, `docs/conception/17-questions-ouvertes.md`.
