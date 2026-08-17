---

description: "Task list — Retrait des dashboards personnalisés"
---

# Tasks: Retrait des dashboards personnalisés

**Input**: Design documents from `/specs/001-retrait-dashboards-perso/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/endpoints-supprimes.md)

**Tests**: Aucune tâche de test automatisé. La spécification n'en demande pas et le Principe III
de la constitution retient la vérification pragmatique : `npm run type-check` + vérification
manuelle sur deux comptes. Les tâches de vérification sont intégrées à chaque phase.

**Organization**: Tâches groupées par user story. Chaque story est livrable et vérifiable seule.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallélisable (fichiers distincts, aucune dépendance)
- **[Story]**: user story de rattachement (US1, US2, US3, US4)
- Chemins de fichiers exacts dans chaque description

## ⚠️ Ordre des phases — lire avant de commencer

Les phases sont ordonnées par **ordre d'exécution**, pas strictement par priorité : **US4 (P4)
précède US3 (P3)**. Raison : US3 contient la migration destructive, qui porte sur les quatre
tables dont `prep_exercise_log` retirée par US4. Inverser produit une migration incomplète.

**Piège principal** (voir [research.md](./research.md) D3) : `_migrate_handball_to_custom_dashboards()`
recrée le tableau de bord et ses cinq widgets à chaque démarrage. Elle **doit** être retirée
(T035) **avant** l'exécution du DROP (T040), sinon la suppression est annulée au lancement
suivant, sans erreur visible.

---

## Phase 1: Setup

**Purpose**: Isoler le travail et figer l'état de départ

- [X] T001 Committer l'état actuel du dépôt (installation spec-kit, `.specify/`, `.claude/skills/`, `.gitignore`, `CLAUDE.md`, `specs/`) sur `main` avant toute modification
- [X] T002 Créer et basculer sur la branche `001-retrait-dashboards-perso` depuis `main`
- [X] T003 Vérifier que l'application démarre et fonctionne avant modification : backend sur `:8000`, frontend sur `:5173`, connexion réussie sur un compte

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Garde-fous obligatoires avant toute opération destructive

**⚠️ CRITICAL**: T005 et T006 conditionnent la phase 6. Sans eux, la migration destructive est
irréversible et invérifiable.

- [ ] T004 Arrêter le backend et le frontend avant toute manipulation de `backend/garmin.db` — **reporté juste avant T040** : la sauvegarde T006 a été prise à chaud via l'API `backup` de SQLite, cohérente sans arrêt de service
- [X] T005 Relever et consigner les compteurs témoins des tables conservées (`users`, `activities`, `daily_health`, `sleep`, `hrv`) de `backend/garmin.db` selon l'étape 1 de [quickstart.md](./quickstart.md) — relevé : users=3, activities=20, daily_health=394, sleep=394, hrv=77
- [X] T006 Copier `backend/garmin.db` vers un emplacement **hors du dépôt** (ex. `~/sauvegardes/garmin-avant-retrait-dashboards.db`) et vérifier la copie lisible — FR-011a — fait : 13,3 Mo, intégrité vérifiée
- [X] T007 Vérifier que la sauvegarde n'est pas dans l'arborescence du projet ni visible par `git status` — Principe II

**Checkpoint**: Sauvegarde vérifiée et témoins consignés — le retrait peut commencer

---

## Phase 3: User Story 1 - Plus aucun point d'entrée dans l'interface (Priority: P1) 🎯 MVP

**Goal**: L'utilisateur ne voit plus nulle part les tableaux de bord personnalisés. La
navigation personnalisable (masquage d'onglets) reste intacte.

**Independent Test**: Se connecter et parcourir barre latérale desktop, navigation mobile et
panneau « Personnaliser » : aucune mention de tableau de bord personnalisé, et toutes les autres
sections restent accessibles.

**⚠️ Ordre intra-phase**: nettoyer les fichiers consommateurs (T008–T011) **avant** de supprimer
les fichiers consommés (T012–T014), sinon l'application est cassée entre deux tâches.

### Nettoyage des consommateurs

- [X] T008 [US1] Retirer les 4 blocs de navigation des tableaux de bord personnalisés (séparateur + `RouterLink v-for` sur `navStore.customDashboards`, desktop lignes ~16-19 et mobile lignes ~68-70) **ainsi que la règle CSS `.nav-separator` (ligne ~172) devenue orpheline** dans `frontend/src/App.vue` — vérifié : aucun autre usage de cette classe
- [X] T009 [US1] Retirer la section « Tableaux de bord », le bouton « + Nouveau tableau de bord », l'import de `DashboardCreateModal`, l'import de `useDashboardsStore`, les fonctions `handleDeleteDashboard` et `onDashboardCreated`, l'usage de `useRouter` s'il devient inutile, et les styles `.nsp-dash-*` / `.nsp-create-btn` devenus orphelins dans `frontend/src/components/sidebar/NavSettings.vue` — conserver intégralement la section « Onglets natifs », `isHidden` et `toggleTab`
- [X] T010 [P] [US1] Retirer l'interface `NavDashboard`, l'état `customDashboards`, les fonctions `addDashboardToNav`, `removeDashboardFromNav`, `updateDashboardInNav`, leur exposition dans le `return`, et le paramètre `custom_dashboards` de `syncFromAuth` dans `frontend/src/stores/nav.ts` — conserver `hiddenTabs`, `nativeTabs`, `fetchPreferences`, `updateHiddenTabs`
- [X] T011 [P] [US1] Retirer l'import de `NavDashboard` et le champ `custom_dashboards?: NavDashboard[]` du type utilisateur dans `frontend/src/stores/auth.ts`
- [X] T012 [US1] Remplacer la route `/d/:slug` par une redirection vers `/` dans `frontend/src/router/index.ts` — FR-005, ne pas supprimer sèchement (écran blanc, voir research.md D4)

### Suppression des fichiers dédiés

- [X] T013 [P] [US1] Supprimer les 6 composants de `frontend/src/components/widgets/` : `ActivityListWidget.vue`, `ChartWidget.vue`, `ExerciseTrackerWidget.vue`, `MetricWidget.vue`, `ObjectiveWidget.vue`, `WidgetRenderer.vue`
- [X] T014 [P] [US1] Supprimer les 3 composants de `frontend/src/components/dashboard-editor/` : `DashboardCreateModal.vue`, `DataSourcePicker.vue`, `WidgetAddModal.vue`
- [X] T015 [P] [US1] Supprimer `frontend/src/views/CustomDashboardView.vue`
- [X] T016 [P] [US1] Supprimer `frontend/src/stores/dashboards.ts`

### Vérification

- [X] T017 [US1] Exécuter `npm run type-check` depuis `frontend/` — aucune erreur attendue (Principe III)
- [ ] T018 [US1] Vérifier manuellement sur deux comptes : navigation desktop et mobile réduites aux cinq onglets, panneau « Personnaliser » sans gestion de tableaux de bord, masquage d'onglet toujours fonctionnel et persistant, `/d/prepa-handball` redirige vers `/` sans écran blanc, console navigateur sans erreur

**Checkpoint**: MVP atteint — la fonctionnalité a disparu du produit. Le backend reste en place,
sans conséquence visible.

---

## Phase 4: User Story 2 - Le service ne répond plus (Priority: P2)

**Goal**: Les 13 opérations de tableaux de bord répondent 404 et `/auth/me` ne renvoie plus
`custom_dashboards`.

**Independent Test**: Appeler chaque opération retirée avec un jeton valide — toutes répondent
404. `/auth/me` ne contient plus `custom_dashboards` mais conserve `nav_preferences`.

- [X] T019 [US2] Retirer l'import `from routes.dashboards import router as dashboards_router` (ligne ~28) et l'appel `app.include_router(dashboards_router)` (ligne ~78) dans `backend/main.py`
- [X] T020 [US2] Supprimer `backend/routes/dashboards.py` (684 lignes, 13 endpoints)
- [X] T021 [US2] Retirer la requête sur `CustomDashboard` et le champ `custom_dashboards` de la réponse de `/auth/me` (lignes ~84-100) dans `backend/routes/auth.py` — conserver `nav_preferences`
- [X] T022 [US2] Retirer le bloc de purge des tableaux de bord, widgets et saisies d'exercices (lignes ~169-174) de `delete_account`, et retirer `CustomExerciseLog` de la boucle de purge (ligne ~177) dans `backend/routes/auth.py` — conserver la purge filtrée par `user_id` des tables restantes (Principe I)
- [X] T023 [US2] Retirer `CustomDashboard`, `DashboardWidget` et `CustomExerciseLog` des imports (lignes ~17-18) de `backend/routes/auth.py`
- [X] T024 [US2] Vérifier que le backend démarre sans erreur d'import depuis `backend/`
- [X] T025 [US2] Vérifier avec un jeton valide que **les 13 opérations** de `/dashboards` listées dans [contracts/endpoints-supprimes.md](./contracts/endpoints-supprimes.md) répondent 404, une par une, et que `GET /auth/me` renvoie `nav_preferences` sans `custom_dashboards` — étape 6 de [quickstart.md](./quickstart.md), SC-002
- [X] T026 [US2] Vérifier sur un compte de test jetable que `DELETE /auth/account` s'exécute sans erreur et ne laisse aucune donnée résiduelle — SC-006

**Checkpoint**: Le service ne rend plus la fonctionnalité, y compris hors interface

---

## Phase 5: User Story 4 - Retrait du code inatteignable de la prépa handball (Priority: P4)

**Goal**: La prépa handball — vue orpheline, store, endpoints et migration automatique —
disparaît du projet.

**⚠️ Exécutée avant US3** : la migration destructive d'US3 porte sur `prep_exercise_log`, et le
retrait de la migration automatique (T035) conditionne la réussite du DROP (T040).

**Independent Test**: Rechercher « handball » dans le code : aucune occurrence hors historique.
L'application démarre et les cinq sections conservées fonctionnent.

- [ ] T027 [P] [US4] Supprimer `frontend/src/views/HandballPrepView.vue`
- [ ] T028 [P] [US4] Supprimer `frontend/src/stores/handball.ts`
- [ ] T029 [US4] Retirer l'import et l'`include_router` du routeur handball dans `backend/main.py`
- [ ] T030 [US4] Supprimer `backend/routes/handball.py` (3 endpoints : `GET /handball/prep`, `POST /handball/exercises`, `DELETE /handball/exercises/{exercise_id}`)
- [ ] T031 [US4] Retirer `PrepExerciseLog` de l'import (ligne ~18) et de la boucle de purge (ligne ~177) de `delete_account` dans `backend/routes/auth.py`
- [ ] T032 [US4] Exécuter `npm run type-check` depuis `frontend/` et vérifier le démarrage du backend — aucune erreur d'import
- [ ] T033 [US4] Vérifier avec un jeton valide que **les 3 opérations** de `/handball` répondent 404 : `GET /handball/prep`, `POST /handball/exercises`, `DELETE /handball/exercises/1` — complète SC-002 (16 opérations au total avec T025)

**Checkpoint**: Plus aucune trace de la prépa handball dans le code applicatif

---

## Phase 6: User Story 3 - Schéma, migration et documentation (Priority: P3)

**Goal**: Les quatre tables disparaissent du modèle et de la base en service ; la documentation
cesse de décrire une fonctionnalité inexistante.

**Independent Test**: Le schéma de `backend/garmin.db` ne contient plus aucune des quatre tables,
y compris après redémarrage. Une recherche des termes retirés dans la documentation ne retourne
rien.

### Retrait des modèles et de la migration automatique

- [ ] T034 [US3] Supprimer les classes `CustomDashboard`, `DashboardWidget`, `CustomExerciseLog` (lignes ~155-198) et `PrepExerciseLog` (ligne ~140) de `backend/database.py`
- [ ] T035 [US3] **Supprimer la fonction `_migrate_handball_to_custom_dashboards()` (lignes ~209-299, ~91 lignes) et son appel conditionnel dans `init_db()`** dans `backend/database.py` — sans quoi le DROP de T040 sera annulé au démarrage suivant (research.md D3)
- [ ] T036 [US3] Retirer `"prep_exercise_log"` de la liste `tables_to_migrate` de la migration `user_id` dans `init_db()` de `backend/database.py` — conserver les autres tables
- [ ] T037 [US3] Vérifier que le backend démarre sans erreur et qu'une installation neuve (base absente) ne crée aucune des quatre tables — FR-010, SC-005

### Migration destructive

- [ ] T038 [US3] Créer `backend/scripts/drop_dashboards.py` : script one-shot, jamais appelé au démarrage, qui relève les compteurs des tables conservées, exécute `DROP TABLE IF EXISTS` sur `custom_exercise_log`, `dashboard_widgets`, `custom_dashboards`, `prep_exercise_log` dans cet ordre, relève à nouveau les compteurs et échoue bruyamment si l'un d'eux a changé — voir [data-model.md](./data-model.md)
- [ ] T039 [US3] Confirmer que T035 est bien appliqué et que la sauvegarde de T006 existe, avant toute exécution destructive
- [ ] T040 [US3] Exécuter `python3 scripts/drop_dashboards.py` depuis `backend/` — les quatre tables sont supprimées, les compteurs conservés inchangés
- [ ] T041 [US3] Vérifier que le schéma de `backend/garmin.db` ne contient plus aucune des quatre tables — étape 4 de [quickstart.md](./quickstart.md), SC-008
- [ ] T042 [US3] Redémarrer le backend puis répéter la vérification T041 — aucune table recréée, SC-009
- [ ] T043 [US3] Comparer les compteurs des tables conservées avec les témoins de T005 — identité stricte exigée, SC-008

### Documentation

- [ ] T044 [P] [US3] Retirer les mentions des dashboards personnalisés, des widgets et de la prépa handball de `README.md` : liste des fonctionnalités (lignes ~23-24), arborescence (`routes/handball.py`, `stores/`, `views/`, `components/widgets/`, `components/dashboard-editor/`) et tableau des données disponibles
- [ ] T045 [P] [US3] Retirer les mentions de `handball.py`, du store `handball`, des composants `widgets/` et `dashboard-editor/`, et des modèles `PrepExerciseLog` / dashboards de `CLAUDE.md` — sections Architecture, `routes/`, Stores Pinia, Composants
- [ ] T046 [US3] Vérifier qu'une recherche de `widget`, `dashboard-editor`, `custom_dashboard` et `handball` dans `README.md` et `CLAUDE.md` ne retourne aucune occurrence, hormis les mentions du dashboard principal sans rapport — SC-007

**Checkpoint**: Le projet ne conserve plus aucune trace de la fonctionnalité

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T047 Exécuter `npm run build` depuis `frontend/` — type-check et build de production sans erreur
- [ ] T048 Dérouler intégralement [quickstart.md](./quickstart.md), étapes 1 à 10, sur deux comptes distincts
- [ ] T049 Vérifier l'isolation des données : sur le second compte, aucune donnée du premier n'apparaît dans les cinq sections conservées — Principe I, SC-004
- [ ] T050 Rechercher les imports et références résiduels dans `backend/` et `frontend/src/` : `dashboards`, `Widget`, `widget`, `handball`, `custom_dashboard` (recherche **insensible à la casse**, `customDashboards` échappe à une recherche sensible)
- [ ] T051 Vérifier que la sauvegarde de T006 n'a pas été introduite dans le dépôt — `git status` et `git ls-files` propres côté fichiers de base
- [ ] T052 Décrire la migration de schéma dans la description de la PR : tables supprimées, script exécuté, sauvegarde prise — exigence du Workflow de développement de la constitution

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: aucune dépendance
- **Phase 2 (Foundational)**: dépend de la phase 1 — **bloque la phase 6**
- **Phase 3 (US1, P1)**: dépend de la phase 1 — livrable seule, c'est le MVP
- **Phase 4 (US2, P2)**: dépend de la phase 3 (sinon l'interface appelle des endpoints disparus)
- **Phase 5 (US4, P4)**: dépend de la phase 4 (les deux touchent `backend/routes/auth.py`)
- **Phase 6 (US3, P3)**: dépend des phases 2, 4 et 5
- **Phase 7 (Polish)**: dépend de toutes les précédentes

### Chaîne critique

```text
T006 (sauvegarde) ─────────────────┐
T035 (retrait migration auto) ─────┼──> T039 (contrôle) ──> T040 (DROP) ──> T042 (redémarrage)
T034 (retrait modèles) ────────────┘
```

T040 sans T035 produit un **échec silencieux** : les données réapparaissent au démarrage suivant.

### Within Each User Story

- Nettoyer les fichiers consommateurs avant de supprimer les fichiers consommés
- Vérifier (`type-check`, démarrage backend) avant de passer à la phase suivante
- Chaque phase se termine par sa vérification propre

### Parallel Opportunities

- **US1**: T010 et T011 en parallèle (stores distincts) ; T013 à T016 en parallèle (suppressions indépendantes) après T008-T012
- **US4**: T027 et T028 en parallèle (frontend, fichiers distincts)
- **US3**: T044 et T045 en parallèle (documents distincts)
- **Aucune parallélisation entre phases** : les dépendances sont strictes

---

## Parallel Example: User Story 1

```bash
# Après le nettoyage des consommateurs (T008-T012), supprimer les fichiers dédiés ensemble :
Task: "Supprimer les 6 composants de frontend/src/components/widgets/"
Task: "Supprimer les 3 composants de frontend/src/components/dashboard-editor/"
Task: "Supprimer frontend/src/views/CustomDashboardView.vue"
Task: "Supprimer frontend/src/stores/dashboards.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (Setup) → Phase 3 (US1)
2. **STOP et VALIDER** : type-check vert, parcours manuel sur deux comptes
3. La fonctionnalité a disparu du produit ; le backend inutilisé peut attendre

### Incremental Delivery

1. Setup + Foundational → garde-fous en place
2. US1 → vérifier → **MVP livrable**
3. US2 → vérifier → le service ne rend plus la fonctionnalité
4. US4 → vérifier → code inatteignable retiré
5. US3 → vérifier → schéma, base et documentation nettoyés
6. Polish → validation complète du quickstart

### Point de non-retour

T040 (DROP) est **irréversible** hors restauration de la sauvegarde de T006. Tout ce qui précède
est annulable par `git checkout`.

---

## Récapitulatif des fichiers

| Action | Nombre | Détail |
|---|---|---|
| Supprimés | 15 | 6 widgets, 3 dashboard-editor, 2 vues, 2 stores, 2 routeurs backend |
| Nettoyés | 10 | `main.py`, `database.py`, `routes/auth.py`, `App.vue`, `router/index.ts`, `stores/nav.ts`, `stores/auth.ts`, `NavSettings.vue`, `README.md`, `CLAUDE.md` |
| Créés | 1 | `backend/scripts/drop_dashboards.py` |
| **Total** | **26** | |

Endpoints retirés : 16 (13 dashboards + 3 handball). Tables supprimées : 4.

---

## Notes

- `[P]` = fichiers distincts, aucune dépendance
- Committer après chaque phase pour pouvoir revenir en arrière avant T040
- Aucun test automatisé : la vérification repose sur `npm run type-check` et le parcours manuel
  imposé par le Principe III
- Point de vigilance permanent : ne jamais affaiblir le filtrage par `user_id` dans les requêtes
  modifiées de `backend/routes/auth.py` (Principe I)
