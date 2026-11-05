# 0008 — Gitleaks : binaire figé via mise, règles par défaut étendues

- **Date** : 2026-11-05
- **Statut** : décidée
- **Contexte** : le jalon PP exige qu'un commit contenant un faux secret soit bloqué. La détection doit donner le même résultat en local (hook Git) et en CI, avec une version figée.
- **Options présentées** :
  1. Binaire `gitleaks` figé via mise, configuration `.gitleaks.toml` qui étend les règles par défaut — même binaire en local et en CI.
  2. `gitleaks-action` en CI — écarté : la CI n'utilise pas cette action, elle lance le même binaire que le poste local.
- **Recommandation des agents** : non consignée dans le compte rendu de la session.
- **Décision de l'utilisateur** : binaire figé via mise ; `.gitleaks.toml` avec `useDefault = true` (les règles par défaut de gitleaks restent actives, les règles du projet s'y ajoutent) ; les faux positifs sont ignorés par empreinte ; en CI, le même binaire, sans `gitleaks-action`.
- **Conséquences** :
  - la version de gitleaks est définie dans `mise.toml` (voir [0011](0011-politique-versions-exactes.md)) ;
  - un faux positif ne s'ignore pas par une règle générale : il est listé par empreinte dans `.gitleaks.toml` ;
  - le même contrôle tourne dans le hook Git et dans la CI.
- **Documents mis à jour** : `docs/decisions/README.md`, `docs/conception/16-jalons.md`, `docs/conception/17-questions-ouvertes.md`.
