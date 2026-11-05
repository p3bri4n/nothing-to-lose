# 04 — IA zombies : Laya

[← Sommaire](README.md)

## Ce qu'est Laya

Modèle de décision open-weight de Convai Innovations, sous Apache 2.0 :
- **Il ne génère pas de texte.** Il reçoit un état (texte ou JSON) et des questions typées (`choice`, `score`, `noul`) et renvoie des réponses avec leurs probabilités, en une passe.
- Checkpoint anglais : ModernBERT-large + tête de décision, 421M paramètres, contexte de 512 tokens. Checkpoint multilingue : 322M, 100+ langues.
- **Les options se définissent à chaque requête** : on peut ajouter un comportement sans réentraîner.
- Latence (T4) : ~40 ms pour une question, ~160 ms pour 10 questions groupées.

## Limites connues (et parades)

| Limite | Parade |
|---|---|
| Proche du hasard en zero-shot | **Fine-tuning obligatoire** (le notebook fourni monte à ~0,77) |
| Checkpoints trop confiants | Recalibration (température) sur nos données |
| Faible sur les questions à beaucoup d'options | Questions `choice` de 3 à 8 options ; découpage hiérarchique |
| Échelles ordinales (`score`) faibles | Les éviter |
| `noul` biaisé sur le checkpoint anglais | Utiliser `choice` oui/non |
| `act_probability` sans signal | Décider à partir de `confidence` |
| Contexte de 512 tokens | Perception textuelle compacte et quantifiée |

## Les usages de Laya dans le projet

| Schéma | Rôle |
|---|---|
| **Zombie** | Intentions : suivre la horde, enquêter sur un bruit, remonter une odeur, rôder, encercler, attaquer le plus faible, attendre en embuscade, **attendre à la sortie d'un bâtiment, encercler les portes, abandonner la proie** (voir [19](19-quartiers-batiments.md)) |
| **Horde** | Décisions stratégiques de groupe (beaucoup moins d'appels qu'au niveau individuel) |
| **Alpha** | Schéma enrichi pour le chef de horde : encercler un bâtiment, couper une retraite, attirer dans une impasse, cri de rassemblement, répondre à une demande d'aide d'un autre alpha, **choisir le cri à pousser (aucun, rassemblement, charge, embuscade, repli)**, **forcer l'entrée d'un bâtiment stratégique (choix du point d'assaut, feinte, attente)** (voir [21](21-interieurs-sieges.md)). La priorité de ruche est une entrée ; au-delà d'un seuil, l'option « ignorer » disparaît (voir [20](20-progression-xp.md)) |
| **Survivant (réflexes)** | Tirer, frapper, reculer, se dégager, couvrir un coéquipier, fuir, se figer, **se repositionner si un allié est dans la ligne de tir**, renforcer, tenir la brèche, se replier dans la pièce suivante, fuir par la sortie de secours, selon la posture fixée par le LLM ; entrées : stress, fatigue, niveaux de compétence |
| **Classification des ordres** | Ordre du commandant → catégorie (déplacement, repli, attaque, fouille, inspection, incompréhensible), pour une réaction immédiate |
| **Jugement social** | Chaque témoin juge une action : positive / neutre / négative |
| **Évaluation de menace** | « Le groupe peut-il atteindre son objectif en gardant X ? » |
| **Juge d'infection** | « Ce survivant est-il infecté ? », à partir des indices observables |
| **Analyste CCTV** (option) | Prévisions calibrées à partir des observations des caméras |
| **Chat** (saison 2) | Classification multilingue des messages du public |

**Progression des zombies** : les options disponibles dans le schéma dépendent du niveau du zombie. Un zombie novice n'a que les intentions de base ; les paliers en ajoutent. Le dataset de fine-tuning doit couvrir ces variantes de schéma.

## Perception textuelle quantifiée

Avant de construire le texte : direction sur 8 secteurs, distance en 3 tranches, intensité en 3 niveaux. Exemple :

```
bruit: impulsif fort, S, proche, direction instable | odeur: humain blessé, NE, moyenne | horde: 12 | faim: haute | lieu: place du Capitole, arcades
```

Avantages : un état plus facile à apprendre, un cache de décisions efficace (beaucoup de zombies partagent le même état), un dataset plus compact.

## Broker de décisions

- Décisions **sur événement** : cible aperçue, bruit entendu, cible perdue, groupe modifié.
- File de priorité, batching sur une fenêtre de ~30 ms, cache sur le hash de l'état.
- Niveau de détail : les zombies hors écran utilisent une heuristique.
- Deadline par requête ; en cas de dépassement, repli sur l'utility AI.

## Fine-tuning par distillation

1. Le LLM local génère des décisions « expertes » sur des états simulés.
2. Fine-tuning de Laya avec le notebook officiel.
3. Recalibration (température par type de question et nombre d'options).
4. Banc de test : accuracy, ECE, latence sur notre matériel.

**Premier livrable de J4** : schéma zombie à 6 intentions, ~500 états, fine-tuning, mesures. Si Laya ne tient pas, on le sait avant d'investir dans le reste.

## Effets visuels liés à Laya

- **Overlay des probabilités** au-dessus des zombies (et des survivants en réflexe).
- **La confiance pilote l'animation** : hésitation, titubation, charge.
- Plan emblématique : un zombie partagé entre un bruit et une odeur (« bruit 48 % / odeur 44 % »), jusqu'à ce que le vent tourne.

## Sources

- Laya sur Hugging Face : https://huggingface.co/app2610/laya
- LLM Reference — Laya : https://www.llmreference.com/model/laya
- GameBusiness.jp : https://www.gamebusiness.jp/article/2026/10/01/28183.html
