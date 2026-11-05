# 0005 — Nom du projet : « Say Again », avec une variante par ville

- **Date** : 2026-11-05
- **Statut** : remplacée par [0016](0016-nom-nothing-to-lose.md) (« Nothing To Lose », décidé le 2026-11-05). Le contenu ci-dessous est conservé à titre historique.
- **Contexte** : le projet avait un nom de travail (« Zombies Laya »). Il lui faut un nom public, mémorable, qui dise ce qui le distingue, et disponible.
- **Options présentées** : The Last Command, We Shall Survive, At Your Command, Thinking Fast and Dead, Squelch, Dead Air, Do You Copy?, Wilco?, Last Known Position, Until Relieved, Those Who Remain, Nobody Left Behind, Wait What?, Say Again. Vérifications faites : « Do You Copy? » (plusieurs jeux, dont un jeu d'horreur radio au concept proche), « Those Who Remain » (jeu commercial, marque déposée), « Wait, What? » (contenu de jeu sur les malentendus), « Last Known Position » (podcast et série Amazon), « No One Left Behind » (film, jeux, série documentaire) sont encombrés ; « Say Again » ne correspond qu'à un petit jeu narratif indépendant.
- **Recommandation des agents** : Say Again — il raconte la mécanique la plus originale (la radio qui se dégrade et les ordres mal compris) et il est le moins encombré.
- **Décision de l'utilisateur** : « Say Again : Toulouse, puis des variantes par ville ».
- **Conséquences** :
  - dépôt `say-again`, projet Cloudflare Pages `say-again`, état Terraform dans `~/.local/share/terraform/say-again/` ;
  - le nom public d'une version est « Say Again : <Ville> » ;
  - la ville est une donnée : le pipeline de carte, les quartiers, les lieux nommés et la perception textuelle ne doivent rien coder en dur sur Toulouse.
- **Non décidé à ce stade (propositions)** : titres de saisons (« Last Known Position », « Nobody Left Behind ») et rubrique de clips courts « Wait, what? ».
- **Documents mis à jour** : `README.md`, `CLAUDE.md`, sous-agents, `justfile`, `infra/terraform/`, `docs/technique/ci-cd.md`, `docs/conception/`.
- **À vérifier avant publication** : disponibilité des noms de domaine et des comptes de réseaux sociaux, recherche de marque (INPI / EUIPO). Point relevé le 2026-11-05 : un podcast de leadership « Say Again » (et une collection de livres « Say Again Essentials ») existe ; autre domaine, risque de confusion faible, à inclure dans la recherche de marque.
