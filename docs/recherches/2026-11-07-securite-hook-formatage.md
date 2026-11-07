# Recherche : sécurité du hook de formatage (prettier 3.9.10, mise 2026.11.0, Claude Code)

- **Date de la recherche** : 2026-11-07
- **Demandé par** : session principale (tâche de vérification avant décision)
- **Périmètre** : faits sourcés sur 4 questions. Aucune décision prise ici.

## Versions vérifiées

| Outil | Version | Preuve | Date |
|---|---|---|---|
| prettier | 3.9.10 | Registre npm `latest` = 3.9.10 ([registre npm](https://registry.npmjs.org/prettier)) ; métadonnées de la version ([registre npm, 3.9.10](https://registry.npmjs.org/prettier/3.9.10)) ; page de release GitHub ([release 3.9.10](https://github.com/prettier/prettier/releases/tag/3.9.10)) | Release du « 10 octobre » 2026 (année issue du pied de page de la page GitHub, non du corps de la page) |
| mise | 2026.11.0 | Page de release GitHub ([jdx/mise v2026.11.0](https://github.com/jdx/mise/releases/tag/v2026.11.0)) | Publiée le « 3 novembre » (année 2026 issue du pied de page) |

Remarques sur les sources :
- Pour prettier 3.9.10, je n'ai pas vu de date dans le champ `time` du registre (champ absent de la réponse obtenue).
- Les recherches web générales n'ont pas trouvé de notes de version 3.9.10 hors GitHub ; une recherche a seulement trouvé des mentions 3.9.6 (Renovate).

## Question 1 : Prettier, recherche de configuration avec `--config`, `--no-config`, `--no-editorconfig`

**Réponse courte** : avec `--config <fichier>`, la recherche automatique est sautée ; `prettier.config.js` du dossier du fichier n'est alors pas lu. Avec `--no-config` (CLI), aucune configuration n'est lue, ni fichier de configuration ni `.editorconfig`. Sans option, un `prettier.config.js` présent dans le dossier du fichier (ou un parent) est bien lu, et s'il est en JavaScript il est exécuté.

**Détails** :
- Liste des noms de fichiers recherchés (documentation officielle, ordre décroissant de priorité) : clé `prettier` de `package.json`/`package.yaml`, `.prettierrc` (JSON/YAML), `.prettierrc.json|yml|yaml|json5`, `.prettierrc.js|ts`, `prettier.config.js|ts`, variantes `.mjs`/`.mts`, `.cjs`/`.cts`, `.prettierrc.toml`. La recherche part du dossier du fichier formaté et remonte l'arborescence. Source : [Prettier, Configuration File](https://prettier.io/docs/configuration) (consultée 2026-11-07, version « stable » de la doc, sans numéro de version affiché).
- La même page indique que `.editorconfig` est lu, mais que ses propriétés sont remplacées par `.prettierrc`, et que sa recherche s'arrête à la racine du projet. Elle indique aussi que Prettier ne supporte intentionnellement aucune configuration globale.
- **Option `--config <path>`** : la documentation CLI dit qu'elle indique à Prettier le fichier à utiliser ; elle ne dit pas explicitement qu'elle désactive la recherche. Source : [Prettier, CLI](https://prettier.io/docs/cli) (consultée 2026-11-07).
- **Code source (branche `main`, consulté 2026-11-07)** :
  - Dans `src/cli/options/get-options-for-file.js` : si `context.argv.config === false` (donc `--no-config`), le code journalise « skip loading config file » et renvoie `null` **avant** tout appel à `resolveConfig`. Donc, avec `--no-config`, ni la configuration ni `.editorconfig` ne sont lus. Le même fichier passe `config: context.argv.config` et `editorconfig: context.argv.editorconfig` à `resolveConfig`.
  - Dans `src/config/resolve-config.js` : la recherche n'a lieu que si `!configFile` (donc si aucun chemin n'est donné). Si `config` est fourni, la recherche est sautée et le fichier indiqué est chargé directement.
  - Toujours dans `resolve-config.js` : `loadEditorconfig` est lancé en parallèle, qu'un `--config` soit fourni ou non ; il ne dépend que de `options.editorconfig`. Donc **avec `--config`, `.editorconfig` reste lu** sauf si `--no-editorconfig` est passé. Les valeurs `.editorconfig` sont fusionnées d'abord et écrasées par la configuration Prettier.
  - `--no-editorconfig` ne désactive que `.editorconfig` (doc CLI : « Don't take `.editorconfig` into account when parsing configuration »). Il ne désactive pas la recherche de fichiers de configuration Prettier.
- **Point d'attention** : `resolve-config.js` ne contient pas de traitement explicite de `config === false`. Si on appelle l'API `resolveConfig(file, { config: false })` directement (hors CLI), la valeur `false` est traitée comme absente et la recherche a lieu. La protection pour `--no-config` est donc dans la CLI, pas dans l'API. Je n'ai pas pu lire le module `prettier-config/index.js` qui contient `searchPrettierConfig`.

**Limites** :
- Le code consulté est celui de la branche `main` (et non celui du tag 3.9.10 ; je n'ai pas pu le lire). Il faut le confirmer sur le tag si la question devient décisive.
- La doc officielle ne dit pas explicitement que `--config` désactive la recherche ; c'est la lecture du code qui le montre.

**Confiance** : moyenne. Documentation officielle pour la liste des noms et la remontée de l'arborescence ; lecture du code source (branche `main`, pas le tag) pour le comportement de `--config`, `--no-config` et `--no-editorconfig`.

## Question 2 : mise, réglage d'installation automatique pendant `mise exec`

**Réponse courte** : le réglage est `exec_auto_install` (variable `MISE_EXEC_AUTO_INSTALL`), valeur par défaut `true`. Il est sans effet si le réglage global `auto_install` (variable `MISE_AUTO_INSTALL`, défaut `true`) vaut `false`.

**Détails** :
- Page des réglages : `auto_install` (`MISE_AUTO_INSTALL`, défaut `true`) : installe les outils manquants quand une commande en a besoin ; `false` désactive aussi `exec_auto_install`, `not_found_auto_install` et `task.run_auto_install`. `exec_auto_install` (`MISE_EXEC_AUTO_INSTALL`, défaut `true`) : installe les outils manquants lors d'un `mise exec` ; sans effet si `auto_install` vaut `false`. `auto_install_disable_tools` (`MISE_AUTO_INSTALL_DISABLE_TOOLS`, liste séparée par des virgules) : liste d'outils exclus de l'installation automatique. Source : [mise, Settings](https://mise.jdx.dev/configuration/settings.html) (consultée 2026-11-07).
- Page `mise exec` : indique que par défaut `mise exec` installe d'abord les outils manquants, et que ce comportement se désactive avec `exec_auto_install` ou `auto_install`. **Cette page ne cite pas de variable d'environnement** pour ces réglages. Source : [mise, exec](https://mise.jdx.dev/cli/exec.html) (consultée 2026-11-07).
- Pas de numéro de version trouvé dans ces deux pages pour ces réglages.

**Contradiction mineure entre sources** : la page des réglages donne les variables `MISE_AUTO_INSTALL` et `MISE_EXEC_AUTO_INSTALL` ; la page `exec` n'en mentionne aucune. Je retiens la page des réglages, qui est la référence de configuration, avec une confiance moyenne.

**Confiance** : moyenne (une page de référence, plus une page de commande qui concorde sur le comportement mais pas sur les variables).

## Question 3 : mode paranoïaque et `mise trust`

**Réponse courte** : le mode paranoïaque existe (`paranoid`, variable `MISE_PARANOID`, défaut `false`). Il est réservé à la configuration globale ou système. En mode paranoïaque, `mise trust` lie la confiance au contenu du fichier. Hors de ce mode, la documentation décrit une approbation attachée au chemin du fichier, sans dire explicitement qu'un hash du contenu est stocké ; je n'ai pas trouvé de confirmation écrite de ce point.

**Détails** :
- `paranoid` : type `boolean | string[]`, défaut `false`, variable `MISE_PARANOID`, réglage global seulement (ignoré avec un avertissement dans un fichier de projet). `true` active toutes les protections ; une liste n'active que les catégories nommées : `config`, `env_files`, `plugins`, `provenance`. La catégorie `config` exige une approbation liée au contenu des fichiers de configuration de projet. Source : [mise, Settings](https://mise.jdx.dev/configuration/settings.html) (consultée 2026-11-07).
- `trusted_config_paths` (`MISE_TRUSTED_CONFIG_PATHS`, global seulement, défaut `[]`) : liste de répertoires approuvés, y compris les projets créés plus tard dedans. La doc précise qu'en mode paranoïaque, ces chemins restent approuvés **sans lier la confiance au contenu**. Même source.
- `yes` (`MISE_YES`, défaut `false`) : répond oui aux confirmations, aussi activé automatiquement quand `CI` est défini ; inclut la demande de confiance, sauf en mode paranoïaque. Même source.
- `mise trust` (page de commande) : la confiance permet à mise de charger les parties d'un fichier de configuration qui peuvent exécuter du code ou modifier l'environnement. Options : `--all`/`-a`, `--untrust`, `--show`, `--ignore`. Le texte décrit une approbation **par chemin de fichier** et ne mentionne pas de hash. En mode paranoïaque, la confiance est « tied to the file's contents » pour toute configuration hors globale/système. Sans chemin, `mise trust` approuve aussi les fichiers d'environnement lus par la configuration. Source : [mise, trust](https://mise.jdx.dev/cli/trust.html) (consultée 2026-11-07).
- Confiance par défaut : les fichiers « simples » (uniquement `min_version`, `[tools]` à versions simples, `[tasks]` sans `secrets`) n'ont pas besoin de confiance, sauf en mode paranoïaque. Les commandes `mise run`, `mise install`, `mise exec`, `mise watch` et les raccourcis de tâches approuvent automatiquement la configuration active. Même source. **Point d'attention** : `mise exec` est donc couvert par une confiance automatique.

**Limites** :
- Je n'ai pas pu lire la section « mode sûr » ou « lockfile » en détail, ni les notes d'évolution de la page des réglages au-delà de ce qui est listé.
- La formulation « approbation par chemin » vient de l'absence de mention de hash, pas d'une phrase explicite ; c'est une lecture, à confirmer.
- Notes de version 2026.11.0 (page GitHub, consultée 2026-11-07) : mode sûr `MISE_SAFE=1` (le `mise.lock` de projet ne choisit plus les URLs de téléchargement), `.miserc.toml` de projet ne peut plus désactiver les environnements globaux sans approbation, `paranoid = true` cité pour `.miserc.toml`. Ces notes ne décrivent pas explicitement le hash de confiance.

**Confiance** : élevée pour l'existence de `paranoid`, `MISE_PARANOID`, leur défaut et la liaison au contenu en mode paranoïaque (page de réglages et page `trust`, concordantes). Moyenne à faible pour « la confiance par défaut porte sur le chemin seul, sans hash » (aucune phrase explicite ; à revérifier en lisant le code de mise ou en testant avec `mise trust --show`).

## Question 4 : Claude Code, matcher `Write|Edit|MultiEdit` et sous-agents

**Réponse courte** : la doc officielle décrit un matcher fait d'une liste de noms exacts séparés par `|` ou `,` ; une regex n'est utilisée que si le motif contient d'autres caractères. Les hooks du projet **s'appliquent aux appels d'outils des sous-agents**. `MultiEdit` n'apparaît pas dans la liste des outils de la référence officielle consultée.

**Détails** :
- Matcher : la doc dit que les caractères autorisés pour une liste exacte sont lettres, chiffres, `_`, `-`, espaces, `,` et `\|`. Elle donne l'exemple `"matcher": "Edit|Write"`, et précise que « Edit\|Write » et « Edit, Write » correspondent à l'un des deux outils exactement. Une chaîne qui contient d'autres caractères (ex. `.` ou `^`) est traitée comme une regex non ancrée (`Edit.*` correspond aussi à `NotebookEdit`). Donc `Write|Edit|MultiEdit`, composé uniquement de lettres et de `|`, est lu comme une liste exacte de trois noms. Source : [Claude Code, Hooks](https://code.claude.com/docs/en/hooks) (consultée 2026-11-07 ; page sans date, version de référence v2.1.314 citée dans la page).
- Sous-agents : la page dit que les hooks issus des fichiers de réglages, de la politique gérée et des plugins s'exécutent aussi dans les sous-agents ; quand un sous-agent appelle un outil, `PreToolUse` et `PostToolUse` se déclenchent avec les mêmes hooks configurés, et l'entrée porte `agent_id` et `agent_type`. Même source.
- Hooks dans le frontmatter d'un sous-agent : exécutés pendant que le sous-agent tourne ; les hooks de frontmatter d'un sous-agent de projet ne s'exécutent qu'après acceptation de la boîte de dialogue de confiance de l'espace de travail. Même source.
- Outils : la [référence des outils](https://code.claude.com/docs/en/tools-reference) (consultée 2026-11-07) liste notamment `Write`, `Edit`, `NotebookEdit`, `TodoWrite`, `ExitWorktree`. Une recherche textuelle sur la page n'a trouvé **aucune occurrence de `MultiEdit`**. Donc la présence de `MultiEdit` dans le matcher n'est pas attestée par la doc ; c'est au mieux un nom inutile, au pire un nom d'outil qui n'existe pas dans cette version.

**Limites** :
- La date de la page hooks n'est pas indiquée ; la version citée est v2.1.314. La référence des outils ne donne pas non plus de date.
- Je n'ai pas vérifié la version exacte de Claude Code installée dans le projet.

**Confiance** : élevée pour la syntaxe du matcher et pour l'application des hooks aux sous-agents (doc officielle, un seul passage cité mais explicite). Moyenne pour l'absence de `MultiEdit` (recherche sur une page de référence, pas de changelog consulté).

## Incertitudes et points à revérifier

1. Prettier : confirmer sur le **tag 3.9.10** (et pas sur `main`) le comportement de `--no-config` dans `src/cli/options/get-options-for-file.js` et de `--config` dans `src/config/resolve-config.js`.
2. mise : vérifier le comportement par défaut de la confiance (chemin ou hash) en lisant le code de mise ou en testant `mise trust --show` dans un répertoire de test.
3. mise : la page `exec` ne cite pas les variables d'environnement, à confirmer par un test (`MISE_EXEC_AUTO_INSTALL=0 mise exec -- <outil>`).
4. Claude Code : vérifier dans la version installée si un outil `MultiEdit` existe encore.

## Sources

- [Prettier, Configuration File](https://prettier.io/docs/configuration) (doc stable, consultée 2026-11-07)
- [Prettier, CLI](https://prettier.io/docs/cli) (doc stable, consultée 2026-11-07)
- [Prettier, src/config/resolve-config.js (branche main)](https://raw.githubusercontent.com/prettier/prettier/main/src/config/resolve-config.js) (consultée 2026-11-07)
- [Prettier, src/cli/options/get-options-for-file.js (branche main)](https://raw.githubusercontent.com/prettier/prettier/main/src/cli/options/get-options-for-file.js) (consultée 2026-11-07)
- [Prettier, release 3.9.10 (GitHub)](https://github.com/prettier/prettier/releases/tag/3.9.10) (release du 10 octobre 2026, selon le pied de page)
- [Registre npm, prettier](https://registry.npmjs.org/prettier) et [registre npm, prettier 3.9.10](https://registry.npmjs.org/prettier/3.9.10) (consultés 2026-11-07 ; tarball `prettier-3.9.10.tgz`)
- [mise, Settings](https://mise.jdx.dev/configuration/settings.html) (consultée 2026-11-07)
- [mise, trust](https://mise.jdx.dev/cli/trust.html) (consultée 2026-11-07)
- [mise, exec](https://mise.jdx.dev/cli/exec.html) (consultée 2026-11-07)
- [mise, release v2026.11.0 (GitHub)](https://github.com/jdx/mise/releases/tag/v2026.11.0) (publiée le 3 novembre 2026, selon le pied de page)
- [Claude Code, Hooks](https://code.claude.com/docs/en/hooks) (sans date ; v2.1.314 citée, consultée 2026-11-07)
- [Claude Code, Tools reference](https://code.claude.com/docs/en/tools-reference) (sans date, consultée 2026-11-07)
