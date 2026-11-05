# 01 — Vision et concept

[← Sommaire](README.md)

## Nom

**[Décidé]** **Nothing To Lose** : jeu de mots avec Toulouse. Le nom public ne désigne que Toulouse : il n'annonce plus de variante par ville (décision [0016](../decisions/0016-nom-nothing-to-lose.md), qui remplace « Say Again », [0005](../decisions/0005-nom-say-again.md)). La radio qui se dégrade et les ordres mal compris restent au cœur des mécaniques ([08](08-radio.md)).

**[Décidé]** Accroche : deux textes officiels, à deux usages.
- **Texte long** : le speech ci-dessous (décision [0017](../decisions/0017-accroche-le-speech.md), qui remplace « Lead or Fade: Your Command », [0006](../decisions/0006-accroche-lead-or-fade.md)).
- **Accroche courte** : « Command humanity's last hope », sous-titre du key art (décision [0019](../decisions/0019-accroche-command-humanity-last-hope.md)). Titre public complet : « Nothing To Lose — Command humanity's last hope ».
- **Signature de la description** : « Commandez avec brio ! », dernière phrase du speech, reste la signature française de la description (précision de l'utilisateur, 2026-11-05) ; elle n'est pas la formule courte.

> « Invasion zombie mondiale, Toulouse est le dernier bastion de l'humanité. Mais une brèche durant la nuit a vu des centaines d'infectés entrer dans la ville, notre groupe de combattants est le dernier espoir de l'humanité. Ceux qui ont déjà tout perdu (familles, maisons, rêves), perdront-ils aussi leur humanité pour la préserver ? Vous seul pourrez les guider, alors commandez avec brio ! »

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
