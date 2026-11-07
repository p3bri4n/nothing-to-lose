# 0022 — Panne du garde-fou Bash : refus limité à git et gh, avertissement à l'ouverture de session

- **Date** : 2026-11-07
- **Statut** : décidée
- **Contexte** : le hook `PreToolUse` `tools/hooks/guard_bash.py` laisse passer une commande (code 0) quand il ne peut pas l'analyser (JSON invalide, exception interne), et écrit une ligne dans `.cache/hooks/guard.log`. Un défaut du hook passe donc inaperçu tant que personne ne lit ce journal, et pendant ce temps une commande `git` ou `gh` non vérifiée peut être exécutée.
- **Options présentées** :
  1. Laisser passer et journaliser (comportement actuel). Avantage : aucun blocage du travail. Inconvénient : pendant une panne, toute commande passe, y compris `git` et `gh`, sans signal visible à l'ouverture de session.
  2. Refuser seulement les commandes qui contiennent `git` ou `gh`, laisser passer le reste, et afficher à l'ouverture de session le nombre d'erreurs de `.cache/hooks/guard.log`. Avantage : le circuit Git reste protégé pendant une panne, le reste du travail continue, et l'erreur devient visible. Inconvénient : une commande `git` légitime peut être refusée tant que le hook est en panne ; le code et le test sont à écrire.
  3. Tout refuser pendant une panne. Avantage : protection maximale. Inconvénient : bloque tous les agents sur un défaut du hook lui-même.
- **Recommandation des agents** : option 2, recommandation de la session principale.
- **Décision de l'utilisateur** : **option 2**.
- **Conséquences** :
  - la règle « un garde-fou qui plante laisse passer » décrite dans [`docs/technique/garde-fous-bash.md`](../technique/garde-fous-bash.md) est remplacée par cette règle **une fois le code écrit** ;
  - **non réalisé à la date de cette fiche** : `guard_bash.py` laisse encore passer toute commande en cas d'erreur, et `tools/hooks/session_start.py` n'affiche pas encore le nombre d'erreurs de `guard.log` ; la documentation décrit donc toujours le comportement actuel ;
  - à faire : modifier `guard_bash.py` (refus des commandes contenant `git` ou `gh` en cas d'erreur, avec explication en français), ajouter les tests correspondants à `tools/tests/test_guard_bash.py`, afficher le compte d'erreurs dans `session_start.py`, puis mettre à jour `docs/technique/garde-fous-bash.md` et `docs/technique/hook-session-start.md` ;
  - le contrat de sortie du hook (code 2 pour un refus, message en français) ne change pas ;
  - il reste volontairement aucune variable d'environnement qui désactive le garde-fou.
- **Documents mis à jour** : `docs/decisions/README.md` (index), `docs/decisions/0022-panne-garde-bash.md` (création), `docs/conception/README.md`, `docs/conception/17-questions-ouvertes.md`.
