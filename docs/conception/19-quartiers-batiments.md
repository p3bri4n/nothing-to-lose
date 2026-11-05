# 19 — Quartiers, bâtiments et information

[← Sommaire](README.md)

## Découpage en quartiers [Décidé : 5 zones]

Cinq zones, délimitées par les grands axes (rue d'Alsace-Lorraine, rue de Metz) et ajustées au bake :

| Zone | Repères |
|---|---|
| Nord | Saint-Sernin, Arnaud-Bernard |
| Centre | Capitole, Saint-Georges |
| Est | Saint-Étienne |
| Sud | Carmes, Esquirol |
| Ouest | Daurade, Saint-Pierre, quais |

Chaque zone a son propre tirage de bâtiments, son antenne d'information, son point de piratage des caméras ([13](13-objectif-cameras.md)) et au plus un alpha.

## Bâtiments d'intérêt : aléatoires et inconnus [Décidé]

- **Cinq types** : **vivres**, **soins** (médicaments), **matériaux** (pour barricader), **munitions**, **repos** (« dodo »).
- **Tous les autres bâtiments sont inexplorables** : volumes pleins, portes condamnées.
- **Tirage aléatoire par quartier**, à partir de la seed de la partie, parmi les bâtiments candidats. Chaque partie a donc une carte différente.
- [Proposé] Contraintes de tirage : au moins un bâtiment de repos par quartier, distance minimale entre bâtiments du même type, pas tous collés à la barricade. Pondération optionnelle par le type OSM (une pharmacie a plus de chances de contenir des soins) pour garder la vraisemblance.
- **Inconnus au départ** : rien ne distingue de l'extérieur un bâtiment d'intérêt d'un bâtiment inexplorable.
- Les postes militaires aux portes de la barricade restent visibles et connus (munitions à haut risque).

## Les antennes [Décidé]

Pour connaître l'emplacement des bâtiments d'intérêt d'un quartier :
1. **Découvrir l'antenne radio du quartier** : son emplacement n'est pas connu au départ.
2. **La tenir pendant toute une vague de zombies** : l'activation déclenche la vague, et les données (emplacement et type des bâtiments d'intérêt du quartier) arrivent quand la vague est repoussée.
3. Les données arrivent dans le `BeliefStore` des survivants présents.

[Proposé] **Découverte de l'antenne** : un mât visible au-dessus des toits, repéré dès qu'un survivant a une ligne de vue dégagée sur lui (depuis une place, un carrefour, une rue alignée). Explorer le quartier finit donc par la révéler, plus ou moins vite selon le chemin suivi.

[Proposé] **Taille de la vague** : proportionnelle au nombre de zombies du quartier, et renforcée si un alpha l'entend. Paramètres à régler en équilibrage.

[Proposé] Pour distinguer les deux objectifs de chaque quartier, l'antenne et l'armoire de piratage sont à des endroits différents : l'antenne donne les bâtiments, l'armoire donne les caméras.

## Sans les données de l'antenne : tester les bâtiments un par un [Décidé]

- Tant que l'antenne du quartier n'a pas été tenue, il faut **tester les bâtiments un par un** : s'approcher d'une porte et essayer d'entrer.
- Un bâtiment inexplorable ne s'ouvre pas : on l'a appris, mais au prix du temps passé et de l'**exposition** dans la rue.
- [Proposé] Chaque essai dure quelques secondes ; forcer une porte fait du bruit (événement sonore), essayer discrètement prend plus de temps.
- Le résultat de chaque essai (« inexplorable », « vivres », etc.) est mémorisé dans le `BeliefStore` et peut être partagé par radio.
- C'est le dilemme du quartier : chercher l'antenne et affronter une vague, ou tester des portes au hasard en restant exposé.

## La connaissance circule mal

- L'information n'est connue que de ceux qui l'ont lue. Pour la partager, il faut **la transmettre par radio**, donc avec les risques de dégradation : « le refuge est rue *** ».
- Le LLM décide de partager ou non (un exclu peut garder une information pour lui et s'en servir pour négocier sa réintégration).
- Le commandant ne voit sur sa carte que ce qui lui a été relayé, ou ce qu'une bodycam a filmé.
- L'information vieillit : un bâtiment de vivres peut avoir été vidé entre-temps.

## Entrer dans un bâtiment

Les bâtiments stratégiques ont un **intérieur modélisé** (MVP), avec combat, renforcement et sièges menés par les alphas. Voir [21](21-interieurs-sieges.md).
- un bâtiment d'intérêt a **une ou deux portes** (nœuds `entrance=*` d'OSM si disponibles, sinon milieu de la façade la plus longue côté rue) ;
- un survivant qui entre n'est plus visible de l'extérieur (sauf par les fenêtres et les ouvertures) ;
- **bâtiment de repos** : récupération de la fatigue, baisse du stress, gain de moral, inspections et conseils en sécurité ; capacité limitée ;
- [Décidé] **bâtiments de loot** : la fouille se fait à l'intérieur, pièce par pièce. Les deux modes restent : forcer la porte (rapide, bruyant) ou entrer discrètement (lent).
- Les zombies ordinaires n'entrent pas ; ils attendent dehors. **Une horde menée par un alpha peut forcer l'entrée** d'un bâtiment stratégique [Décidé] (voir [21](21-interieurs-sieges.md)).

## Les zombies attendent à la sortie [Décidé]

- **Mémoire d'entrée** : un zombie qui a une ligne de vue sur la porte au moment où un survivant entre enregistre « proie dans le bâtiment X » (heure, nombre de survivants). Cette mémoire s'estompe avec le temps.
- **Fuites par la porte** : le son et l'odeur produits à l'intérieur sortent par les portes (avec atténuation). Un zombie qui n'a rien vu peut quand même flairer une présence. Une radio à fort volume à l'intérieur trahit le groupe.
- **Nouvelles options Laya** pour le zombie et la horde : `attendre à la sortie`, `encercler les portes`, `abandonner la proie`. Les probabilités calibrées montrent la patience de la horde qui faiblit.

## Contre-jeu des survivants

- **Observer depuis une fenêtre** : vue partielle et limitée des abords de la porte (rendue en bodycam).
- **Utiliser la deuxième porte**, quand il y en a une.
- **Créer une diversion** : leurre sonore lancé par une fenêtre, ou coéquipier dehors qui attire la horde.
- **Les caméras piratées** qui couvrent la porte, et le commandant qui prévient par radio.
- **Attendre** que la mémoire des zombies s'estompe, au prix du temps (moral qui baisse, faim).

## Technique

- **Bake** : `zones.json` contient les polygones des quartiers ; liste des bâtiments candidats par zone, avec positions des portes.
- **`core`** :
  - `WorldGenSystem` : tirage seedé des bâtiments d'intérêt et des stocks ;
  - `ShelterSystem` : occupation des bâtiments, capacités, effets du repos ;
  - `KnowledgeSystem` : antennes, essais de portes, mise à jour et partage des connaissances ;
  - mémoire d'entrée des zombies.
- **Viewer** : bascule « vue omnisciente / vue du groupe » dans le replay public. Le spectateur voit ce que le groupe ignore, par exemple la horde qui l'attend derrière la porte.
