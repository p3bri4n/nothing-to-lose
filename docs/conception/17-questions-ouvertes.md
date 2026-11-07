# 17 — Questions ouvertes et journal des décisions

[← Sommaire](README.md)

## Restent ouvertes

| # | Question | Recommandation | Impact |
|---|---|---|---|
| Q21 | Les survivants gardent-ils leur XP d'un épisode à l'autre ? | **Reporté** | [20](20-progression-xp.md) |
| Q30 | Taille de la vague déclenchée par une antenne | Proportionnelle aux zombies du quartier, à régler en équilibrage | [19](19-quartiers-batiments.md) |
| Q32 | Comment l'antenne est-elle découverte ? | Mât visible au-dessus des toits, repéré par ligne de vue | [19](19-quartiers-batiments.md) |
| Q33 | Durée et bruit d'un essai de porte sur un bâtiment inconnu | Quelques secondes ; forcer = bruyant, discret = plus long | [19](19-quartiers-batiments.md) |
| Q31 | Antenne et armoire de piratage au même endroit, ou séparées ? | Séparées : deux objectifs distincts par quartier | [19](19-quartiers-batiments.md) |
| — | Capacités réelles de la machine (CPU, débit LLM en parallèle, latence de Laya) | Trois benchmarks à écrire | [03](03-architecture-technique.md) |

## Journal des décisions (revue du 5 novembre 2026)

| # | Question | Décision |
|---|---|---|
| Q1 | Refuge | Bâtiments de repos tirés au hasard par quartier |
| Q2 | Réintégration d'un exclu | Oui, après une bonne action pour le groupe |
| Q3 | Confiance après une rupture | Plafond définitivement abaissé (~0,85) |
| Q4 | Cacher une griffure | Oui : le survivant peut se taire et mentir |
| Q5 | Résultat d'une griffure pour le public | Caché aussi ; pronostics du public |
| Q6 | Vitesse du son | Ralentie (~50 m/s) |
| Q7 | Effectifs | ~2 000–3 000 zombies, ~100 civils, 6–10 héros LLM (4–6 en live) |
| Q8 | Commandant | Local d'abord, invités plus tard |
| Q9 | Moteur 3D | Three.js |
| Q10 | Médicament contre la griffure | Dans une fenêtre juste après la griffure |
| Q11 | Majorité pour exclure | 2/3 pour un membre sain, simple pour un soupçonné |
| Q12 | Laya | Le modèle de décision de Convai Innovations |
| Q13 | Deuil dans un groupe uni | Plus lourd, mais récupération plus rapide après les bons moments |
| Q14 | Dernier recours (choix de mourir plutôt que d'être mordu) | **Mécanique supprimée** |
| Q15 | Zombies qui forcent l'entrée | Seulement une horde menée par un alpha, sur un bâtiment stratégique |
| Q16 | Fouille | À l'intérieur des bâtiments |
| Q17 | Quartiers | 5 quartiers (axes Alsace-Lorraine / Metz) |
| Q18 | Point d'information | Antenne par quartier, à découvrir puis à tenir pendant toute une vague ; sans elle, tester les bâtiments un par un |
| Q19 | XP des zombies | Oui, avec mutation en alpha |
| Q20 | Choix de la compétence débloquée | Le survivant (son LLM), recommandation possible du commandant |
| Q22 | Compétences | 9 compétences, évolutives ; spécialisations plus tard |
| Q23 | Nombre d'alphas | Un pour X zombies, un par quartier au maximum |
| Q24 | Alpha qui force l'entrée | Oui, sur les bâtiments stratégiques |
| Q25 | Valeur de X | 300 à 500 zombies par alpha (départ de l'équilibrage) |
| Q26 | Perception partagée entre alphas | Non : seulement une priorité de ruche résumée |
| Q27 | Matériaux de renforcement | Stock limité par bâtiment, apport possible depuis ailleurs |
| Q28 | Sorties de secours | À découvrir en explorant l'intérieur |
| Q29 | Intérieurs et sièges | Dans le MVP (J4c, avec les alphas en J4b) |
| — | Nom du projet | **Say Again**, une variante par ville (« Say Again : Toulouse ») — décision 0005 du dépôt |
| — | Nom du projet (suite, 5 novembre 2026) | **Nothing To Lose**, jeu de mots avec Toulouse ; Toulouse seulement dans le nom public ; identifiant technique `nothing-to-lose` — décision [0016](../decisions/0016-nom-nothing-to-lose.md), qui remplace 0005 |
| — | Accroche (suite, 5 novembre 2026) | Le speech officiel, signature « commandez avec brio ! », à la place de « Lead or Fade: Your Command » — décision [0017](../decisions/0017-accroche-le-speech.md), qui remplace 0006 |
| — | Accroche (suite, 5 novembre 2026) | Accroche courte officielle : « Command humanity's last hope » (sous-titre du key art) ; le speech reste le texte long. La signature « commandez avec brio ! » reste celle de la description (précision de l'utilisateur) — décision [0019](../decisions/0019-accroche-command-humanity-last-hope.md), qui complète 0017 |
| — | Outillage et circuit Git du jalon PP (5 novembre 2026) | Hooks Git maison, gitleaks figé via mise, `mise-action` en CI, liste de contrôle des PR bloquante, versions exactes, Markdown hors formatage, identité des agents et fusion réservée à l'utilisateur, séquencement de PP, sandbox reporté (Claudeus) — décisions [0007](../decisions/0007-hooks-git-scripts-maison.md) à [0015](../decisions/0015-sandbox-reporte-apres-pp.md) |

## Journal des décisions (suite, 7 novembre 2026)

| # | Question | Décision |
|---|---|---|
| — | Fusion des pull requests (revue d'architecte d'E10) | Compte machine pour les agents (rôle Write, pas administrateur), 1 approbation requise, fusion par l'utilisateur seul en administrateur ; étape E10b séparée d'E10 — décision [0021](../decisions/0021-fusion-compte-machine-agents.md), qui précise [0013](../decisions/0013-identite-agents-fusion.md) |
| — | Panne du garde-fou Bash | Refus limité aux commandes `git` et `gh` en cas d'erreur, nombre d'erreurs de `guard.log` affiché à l'ouverture de session (à coder) — décision [0022](../decisions/0022-panne-garde-bash.md) |
| — | Périmètre du garde-fou Bash | Règles ajoutées au-delà du plan conservées ; garde sur Edit et Write pour `.git/`, `.githooks/`, `.claude/settings.json` reporté à la refonte des agents — décision [0023](../decisions/0023-perimetre-garde-bash.md) |
