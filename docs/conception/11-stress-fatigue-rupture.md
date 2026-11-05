# 11 — Stress, fatigue et rupture

[← Sommaire](README.md)

## Fatigue

| Composante | Évolution | Récupération |
|---|---|---|
| Endurance (court terme) | Course, combat, charge, piratage | Quelques secondes de calme |
| Fatigue accumulée (long terme) | Activité prolongée | Repos dans un bâtiment de repos uniquement |

Effets : vitesse, précision, temps de réaction, rayon de perception, sensibilité au stress.

## Stress

**Sources** : zombies proches, encerclement, tirs à proximité, blessures, mort ou transformation d'un coéquipier, munitions basses, faim, silence radio prolongé, soupçons dans le groupe, faible confiance accordée par le groupe.

**Apaisements** : repos, nourriture, succès, ordre clair d'un commandant de confiance, coéquipier fiable à proximité, gestes de réconciliation.

**Traits individuels** tirés à la création : résilience, irritabilité, loyauté.

Le **moral** ([18](18-moral.md)) fixe le niveau de base du stress et sa vitesse de récupération. La compétence **Sang-froid** ([20](20-progression-xp.md)) réduit les gains de stress et relève le seuil de rupture.

## Effets (courbe de Yerkes-Dodson)

- Stress modéré : **meilleurs réflexes**.
- Stress élevé :
  - **effet tunnel** (cône de perception rétréci) ;
  - précision en baisse ;
  - **compréhension radio dégradée** : le seuil de confiance ASR augmente, d'où plus de `***` ;
  - probabilité de désobéissance.

## Désobéissance [Décidé]

- **États extrêmes décidés par la simulation** (panique, sidération, fuite) via un jet déterministe : le LLM les joue sans pouvoir les ignorer.
- **Refus nuancés décidés par le LLM**, à partir de l'état intérieur décrit dans son prompt.
- Le schéma Laya du survivant reçoit stress et fatigue en entrée.

## Disputes [Décidé]

Échelle d'escalade, chaque marche étant conditionnée par le stress, la fatigue et la relation entre les protagonistes :

**désaccord → dispute verbale → ultimatum → séparation du groupe ou bagarre → menace armée → tir**

Le LLM écrit les dialogues ; la simulation décide du passage à la marche suivante.

## Point de rupture [Décidé]

Terminologie : « point de rupture » (décompensation de stress aigu) plutôt que « psychose », plus juste et sans stigmatisation.

- **Déclenchement rare** : stress maximal prolongé + fatigue élevée + événement traumatique.
- **Perception corrompue** : le LLM du personnage reçoit des perceptions fausses (un coéquipier sain décrit comme infecté).
- **Bodycam déformée** : le shader altère les silhouettes des coéquipiers.
- **Tir fratricide** : conséquence de la perception corrompue ; décidé par la simulation/Laya, joué par le LLM.
- **Intervention possible** : le commandant par la voix, les coéquipiers par le dialogue ou en désarmant au corps à corps.
- **Après une rupture** : indice de confiance très bas, avec remontée possible (voir [12](12-dynamique-sociale.md)).

## Visualisation

- Jauges de stress et de fatigue au-dessus des héros.
- Bodycam : tremblements, vignettage, respiration.
- Voix des clips : prosodie selon le stress.

## Systèmes

`FatigueSystem`, `StressSystem`, `BreakdownSystem` (déclenchement, filtre de perception corrompue), dans `core`, déterministes.
