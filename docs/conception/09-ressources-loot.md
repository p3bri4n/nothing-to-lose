# 09 — Ressources et loot

[← Sommaire](README.md)

## Ressources [Décidé]

**Vivres**, **médicaments**, **munitions**, **matériaux** (pour barricader).

## Sources

| Ressource | Sources |
|---|---|
| Vivres | Bâtiments « vivres » tirés au hasard par quartier |
| Médicaments | Bâtiments « soins » tirés au hasard par quartier (rares, très recherchés) |
| Matériaux | Bâtiments « matériaux » tirés au hasard par quartier ; servent à renforcer les bâtiments (voir [21](21-interieurs-sieges.md)) |
| Munitions | Bâtiments « munitions » tirés au hasard par quartier ; **postes militaires aux portes de la barricade** (connus, mais sur le périmètre où poussent les hordes) ; **corps des survivants tombés** |

**Les bâtiments d'intérêt sont inconnus au départ** [Décidé] : il faut découvrir l'antenne du quartier et la tenir pendant une vague, ou tester les bâtiments un par un. Tous les autres bâtiments sont inexplorables. Voir [19](19-quartiers-batiments.md).

## Fouille

[Décidé] On **entre dans le bâtiment** (intérieur modélisé, voir [21](21-interieurs-sieges.md)) et la fouille se fait à l'intérieur pendant une durée donnée, ce qui remplace la fouille sur le seuil :
- **forcer la porte** : rapide, **très bruyant** (événement sonore) ;
- **entrer discrètement** : silencieux, trois à quatre fois plus long.

Le choix revient au LLM. Les zombies qui ont vu l'entrée peuvent attendre à la sortie.

## Stocks et connaissance

- Stocks finis, sans régénération, tirés avec la seed.
- Chaque escouade tient une carte de croyances (« soins rue X : vidé », « vivres : horde devant la porte »), alimentée par les antennes, les essais de portes et la radio.
- L'information vieillit : un bâtiment connu peut avoir été vidé entre-temps.

## Besoins

- **Faim** : baisse lentement, réduit l'endurance, augmente le stress, fait baisser le moral.
- **Santé** : blessures ; influence la durée d'incubation après une morsure.
- Inventaire limité ; munitions comptées.

## Repos

Assuré par les **bâtiments de repos** tirés au hasard par quartier [Décidé] : récupération de la fatigue, baisse du stress, gain de moral, inspections et conseils en sécurité. Voir [19](19-quartiers-batiments.md).
