<!--
Sync Impact Report
==================
Version change: (aucune) → 1.0.0
Rationale: Adoption initiale. Le fichier ne contenait que le scaffold vierge
(placeholders [PRINCIPLE_N_NAME]) ; aucune valeur de projet n'a été écrasée.

Principes ajoutés:
- I. Isolation des données par utilisateur (NON-NÉGOCIABLE)
- II. Secrets chiffrés au repos
- III. Vérification avant merge
- IV. Payload brut préservé et synchronisation idempotente
- V. Résilience de la synchronisation

Principes modifiés: aucun (première rédaction)
Principes renommés: aucun
Principes supprimés: aucun

Sections ajoutées:
- Contraintes techniques (SECTION_2)
- Workflow de développement (SECTION_3)
- Governance

Sections supprimées: aucune

Placeholders restants: aucun

TODO différés: aucun

Notes de dérivation:
- Principes I, II, IV, V inférés de README.md, CLAUDE.md et de la structure
  backend/ (auth.py, garmin_client.py, garmin_manager.py, scheduler.py, routes/).
- Principe III arbitré explicitement par l'utilisateur (option « vérification
  pragmatique ») : le repo ne contient aucun test automatisé à ce jour.
- Date de ratification = date d'adoption de la constitution (2026-08-17), et non
  la date du premier commit du projet (2026-06-22).
-->

# Garmin Dashboard Constitution

## Core Principles

### I. Isolation des données par utilisateur (NON-NÉGOCIABLE)

Le dashboard est multi-utilisateurs et manipule des données de santé. Aucune donnée
ne MUST jamais franchir la frontière d'un compte.

- Toute table portant des données Garmin MUST avoir une colonne `user_id` avec une
  clé étrangère vers `users`.
- Toute route servant ces données MUST déclarer `Depends(get_current_user)` et MUST
  filtrer chaque requête SQLAlchemy par le `user_id` du token — jamais par un
  identifiant reçu du client.
- Un identifiant de ressource fourni par le client (activité, jour, dashboard) MUST
  être vérifié comme appartenant à l'utilisateur courant avant lecture ou écriture ;
  une ressource d'autrui MUST retourner 404, jamais 403 (pas de fuite d'existence).
- Le `GarminManager` MUST instancier un `GarminClient` distinct par utilisateur et
  MUST invalider l'instance dès que les credentials changent.

*Rationale : une seule requête non filtrée expose l'historique de santé complet d'un
tiers. C'est le seul défaut de ce projet qui soit irréparable après coup.*

### II. Secrets chiffrés au repos

- Les mots de passe Garmin MUST être chiffrés avec Fernet (`GARMIN_CREDENTIAL_KEY`)
  avant insertion en base et MUST n'être déchiffrés qu'au moment d'ouvrir une session
  Garmin.
- Les mots de passe de compte MUST être hachés avec bcrypt. Aucun mécanisme
  réversible n'est acceptable.
- Aucune réponse d'API, aucun log (y compris Discord), aucune trace d'exception MUST
  contenir un mot de passe, un token JWT, une clé Fernet ou un cookie de session
  Garmin — en clair comme chiffré.
- `JWT_SECRET_KEY` et `GARMIN_CREDENTIAL_KEY` MUST provenir de l'environnement. Une
  valeur par défaut codée en dur est interdite : l'application MUST refuser de
  démarrer si l'une des deux est absente.
- `backend/.env` et `*.db` MUST rester hors du dépôt.

*Rationale : les credentials Garmin donnent accès au compte Garmin réel de
l'utilisateur, bien au-delà du périmètre de ce dashboard.*

### III. Vérification avant merge

- Toute modification frontend MUST passer `npm run type-check` sans erreur.
- Tout endpoint nouveau ou modifié MUST être vérifié manuellement : requête réelle
  avec un token valide, puis contrôle de l'affichage dans l'UI concernée.
- Toute modification touchant l'authentification, le filtrage `user_id` ou le
  chiffrement MUST être vérifiée avec au moins deux comptes distincts.
- Les tests automatisés SHOULD être ajoutés sur la logique de calcul (score de forme,
  CTL/ATL, agrégations hebdomadaires, parsing des payloads Garmin), qui est la partie
  la plus dense en règles métier et la moins visible à l'œil nu.

*Rationale : projet mono-développeur sans suite de tests. La vérification exigée est
celle qui est réellement tenable ; l'inflation d'obligations non appliquées ne
protège rien.*

### IV. Payload brut préservé et synchronisation idempotente

- Chaque enregistrement issu de Garmin MUST conserver le payload d'origine dans une
  colonne `raw` JSON, en plus des colonnes dérivées.
- Toute nouvelle métrique MUST d'abord être cherchée dans les `raw` déjà stockés
  avant d'envisager une re-synchronisation complète.
- La synchronisation MUST être un upsert par `(user_id, clé naturelle)` : relancer
  une synchro sur une période déjà couverte MUST être sans effet de bord ni doublon.
- Les routes de lecture MUST servir la base locale. Aucun appel à l'API Garmin MUST
  être déclenché dans le cycle requête/réponse d'un utilisateur.

*Rationale : l'API Garmin est non contractuelle, limitée en débit et sujette au
bannissement. Le `raw` rend les nouvelles métriques rétroactives sans re-synchro.*

### V. Résilience de la synchronisation

- `sync_all_users()` MUST isoler chaque utilisateur : l'échec de l'un MUST être
  journalisé et MUST laisser les suivants se synchroniser.
- Un échec d'authentification Garmin MUST déclencher le cooldown existant plutôt
  qu'une boucle de reconnexion.
- Un utilisateur sans credentials Garmin, ou dont la synchro échoue, MUST voir une
  UI fonctionnelle : état vide explicite, jamais une page en erreur ou un chargement
  infini.
- Les erreurs de synchronisation MUST être journalisées en français avec le contexte
  utile (utilisateur concerné, période, cause).

*Rationale : la synchro tourne sans surveillance via APScheduler ; une défaillance
silencieuse ou globale se découvre des semaines plus tard, en données manquantes.*

## Contraintes techniques

- **Stack imposée** : backend Python 3.11+ / FastAPI / SQLAlchemy / SQLite /
  APScheduler ; frontend Vue 3 / Vite / TypeScript / Pinia / ApexCharts. Introduire
  un framework, un ORM ou une librairie de graphiques concurrents MUST faire l'objet
  d'un amendement à cette constitution.
- **Langue** : le code, les commentaires, les logs, les messages d'erreur et l'UI
  MUST être en français, accents compris. Les identifiants techniques issus de
  librairies tierces restent dans leur forme d'origine.
- **Accès HTTP frontend** : tout appel MUST passer par l'instance axios partagée
  `api.ts` (Bearer token + redirection 401). Aucun `fetch` ou `axios` direct.
- **Forme des réponses** : les routes retournent des dicts sérialisés manuellement ;
  Pydantic est réservé à la validation des entrées POST/PUT.
- **Responsive** : toute vue nouvelle ou modifiée MUST rester utilisable en largeur
  mobile (bottom nav, tableaux scrollables, modals adaptés). Les couleurs et espacements
  MUST utiliser les design tokens de `assets/main.css`, jamais de valeur en dur.
- **Configuration** : tout nouveau paramètre d'exécution MUST être une variable
  d'environnement documentée dans `README.md` et `backend/.env.example`, avec un
  défaut sûr quand il n'est pas critique.

## Workflow de développement

- Le travail se fait sur une branche dédiée puis en pull request vers `main` ; on ne
  commit pas directement sur `main`.
- Le workflow Spec Kit s'applique aux fonctionnalités : `/speckit-specify` →
  `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. Les corrections de bug et
  ajustements d'UI mineurs peuvent s'en dispenser.
- `/speckit-analyze` SHOULD être exécuté avant `/speckit-implement` sur toute
  fonctionnalité touchant l'authentification, le filtrage `user_id` ou la synchro.
- `CLAUDE.md` et `README.md` MUST être mis à jour dans la même PR que le changement
  qui les rend obsolètes (nouvelle route, nouveau store, nouvelle variable d'env).
- Une migration de schéma MUST être décrite dans la PR : colonnes ajoutées, valeur de
  remplissage pour les lignes existantes, impact sur `garmin.db` en production.

## Governance

Cette constitution prime sur toute autre pratique du projet. En cas de contradiction
entre elle et `CLAUDE.md`, un commentaire de code ou une habitude établie, c'est elle
qui tranche.

**Amendements** : toute modification MUST être portée par une PR dédiée modifiant ce
fichier, avec la justification du changement et le report de version mis à jour en
en-tête. Un principe ne MUST jamais être contourné, réinterprété ou ignoré
silencieusement dans une spec, un plan ou une tâche : soit la fonctionnalité s'y plie,
soit la constitution est amendée d'abord.

**Versionnement** : sémantique. MAJOR = suppression ou redéfinition incompatible d'un
principe ; MINOR = ajout d'un principe ou d'une section, ou extension matérielle d'une
règle ; PATCH = clarification, reformulation, correction sans effet normatif.

**Conformité** : chaque PR MUST être relue au regard des principes I et II au minimum.
Toute complexité ajoutée MUST être justifiée dans la description de la PR — à défaut,
la version simple l'emporte. `CLAUDE.md` reste le guide opérationnel au quotidien ;
cette constitution en fixe les limites non négociables.

**Version**: 1.0.0 | **Ratified**: 2026-08-17 | **Last Amended**: 2026-08-17