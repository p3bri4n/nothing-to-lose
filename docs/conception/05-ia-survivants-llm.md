# 05 — IA survivants : LLM

[← Sommaire](README.md)

## Deux cerveaux par survivant

| | System 2 (LLM) | System 1 (Laya) |
|---|---|---|
| Rôle | Stratégie, règles d'engagement, dialogues, décisions sociales | Réflexes de combat, réactions immédiates |
| Cadence | Plan toutes les 2 à 5 s ; conseils ponctuels | ~30 ms, sur événement |
| Sortie | JSON contraint : intention, posture, destination, mode de fouille, réplique radio | Intention réflexe |

Exemple de posture fixée par le LLM : « économiser les munitions, ne tirer que si plus de 3 zombies ou si un coéquipier est au contact ; sinon corps à corps ; repli vers la pharmacie si griffure ».

## Effectifs

- **6 à 10 héros LLM** au maximum (mode clips), 4 à 6 en live.
- Les civils restent en utility AI.
- LLM : Qwen3.6-27B via TabbyAPI/ExLlamaV3, sortie JSON contrainte par schéma.

## Contenu du prompt

Construit **uniquement** à partir du `BeliefStore` du personnage :
- état interne : faim, santé, endurance, fatigue, stress, symptômes ressentis ;
- inventaire ;
- niveaux de compétence, décrits en langage clair ([20](20-progression-xp.md)) ;
- perceptions récentes (son, odeur, vue, radio telle que **comprise**, avec ses `***`) ;
- carte de croyances (loot connu, zones dangereuses, observations CCTV si accès) ;
- relations, indices de confiance perçus, soupçons ;
- ordres reçus du commandant.

## Pare-feu d'information

- La vérité (infection réelle, stocks réels, positions non vues) vit dans la simulation.
- Le constructeur de prompts ne lit que le `BeliefStore`.
- **Test automatique** vérifiant qu'aucun champ de vérité ne fuit dans un prompt.
- Usage inverse et volontaire : la **perception corrompue** lors d'une rupture (voir [11](11-stress-fatigue-rupture.md)).

## Le conseil

Événement déclenché par une griffure vue, un affaiblissement remarqué, une proposition d'exclusion ou une arrivée dans un bâtiment de repos :
- chaque membre parle à tour de rôle ;
- nombre de tours borné ;
- vote pondéré par l'indice de confiance.

## Actions sociales du LLM

`demander_inspection`, `accepter` / `refuser`, `accuser`, `se_justifier`, `révéler_griffure`, `voter_exclusion`, `proposer_exclusion`, `isoler`, `émettre`, `changer_canal`, `couper_volume`, `répéter`.

## Infection et perte du System 2

Pendant l'incubation, les répliques du LLM deviennent progressivement confuses (dégradation injectée dans le prompt), puis le LLM est retiré : il ne reste que le schéma Laya zombie.

## Contraintes

- Certaines décisions dures (tir pendant une rupture, panique) sont prises **par la simulation ou par Laya**, pas par le LLM : il se contente de les jouer.
- Le temps de réponse est compensé par la réaction immédiate de Laya (« reçu », « répétez »).
