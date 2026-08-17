# Phase 1 — Modèle de données : entités retirées et migration

**Date**: 2026-08-17 | **Plan**: [plan.md](./plan.md)

## Entités retirées

Les quatre tables ci-dessous disparaissent du modèle (`backend/database.py`) et de toute base en
service. Les volumes sont ceux relevés le 2026-08-17.

### `custom_dashboards` — 1 ligne

| Colonne | Type | Note |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK → `users.id` | indexé, non nul |
| `name` | String | non nul |
| `slug` | String | indexé, unique par utilisateur |
| `icon` | String | nullable |
| `position` | Integer | défaut 0 |
| `config` | JSON | nullable |
| `created_at` | DateTime | |

Contrainte : `uq_dashboard_user_slug` sur `(user_id, slug)`.

### `dashboard_widgets` — 5 lignes

| Colonne | Type | Note |
|---|---|---|
| `id` | Integer PK | |
| `dashboard_id` | Integer FK → `custom_dashboards.id` | `ON DELETE CASCADE`, indexé |
| `widget_type` | String | `metric`, `chart`, `objective`, `exercise_tracker`, `activity_list` |
| `title` | String | non nul |
| `position` | Integer | défaut 0 |
| `width` | String | défaut `full` |
| `config` | JSON | non nul |
| `created_at` | DateTime | |

### `custom_exercise_log` — 0 ligne

| Colonne | Type | Note |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK → `users.id` | indexé, non nul |
| `dashboard_id` | Integer FK → `custom_dashboards.id` | `ON DELETE CASCADE`, indexé |
| `date` | String | indexé |
| `exercise_type` | String | non nul |
| `reps` | Integer | non nul |
| `created_at` | DateTime | |

Contrainte : `uq_exercise_user_dashboard_date_type` sur `(user_id, dashboard_id, date, exercise_type)`.

### `prep_exercise_log` — 0 ligne

Ancêtre de `custom_exercise_log`, dont le contenu a été migré (voir [research.md](./research.md) D3).
Retirée au titre de l'US4.

## Entités conservées — aucune modification de schéma

`users`, `activities`, `daily_health`, `sleep`, `hrv`.

La colonne `users.nav_preferences` (JSON) est **conservée** : elle porte les préférences de
masquage d'onglets, hors périmètre du retrait (FR-016).

## Dépendances référentielles

```text
users ──┬──> custom_dashboards ──┬──> dashboard_widgets
        │                        └──> custom_exercise_log
        ├──> prep_exercise_log
        └──> activities, daily_health, sleep, hrv   (conservées)
```

Aucune entité conservée ne référence une entité retirée. La suppression ne laisse donc aucune
clé étrangère orpheline, et l'ordre de suppression n'a pas d'importance fonctionnelle — il est
néanmoins effectué des feuilles vers la racine par convention.

## Migration destructive

**Fichier** : `backend/scripts/drop_dashboards.py` — script one-shot, jamais appelé au démarrage.

**Préconditions** (FR-011a) :
1. Application arrêtée (backend et frontend).
2. Sauvegarde de `backend/garmin.db` prise **hors du dépôt** et vérifiée lisible.
3. `_migrate_handball_to_custom_dashboards()` déjà retirée de `backend/database.py`, ainsi que
   son appel dans `init_db()` — sinon la suppression est annulée au démarrage suivant.

**Opération** :
1. Relever et journaliser le nombre de lignes de chaque table conservée (témoin avant).
2. `DROP TABLE IF EXISTS` dans l'ordre : `custom_exercise_log`, `dashboard_widgets`,
   `custom_dashboards`, `prep_exercise_log`.
3. Relever à nouveau le nombre de lignes des tables conservées (témoin après).
4. Échouer bruyamment si un compteur conservé a changé.

**Postconditions** :
- Les quatre tables sont absentes.
- Les compteurs de `users`, `activities`, `daily_health`, `sleep`, `hrv` sont strictement
  identiques avant et après (SC-008).
- Un second démarrage de l'application ne recrée aucune des quatre tables (SC-009).

**Réversibilité** : aucune, hors restauration de la sauvegarde.

**Idempotence** : `DROP TABLE IF EXISTS` permet de relancer le script sans erreur, y compris sur
une base déjà nettoyée ou une installation neuve.

## Retrait de la migration automatique

`_migrate_handball_to_custom_dashboards()` (`backend/database.py`, ~91 lignes) est supprimée avec
son appel conditionnel dans `init_db()`. La migration `user_id` de `init_db()` liste
`prep_exercise_log` parmi les tables à traiter : cette entrée est retirée de la liste, les autres
tables restant inchangées.
