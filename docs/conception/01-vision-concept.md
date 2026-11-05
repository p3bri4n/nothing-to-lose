# 01 — Vision et concept

[← Sommaire](README.md)

## Nom

**[Décidé]** **Say Again** : la formule radio « répétez », parce que la mécanique la plus originale du projet est la radio qui se dégrade et les ordres mal compris. Chaque ville est une variante : « Say Again : Toulouse », puis d'autres.

**[Décidé]** Accroche officielle : **« Lead or Fade: Your Command »** — le commandement qui faiblit et le signal radio qui s'évanouit ; « Your Command », l'ordre donné et l'unité commandée. Sur les visuels : « SAY AGAIN : TOULOUSE » puis « Lead or Fade. » ; formule complète en fin de vidéo et dans les bios.

[Proposé] Titres de saisons : **Last Known Position** (la traque : zombies, alphas, survivants qui disparaissent du réseau), **Nobody Left Behind** (le dilemme moral : abandonner, exclure, réintégrer). Rubrique de clips courts : **« Wait, what? »**, les malentendus radio les plus absurdes.

## Pitch

Une invasion zombie dans le centre de Toulouse, simulée en temps réel. Les infectés réagissent par **instinct** (Laya, ~30 ms par décision). Les survivants **raisonnent, se parlent par radio, se soupçonnent et se disputent** (LLM local). Un humain peut prendre le rôle du commandant à distance.

## Le concept central : System 1 contre System 2

| | Zombies | Survivants |
|---|---|---|
| Cerveau | Laya : décision rapide, probabilités calibrées | LLM : délibération lente, langage |
| Cadence | Sur événement, ~30 ms | Toutes les 2 à 5 s, plus des conseils ponctuels |
| Visible à l'écran | Barres de probabilité au-dessus de la tête | Répliques radio, sous-titres |

- **L'infection retire le System 2.** Un survivant mordu perd progressivement son LLM (répliques de plus en plus confuses pendant l'incubation) jusqu'à ne plus garder que ses réflexes Laya.
- Les survivants ont eux aussi un **System 1** (Laya, réflexes de combat) piloté par la posture que fixe leur **System 2** (LLM). Voir [05](05-ia-survivants-llm.md).

## Ce qui rend le démonstrateur novateur

1. **Un cerveau visible et honnête** : les probabilités calibrées de Laya s'affichent, et la confiance pilote l'animation (un zombie incertain hésite, un zombie sûr charge).
2. **La physique produit le récit** : ondes sonores qui ricochent, odeurs portées par le vent, radio qui se dégrade avec la distance. Les malentendus et les scènes fortes ne sont pas scriptés.
3. **La déduction sociale entre IA** : qui est infecté ? Inspections, soupçons, mensonges, exclusions.
4. **Un humain commande des IA qui n'obéissent pas toujours.**
5. **Une vraie ville** : Toulouse, ses rues, ses places, son vent d'autan.
6. **Laya en juge calibré** : ses prédictions (infection, menace) sont vérifiées après coup et comparées aux pronostics du public.

## Formats pour les réseaux sociaux

- Clips verticaux 9:16 tirés des replays, avec détection automatique des moments forts.
- Replays interactifs dans le navigateur (lien partageable, sans serveur).
- Plus tard : live avec commandant humain et/ou participation du chat.

## Mécaniques de jeu (vue d'ensemble)

- Survivants : recherche de vivres, médicaments, munitions et matériaux ; bâtiments de repos ; une antenne par quartier à tenir pendant une vague ; objectifs stratégiques.
- Perception : son (onde), odeur (champ + vent), vue (lignes de vue, caméras).
- Combat : distance (bruyant, coûteux) contre corps à corps (silencieux, risqué).
- Infection : morsure certaine, griffure cachée et probabiliste.
- États internes : stress, fatigue, confiance, relations.
- Social : conseil, inspection, disputes, abandon, exclusion.
