# 0020 — Sécurité du hook de formatage : refus si la configuration diffère de HEAD

- **Date** : 2026-11-07
- **Statut** : décidée
- **Contexte** : le hook `PostToolUse` de formatage (E6, `tools/hooks/format_on_edit.py`) exécute des formateurs après chaque édition. La revue d'`architecte` a relevé qu'une modification de `mise.toml`, `.prettierrc.json` ou `mise.local.toml` peut entraîner une exécution de code lors d'une édition suivante.
- **Options présentées** :
  1. Accepter le risque et le documenter — le hook reste tel quel. Avantage : aucun blocage du formatage. Inconvénient : une modification de configuration faite par un agent peut exécuter du code au prochain formatage, sans garde.
  2. Mode paranoïaque de mise (`MISE_PARANOID=1`), confiance liée au contenu des fichiers. Avantage : protection native de mise. Inconvénient : ce réglage n'est lu que dans la configuration globale ou système (ignoré avec un avertissement dans un fichier de projet), donc il dépend de la machine de chaque développeur et n'est pas versionné avec le dépôt.
  3. Le hook refuse de formater si `mise.toml`, `mise.local.toml` ou `.prettierrc.json` diffèrent de HEAD. Avantage : la configuration exécutable doit être commitée et relue avant d'être utilisée. Inconvénient : le formatage automatique s'arrête tant que ces fichiers ne sont pas commités.
- **Recommandation des agents** : option 1 (accepter et documenter), recommandée par l'`architecte`.
- **Décision de l'utilisateur** : option 3 (le hook refuse de formater si la configuration diffère de HEAD). Elle est accompagnée des correctifs suivants :
  - la configuration de Prettier est imposée via `--config`, et non trouvée par recherche dans l'arborescence du fichier formaté ;
  - mise n'installe pas automatiquement les outils manquants pendant le formatage ;
  - le processus formateur est tué à l'expiration du délai (timeout de 30 s).
  Le fichier `rust-toolchain.toml` est ajouté à la liste des fichiers gardés.
- **Conséquences** :
  - tant que `mise.toml`, `mise.local.toml`, `.prettierrc.json` ou `rust-toolchain.toml` ne sont pas commités (ou diffèrent de HEAD), le formatage automatique ne s'applique pas ;
  - le risque résiduel est décrit dans la note [`docs/recherches/2026-11-07-securite-hook-formatage.md`](../recherches/2026-11-07-securite-hook-formatage.md), qui liste les points à revérifier (code de Prettier sur le tag 3.9.10, confiance de mise par chemin ou par contenu, variables d'installation automatique) ;
  - le test de bout en bout de C2 change de fichier d'essai (il ne peut pas être dans `.cache/`, ignoré par Git et par le hook) ; le critère ne change pas ;
  - la garde est à décrire dans `docs/technique/hook-format-on-edit.md` une fois le code en place (non modifié par cette décision).
- **Documents mis à jour** : `docs/decisions/README.md` (index), `docs/decisions/0020-securite-hook-formatage.md` (création), `docs/plans/PP.md` (C2, E6, E11), `docs/recherches/README.md` (index de la note de recherche).
