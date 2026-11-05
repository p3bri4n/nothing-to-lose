# Base documentaire

Point d'entrée de toute la documentation du projet. Elle est maintenue par les agents (voir `CLAUDE.md`, section « Base documentaire ») et doit toujours refléter l'état réel du projet.

| Dossier | Contenu | Qui écrit |
|---|---|---|
| [`conception/`](conception/README.md) | Dossier de conception : vision, mécaniques, architecture, jalons, questions ouvertes | Mis à jour après chaque décision de l'utilisateur |
| [`decisions/`](decisions/README.md) | Registre des décisions structurantes (une fiche par décision) | Session principale, après réponse de l'utilisateur |
| [`journal/`](journal/README.md) | Journal de développement (une entrée par session) | `documentaliste`, en fin de session |
| [`technique/`](technique/README.md) | Documentation technique du code tel qu'il existe : modules, formats, commandes | `documentaliste` et `developpeur` |
| [`plans/`](plans/) | Plans de jalons et de fonctionnalités | `architecte` |
| [`recherches/`](recherches/README.md) | Notes de recherche sourcées et datées | `chercheur-web` |
| [`assets/`](assets/) | Visuels du projet, dont l'image principale du jeu [`key-art.png`](assets/key-art.png) ([décision 0018](decisions/0018-image-principale-key-art.md)) | Utilisateur (fichiers fournis), `documentaliste` (index) |

**Règle de cohérence** : si le code et la documentation divergent, c'est un défaut à corriger dans la même session, pas plus tard.
