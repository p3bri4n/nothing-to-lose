# 0028 — Extension du garde Bash aux identifiants GitHub

- **Date** : 2026-11-07
- **Statut** : décidée
- **Contexte** : le garde-fou `tools/hooks/guard_bash.py` refuse déjà les commandes qui contournent le circuit Git (décision [0023](0023-perimetre-garde-bash.md) pour son périmètre). Rien ne l'empêche aujourd'hui d'afficher ou de manipuler les identifiants GitHub : `gh auth token` affiche le jeton, `gh auth login` ou `switch` changent de compte, et les variables `GH_TOKEN` ou `GITHUB_TOKEN` peuvent être affectées, retirées ou transmises à une commande.
- **Options présentées** :
  1. Étendre le garde aux identifiants GitHub : refus de `gh auth token|login|logout|switch|refresh`, de `gh auth status --show-token`, et des affectations et retraits de `GH_TOKEN`, `GITHUB_TOKEN`, `GH_ENTERPRISE_TOKEN` et `GITHUB_ENTERPRISE_TOKEN`. Avantage : ferme les moyens simples d'accès au jeton par une commande Bash. Inconvénient : palliatif partiel, car `curl` et la lecture directe de fichiers restent possibles.
  2. Ne pas étendre : le garde reste limité au circuit Git. Avantage : aucune règle nouvelle à maintenir. Inconvénient : un agent peut afficher le jeton avec `gh auth token`.
- **Recommandation des agents** : option 1 (étendre), recommandée par la session principale.
- **Décision de l'utilisateur** : **étendre**.
- **Conséquences** :
  - refus, par `guard_bash.py`, des commandes suivantes : `gh auth token`, `gh auth login`, `gh auth logout`, `gh auth switch`, `gh auth refresh`, `gh auth status --show-token` ; des affectations et retraits de `GH_TOKEN`, `GITHUB_TOKEN`, `GH_ENTERPRISE_TOKEN` et `GITHUB_ENTERPRISE_TOKEN` sous toutes leurs formes : `env -u`, `unset`, préfixe de commande (`GH_TOKEN=… commande`) et `export` ;
  - palliatif partiel : `curl` et la lecture directe de fichiers (par exemple la configuration de `gh`) restent possibles. Cette limite ne se règle pas par une règle de garde : elle est traitée par l'isolement des identifiants ([0026](0026-isolement-identifiants-claudeus.md)) ;
  - le périmètre décidé en [0023](0023-perimetre-garde-bash.md) est étendu, sans être remis en cause ; le garde sur `Edit` et `Write` reste reporté ;
  - la mise en œuvre dans `guard_bash.py`, ses tests et la documentation (`docs/technique/garde-fous-bash.md`) sont faites en E10b (règles `gh-auth` et `gh-token-env`, tests dans `tools/tests/test_guard_bash.py`, page `docs/technique/garde-fous-bash.md`).
- **Documents mis à jour** : `docs/decisions/README.md` (index), `docs/decisions/0028-garde-bash-identifiants-github.md` (création), `docs/conception/README.md`, `docs/conception/17-questions-ouvertes.md`.
