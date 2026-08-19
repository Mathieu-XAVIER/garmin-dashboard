# Implementation Plan: Retrait des dashboards personnalisés

**Branch**: `001-retrait-dashboards-perso` | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-retrait-dashboards-perso/spec.md`

## Summary

Retrait intégral de la fonctionnalité de tableaux de bord personnalisés (widgets configurables)
et, par ricochet, de la prépa handball devenue inatteignable. L'approche est un retrait en
quatre couches, de la plus visible à la plus profonde : d'abord la surface d'interface (US1),
puis les opérations de service (US2), puis le schéma et la documentation (US3), enfin le code
inatteignable de la prépa handball (US4).

Le point technique déterminant est la fonction de migration automatique
`_migrate_handball_to_custom_dashboards()` : elle recrée au démarrage le tableau de bord et ses
widgets pour chaque utilisateur ayant des identifiants Garmin. **Tant qu'elle existe, toute
suppression de données est annulée au lancement suivant.** Elle doit donc être retirée avant ou
en même temps que la migration destructive, jamais après.

Volume : 16 endpoints supprimés (13 dashboards + 3 handball), 4 tables supprimées, 15 fichiers
supprimés, 10 fichiers nettoyés partiellement, 1 fichier créé, ~91 lignes de migration retirées.
Soit 26 fichiers touchés — décompte exact établi en Phase 2, voir [tasks.md](./tasks.md).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5 / Vue 3 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy, APScheduler ; Vite, Pinia, vue-router, ApexCharts

**Storage**: SQLite (`backend/garmin.db`), schéma créé par `Base.metadata.create_all` et migrations
impératives dans `init_db()`

**Testing**: Aucune suite automatisée (constitution III) — `npm run type-check` + vérification
manuelle sur deux comptes distincts

**Target Platform**: Serveur Linux auto-hébergé, backend sur `:8000`, frontend Vite sur `:5173`

**Project Type**: Application web à deux couches (backend Python + frontend Vue)

**Performance Goals**: Sans objet — un retrait ne doit dégrader aucun temps de chargement
existant

**Constraints**: Opération destructive sur une base en service (3 comptes) ; irréversible hors
sauvegarde (FR-011a)

**Scale/Scope**: 3 comptes, 1 tableau de bord, 5 widgets, 0 saisie d'exercice.
26 fichiers touchés au total.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principe | Applicabilité | Gate | Statut |
|---|---|---|---|
| **I. Isolation par utilisateur** | Oui — `delete_account` et `/auth/me` sont modifiés | La suppression de compte doit continuer à purger toutes les données du seul utilisateur courant ; aucune requête restante ne doit perdre son filtre `user_id` | ✅ Passe — vérification imposée en US2, contrôlée par SC-004 et SC-006 |
| **II. Secrets chiffrés au repos** | Oui — indirectement, via la sauvegarde exigée par FR-011a | La sauvegarde de `garmin.db` contient des identifiants Garmin chiffrés et des hashes bcrypt : elle MUST rester hors du dépôt | ⚠️ **Violation préexistante détectée** — voir Complexity Tracking |
| **III. Vérification avant merge** | Oui | `npm run type-check` vert + parcours manuel des cinq sections conservées sur deux comptes | ✅ Passe — imposé par le quickstart |
| **IV. Payload brut / idempotence** | Non | Aucune donnée issue de Garmin n'est touchée ; les colonnes `raw` sont hors périmètre | ✅ Sans objet |
| **V. Résilience de la synchronisation** | Non | Le scheduler et le client Garmin ne sont pas modifiés | ✅ Sans objet |

**Contrainte de langue** (section Contraintes techniques) : les messages et commentaires
introduits ou modifiés restent en français.

**Contrainte de migration** (section Workflow de développement) : « Une migration de schéma MUST
être décrite dans la PR ». Satisfaite par [data-model.md](./data-model.md).

**Verdict Phase 0** : passe. Une violation préexistante est constatée mais n'est pas causée par
cette feature et n'est pas traitée ici.

**Verdict post-Phase 1** : passe, inchangé. Le design ne crée aucune nouvelle dérogation.

## Project Structure

### Documentation (this feature)

```text
specs/001-retrait-dashboards-perso/
├── plan.md              # Ce fichier
├── spec.md              # Spécification (amendée)
├── research.md          # Phase 0 — décisions techniques
├── data-model.md        # Phase 1 — entités retirées et migration
├── quickstart.md        # Phase 1 — guide de validation
├── contracts/
│   └── endpoints-supprimes.md   # Phase 1 — contrat de service après retrait
├── checklists/
│   └── requirements.md  # Qualité de la spec
└── tasks.md             # Phase 2 — produit par /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── main.py                    # NETTOYER — import + include du routeur dashboards
├── database.py                # NETTOYER — 4 modèles, _migrate_handball_to_custom_dashboards(), appel dans init_db()
├── routes/
│   ├── dashboards.py          # SUPPRIMER — 684 lignes, 13 endpoints
│   ├── handball.py            # SUPPRIMER — 3 endpoints
│   ├── auth.py                # NETTOYER — imports, /auth/me, delete_account
│   ├── activities.py          # INTACT
│   ├── health.py              # INTACT
│   ├── stats.py               # INTACT
│   ├── profile.py             # INTACT
│   └── preferences.py         # INTACT — porte les préférences de navigation conservées
└── scripts/
    └── drop_dashboards.py     # CRÉER — migration destructive one-shot (FR-011)

frontend/src/
├── App.vue                    # NETTOYER — 4 blocs de navigation (desktop + mobile)
├── router/index.ts            # NETTOYER — route /d/:slug → redirection vers /
├── stores/
│   ├── dashboards.ts          # SUPPRIMER
│   ├── handball.ts            # SUPPRIMER
│   ├── nav.ts                 # NETTOYER — NavDashboard, customDashboards, 3 fonctions
│   ├── auth.ts                # NETTOYER — champ custom_dashboards
│   ├── garmin.ts              # INTACT
│   ├── profile.ts             # INTACT
│   └── notifications.ts       # INTACT
├── views/
│   ├── CustomDashboardView.vue   # SUPPRIMER
│   ├── HandballPrepView.vue      # SUPPRIMER
│   └── (Dashboard, Activities, ActivityDetail, Health, Sleep, Profile, Login)  # INTACTS
└── components/
    ├── widgets/               # SUPPRIMER — 6 fichiers
    ├── dashboard-editor/      # SUPPRIMER — 3 fichiers
    ├── sidebar/NavSettings.vue   # NETTOYER — section « Tableaux de bord » + bouton créer
    ├── charts/                # INTACT
    ├── cards/                 # INTACT
    └── maps/                  # INTACT

README.md                      # NETTOYER — fonctionnalités, arborescence
CLAUDE.md                      # NETTOYER — routes, stores, composants
```

**Structure Decision**: Structure existante à deux couches conservée telle quelle. Aucun dossier
nouveau hormis `backend/scripts/` pour héberger la migration destructive one-shot, isolée du code
applicatif afin qu'elle ne soit jamais exécutée au démarrage.

## Ordre d'exécution imposé

Cet ordre n'est pas indicatif : l'inverser produit un résultat incorrect.

1. **US1** (surface UI) — livrable seul, constitue le MVP.
2. **US2** (opérations de service) — après US1, sinon l'interface appelle des endpoints disparus.
3. **US4** (retrait handball, code + endpoints) — regroupé avec US3 côté code car les deux
   touchent `database.py`.
4. **Retrait de `_migrate_handball_to_custom_dashboards()`** — **impérativement avant** l'étape 5.
5. **Sauvegarde de `garmin.db`**, puis migration destructive (`drop_dashboards.py`).
6. **US3** (documentation) — en dernier, une fois le résultat constaté.

**Piège principal** : exécuter la migration destructive avant d'avoir retiré la fonction de
migration automatique. Le prochain démarrage recréerait le tableau de bord et ses cinq widgets
pour chaque compte disposant d'identifiants Garmin, annulant silencieusement le travail.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principe II — `backend/garmin.db.bak` (9 Mo) est suivi par Git** | Aucune : violation **préexistante**, sans lien avec cette feature. Le fichier contient les identifiants Garmin chiffrés, les hashes bcrypt et les données de santé des 3 comptes. Le `.gitignore` couvre `*.db` mais pas `*.db.bak`. | Non rejetée — **non traitée ici**. Le retrait de l'historique Git est une opération lourde (réécriture d'historique, rotation des clés) qui excède le périmètre de cette feature et doit faire l'objet d'un travail dédié. Signalée pour décision. |
| **Migration destructive sur base en service** | FR-011, décision explicite de l'utilisateur. | Conserver les tables orphelines a été proposé et écarté : l'utilisateur a choisi le nettoyage complet, la base ne contenant aucune saisie manuelle. Risque couvert par la sauvegarde obligatoire (FR-011a). |
