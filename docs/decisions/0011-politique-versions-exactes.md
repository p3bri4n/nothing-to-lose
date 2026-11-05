# 0011 — Politique de versions : versions exactes partout

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : le critère de PP exige les mêmes versions d'outils en local et en CI, et la simulation doit pouvoir être rejouée (les versions qui influencent une partie sont consignées dans `summary.json`). Des plages de versions empêcheraient cette reproductibilité.
- **Options présentées** : non consignées dans le compte rendu de la session (décision prise directement par l'utilisateur).
- **Recommandation des agents** : non consignée dans le compte rendu de la session.
- **Décision de l'utilisateur** :
  - versions exactes partout : `mise.toml`, `rust-toolchain.toml`, Claude Code compris ;
  - les mises à jour se font par une pull request dédiée.
- **Conséquences** :
  - toute montée de version est une modification isolée, relue et testée à part ;
  - Claude Code est lui aussi épinglé dans `mise.toml`.
- **Documents mis à jour** : `docs/decisions/README.md`, `docs/conception/16-jalons.md`, `docs/conception/17-questions-ouvertes.md`.
