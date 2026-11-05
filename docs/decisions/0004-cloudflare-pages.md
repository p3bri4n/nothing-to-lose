# 0004 — Déploiement du viewer sur Cloudflare Pages

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : le viewer de replays a besoin des en-têtes COOP/COEP pour le multithread WebAssembly, que GitHub Pages ne permet pas.
- **Options présentées** :
  1. Cloudflare Pages — gratuit, en-têtes configurables, gérable par Terraform (recommandée)
  2. Netlify — gratuit, en-têtes configurables
  3. Plus tard — CI uniquement pour l'instant
- **Recommandation des agents** : Cloudflare Pages.
- **Décision de l'utilisateur** : Cloudflare Pages.
- **Conséquences** : `deploy-viewer.yml` (désactivé tant que `DEPLOY_ENABLED` n'est pas à `true`), `web/viewer/public/_headers`, secrets Cloudflare dans l'environnement `production`. Création du projet Pages et du jeton Cloudflare à faire avant activation.
- **Documents mis à jour** : `.github/workflows/deploy-viewer.yml`, `infra/terraform/`, `docs/technique/ci-cd.md`, `docs/conception/03-architecture-technique.md`.
