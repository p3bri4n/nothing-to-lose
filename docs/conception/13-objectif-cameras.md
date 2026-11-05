# 13 — Objectif : piratage des caméras

[← Sommaire](README.md)

## Principe [Décidé]

Tenir une zone pendant un temps X pour pirater les caméras de la ville et gagner une meilleure vue sur les zombies. Couverture imparfaite, mais objectif stratégique.

## Réseau de caméras : plausible mais fictif

Toulouse compte de l'ordre de 650 caméras de vidéoprotection, mais aucun jeu de données ouvert ne les localise. Même si c'était le cas, on **n'utilise pas les emplacements réels** (sensibilité d'une carte réelle de surveillance associée à un récit de piratage). Placement procédural plausible : carrefours, places, abords des monuments.

## Points de piratage

- Armoires techniques ou relais fibre en pleine rue (pas d'intérieurs).
- **Un point par quartier** (4 à 5, voir [19](19-quartiers-batiments.md)), chacun débloquant **les caméras de son quartier**. L'ordre est une décision stratégique.
- Une caméra piratée qui couvre la porte d'un bâtiment permet de vérifier si une horde attend à la sortie.

## Tenir la position

- Un survivant au terminal, immobile, sans pouvoir combattre ; les autres tiennent un rayon de 15 à 25 m.
- Progression arrêtée si personne n'est au terminal ou si la zone est **contestée**.
- **Paliers acquis** à 25 / 50 / 75 %.
- **Alarme à chaque palier** : un événement sonore dans le solveur FDTD, qui fait converger la horde. L'objectif se transforme en siège.
- Durée X réglée en équilibrage headless.

## Couverture imparfaite

- Caméras fixes (cône) et dômes motorisés (balayage, angles morts variables dans le temps).
- **Pannes** tirées avec la seed, découvertes après le piratage.
- **Occlusions** : arcades et frondaisons des arbres bloquent la vue.
- **Observations bruitées** : comptage approximatif (« ~20–40 zombies, direction nord »), meilleur quand plusieurs caméras couvrent la même zone.
- Les observations **vieillissent** et s'estompent sur la carte.

## Bénéficiaires

- **Commandant** (live) : grille de 4 à 9 flux au choix (noir et blanc, 5 fps, horodatage), carte de chaleur. Il doit trier et relayer par radio.
- **Survivants** (clips) : résumés textuels sur la tablette du hacker, intégrés au `BeliefStore`.
- **Option** : Laya analyste, avec des prévisions calibrées et vérifiables.

## Technique

- **Bake** : visibilité à 360° par caméra (raycast sur bâtiments et frondaisons), en bitsets compressés. À l'exécution : intersection avec le cône courant.
- **`core`** : `ObjectiveSystem` (progression, contestation, paliers), `CctvSystem` (états, balayage, observations).
- **Brouillard de guerre** : les observations ne vont qu'à ceux qui ont accès au réseau piraté.

## Source

- Ville de Toulouse, police municipale : https://metropole.toulouse.fr/mon-environnement/prevention-et-securite/police-municipale
