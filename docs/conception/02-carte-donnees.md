# 02 — Carte et données

[← Sommaire](README.md)

## Toulouse seulement dans le nom, la ville reste une donnée [Décidé]

Le nom public, « Nothing To Lose », ne désigne que Toulouse (décision [0016](../decisions/0016-nom-nothing-to-lose.md), qui abandonne le principe « Say Again : <Ville> » de [0005](../decisions/0005-nom-say-again.md)). La règle technique reste inchangée : le pipeline de bake, les quartiers, les lieux nommés, les tables de loot et la perception textuelle sont des **données de carte** ; le code de simulation et d'IA n'en contient aucune, et rien de spécifique à Toulouse n'y est codé en dur. Toulouse est la seule ville prévue.

## Périmètre de Toulouse [Décidé]

- **Centre de Toulouse** uniquement : à l'intérieur des boulevards, la Garonne fermant le côté ouest.
- **Mur de barricades** généré automatiquement le long des boulevards ; les ponts sont barricadés. Chaque rue coupée par le mur est une entrée possible pour les hordes.
- **Intérieurs limités aux bâtiments stratégiques**, générés procéduralement sur un seul niveau (voir [21](21-interieurs-sieges.md)) ; les autres bâtiments sont des volumes pleins. **Pas d'accès à l'eau** (Garonne, canaux).
- **4 à 5 quartiers** délimités au bake (voir [19](19-quartiers-batiments.md)).
- La simulation est **entièrement 2D** ; seul le rendu est en 3D.

## Sources de données

| Donnée | Source | Licence |
|---|---|---|
| Voirie, places, POI (commerces, pharmacies), passages couverts | OpenStreetMap | ODbL — créditer « © OpenStreetMap contributors » |
| Emprise et hauteur des bâtiments | IGN BD TOPO | Licence Ouverte Etalab 2.0 — citer l'IGN |
| Arbres | Toulouse Métropole, jeu « Arbres urbains » | Licence Ouverte 2.0 |

Points d'attention :
- L'attribut `HAUTEUR` de la BD TOPO correspond à la hauteur à la gouttière ; le `height` d'OSM inclut le toit.
- Pour les arbres, un rayon de couronne par défaut selon l'essence quand la dimension manque.
- Arches et passages : tags OSM `tunnel=building_passage`, `covered=yes`.
- **Caméras de surveillance : placement procédural plausible, jamais les emplacements réels** (voir [13](13-objectif-cameras.md)).

## Repère

Lambert-93 (EPSG:2154), en mètres. Toutes les sources y sont reprojetées.

## Pipeline de bake (Python, offline)

Entrées : extraits OSM, BD TOPO (département 31), arbres urbains.

Sorties :

| Fichier | Contenu |
|---|---|
| `city.glb` | Bâtiments extrudés, fusionnés par tuile |
| `nav.bin` | Grille de navigation (1–2 m) et navmesh Recast |
| `masks.bin` | Masques bâtiments / marchable / eau / frondaisons, aux résolutions du son (1 m) et de l'odeur (2 m) |
| `zones.json` | Polygones des quartiers (4 à 5) et des lieux nommés (Capitole, Saint-Sernin, Esquirol, Carmes…) |
| `buildings.json` | Bâtiments candidats par quartier, positions des portes (OSM `entrance=*` ou façade côté rue) |
| `occluders.json` | Arbres et arches (pour la transparence) |
| `loot.json` | Tables de stock et pondérations par type OSM (le tirage se fait en début de partie) |
| `wind/*.bin` | Champs de vent précalculés (8 à 16 directions) |
| `cameras.json` + masques de visibilité | Réseau CCTV procédural, visibilité à 360° par caméra |
| `barricade.json` | Tracé du mur, entrées, postes militaires |

## Pourquoi les lieux nommés comptent

Ils ancrent la perception textuelle de Laya (« horde à 30 m, place du Capitole, sous les arcades ») et les dialogues des survivants (« on se replie vers Saint-Sernin »). C'est aussi ce qui rend les vidéos reconnaissables pour un public local.

## Sources

- Arbres urbains — data.gouv.fr : https://www.data.gouv.fr/datasets/arbres-urbains-1
- Hauteurs BD TOPO (définition, licence) — wiki OSM : https://wiki.openstreetmap.org/wiki/Organised_Editing/Activities/TomTom/Global_-_Building_Height_Imports/France_-_IGN_BD_TOPO_Building_Heights_Import
