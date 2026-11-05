# 0003 — Dépôt public dès le départ

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : les tests avec Laya et le LLM ne peuvent tourner que sur la machine de l'utilisateur (runner GPU auto-hébergé), ce qui est risqué sur un dépôt public si du code proposé par des inconnus peut s'y exécuter.
- **Options présentées** :
  1. Privé pendant le développement, public au lancement
  2. Public dès le départ, runner GPU limité aux pushs sur la branche principale et aux lancements manuels
  3. Privé, seuls les replays et vidéos sont publiés
- **Décision de l'utilisateur** : public dès le départ.
- **Conséquences** : `gpu-eval.yml` jamais déclenché par `pull_request`, réservé aux pushs sur `main` (protégée) et aux lancements manuels du propriétaire ; liste blanche des actions autorisées ; détection de secrets et blocage des pushs contenant un secret ; secrets de déploiement limités à l'environnement `production`.
- **Documents mis à jour** : `infra/terraform/`, `.github/workflows/`, `CLAUDE.md`, `docs/technique/ci-cd.md`.
