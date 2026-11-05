# Démonstrateur IA « Say Again » — Dossier de conception

**Say Again** — simulateur urbain de combat entre survivants humains et infectés. Première variante : **« Say Again : Toulouse »**, dans le centre de Toulouse ; d'autres villes suivront. Les zombies sont animés par **Laya** (modèle de décision « System 1 ») et les survivants par un **LLM local** (« System 2 »). Objectif : un démonstrateur novateur, pensé pour avoir un fort impact sur les réseaux sociaux.

> Statut : conception — version du 5 novembre 2026.
> Convention : **[Décidé]** = validé ; **[Proposé]** = recommandation en attente de validation ; **[Ouvert]** = question à trancher.

## Sommaire

| # | Document | Contenu |
|---|---|---|
| 01 | [Vision et concept](01-vision-concept.md) | Pitch, System 1 / System 2, axes de viralité |
| 02 | [Carte et données](02-carte-donnees.md) | Toulouse, périmètre, pipeline de bake, licences |
| 03 | [Architecture technique](03-architecture-technique.md) | Blocs, Rust/WASM, déterminisme, journal, VRAM |
| 04 | [IA zombies : Laya](04-ia-laya.md) | Capacités, limites, schémas, fine-tuning, broker |
| 05 | [IA survivants : LLM](05-ia-survivants-llm.md) | Double cerveau, conseil, croyances, pare-feu d'information |
| 06 | [Son](06-son.md) | Solveur d'onde FDTD, échos, perception |
| 07 | [Odeur et vent](07-odeur-vent.md) | Advection-diffusion, vent canalisé, vent d'autan |
| 08 | [Radio et communications](08-radio.md) | Propagation, dégradation audio, `***`, TTS/ASR |
| 09 | [Ressources et loot](09-ressources-loot.md) | Vivres, médicaments, munitions, fouille |
| 10 | [Combat et infection](10-combat-infection.md) | Distance / corps à corps, morsure, griffure, inspection |
| 11 | [Stress, fatigue et rupture](11-stress-fatigue-rupture.md) | Jauges, désobéissance, point de rupture |
| 12 | [Dynamique sociale](12-dynamique-sociale.md) | Déduction, confiance, disputes, abandon, exclusion |
| 13 | [Objectif : piratage des caméras](13-objectif-cameras.md) | Tenir une zone, réseau CCTV imparfait |
| 14 | [Commandant humain](14-commandant-humain.md) | Ordres vocaux/textuels, bodycams, brouillard de guerre |
| 15 | [Rendu et viewer](15-rendu-viewer.md) | Vue 3D de dessus, transparences, overlays, clips |
| 16 | [Jalons et périmètre](16-jalons.md) | Prototype P0 → P5, puis J0 → J8, MVP vs saison 2 |
| 17 | [Questions ouvertes et décisions](17-questions-ouvertes.md) | Questions restantes, journal des décisions |
| 18 | [Moral](18-moral.md) | Érosion avec le temps, deuil, petites victoires |
| 19 | [Quartiers, bâtiments et information](19-quartiers-batiments.md) | Zones, bâtiments d'intérêt aléatoires, antennes, essais de portes, embuscades à la sortie |
| 20 | [Progression : XP et compétences](20-progression-xp.md) | Débutants au départ, XP, paliers, compétences, alphas, ruche |
| 21 | [Intérieurs et sièges](21-interieurs-sieges.md) | Bâtiments stratégiques, renforcement, assaut d'alpha, sorties de secours |
| 22 | [Boucle de retour](22-boucle-de-retour.md) | Headless, invariants, indicateurs, captures, inspection, retour humain |

## Décisions structurantes

- **[Décidé]** Centre de Toulouse uniquement, ceinturé de barricades ; seuls les bâtiments stratégiques ont un intérieur (un seul niveau) ; eau infranchissable.
- **[Décidé]** Ville découpée en 5 quartiers ; bâtiments d'intérêt tirés au hasard par quartier.
- **[Décidé]** Les zombies qui voient des survivants entrer dans un bâtiment peuvent les attendre à la sortie.
- **[Décidé]** Tir ami possible : les lignes de tir comptent.
- **[Décidé]** Survivants débutants au départ ; chaque entité, zombies compris, gagne de l'XP ; chaque palier débloque un niveau de compétence (survivants) ou de nouveaux comportements (zombies).
- **[Décidé]** Zombies alphas : un pour X zombies, un par quartier au maximum ; apparence et caractéristiques supérieures, sens très développés, rapides ; ils commandent leur horde. Égaux entre eux, ils peuvent coopérer sans commander la horde d'un autre ; l'intérêt de la ruche l'emporte toujours.
- **[Décidé]** Les alphas crient pour donner des ordres vocaux à leur horde ; seuls les zombies qui entendent le cri le reçoivent.
- **[Décidé]** Compétences et spécialisations évolutives.
- **[Décidé]** Un alpha peut forcer l'entrée d'un bâtiment stratégique : combat en intérieur, renforcement coûteux en effort et en temps, sorties de secours d'autant plus rares que le bâtiment est stratégique.
- **[Décidé]** Vue 3D de dessus simplifiée, transparence sous les arbres et les arches.
- **[Décidé]** Son et odeur bloqués par les bâtiments ; le son se comporte comme une onde (réflexions, diffraction).
- **[Décidé]** Morsure = transformation certaine (durée selon la santé) ; griffure = infection cachée et probabiliste, réduite par les médicaments.
- **[Décidé]** Radio réaliste avec grésillement ; dégradation des échanges en `***`.
- **[Décidé]** Projet non monétisé.
- **[Décidé]** Clips d'abord, avec rendu en deux phases (partie jouée, puis re-synthèse des voix).
- **[Décidé]** Cœur de simulation en **Rust**, compilé en **WebAssembly** (Node + navigateur).
- **[Décidé]** Commandant humain distant, bodycams, objectif de piratage des caméras.
- **[Décidé]** Stress, fatigue, disputes, rupture ; indice de confiance ; abandon et exclusion.
- **[Décidé]** Un exclu peut être réintégré après une bonne action pour le groupe.
- **[Décidé]** Moral : chaque mort affecte le groupe ; massacres de zombies, ressources et repos le relèvent un peu ; il baisse avec la durée de la partie.
- **[Décidé]** Phase 0 (prototype P0 à P5) avant le MVP, pour valider le concept avec des mécaniques simplifiées.
- **[Décidé]** MVP = jalons J0 à J4c, intérieurs et sièges compris ; le reste en « saison 2 ».
- **[Décidé]** Boucle de retour outillée dès P0 (headless, invariants, indicateurs, captures, retour humain), pour un développement avec Claude Code.
- **[Décidé]** Vitesse du son ralentie (~50 m/s) ; rendu Three.js ; 5 quartiers.
- **[Décidé]** Antennes : une par quartier, à découvrir puis à tenir pendant toute une vague de zombies pour révéler l'emplacement des bâtiments d'intérêt du quartier.
- **[Décidé]** Cinq types de bâtiments d'intérêt (vivres, soins, matériaux, munitions, repos) ; tous les autres sont inexplorables ; sans les données de l'antenne, on teste les bâtiments un par un en s'exposant.
- **[Décidé]** Effectifs de départ : ~2 000 à 3 000 zombies, ~100 civils, 6 à 10 héros LLM (4 à 6 en live).
- **[Décidé]** Accroche officielle : **« Lead or Fade: Your Command »**.
- **[Décidé]** Nom du projet : **Say Again**, avec une variante par ville (« Say Again : Toulouse »). La ville est une donnée : rien de spécifique à Toulouse n'est codé en dur hors des données de la carte.
- **[Décidé]** Commandant local d'abord ; invités à distance plus tard.
- **[Décidé]** CI/CD : GitHub configuré par Terraform (état local), dépôt public, runner GPU auto-hébergé hors pull requests, viewer sur Cloudflare Pages.

## Modèle d'IA

**[Décidé]** « Laya » désigne le **modèle de décision open-weight de Convai Innovations** (sept. 2026), et non le moteur de jeu LayaAir. Voir [04-ia-laya.md](04-ia-laya.md).
