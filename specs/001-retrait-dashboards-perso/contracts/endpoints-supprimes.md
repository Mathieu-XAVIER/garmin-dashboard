# Phase 1 — Contrat de service après retrait

**Date**: 2026-08-17 | **Plan**: [../plan.md](../plan.md)

Ce document fige le contrat HTTP attendu après le retrait : ce qui disparaît, ce qui change, ce
qui ne bouge pas.

## Endpoints supprimés — `/dashboards` (13)

Le routeur entier est retiré de `backend/main.py`. Toutes les opérations ci-dessous doivent
répondre **404 Not Found** après le retrait, y compris avec un jeton valide.

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/dashboards/` | Liste des tableaux de bord |
| POST | `/dashboards/` | Création |
| PUT | `/dashboards/reorder` | Réordonnancement |
| GET | `/dashboards/{slug}` | Détail |
| GET | `/dashboards/{slug}/data` | Données agrégées des widgets |
| PUT | `/dashboards/{slug}` | Modification |
| DELETE | `/dashboards/{slug}` | Suppression |
| POST | `/dashboards/{slug}/widgets` | Ajout de widget |
| PUT | `/dashboards/{slug}/widgets/reorder` | Réordonnancement des widgets |
| PUT | `/dashboards/{slug}/widgets/{widget_id}` | Modification de widget |
| DELETE | `/dashboards/{slug}/widgets/{widget_id}` | Suppression de widget |
| POST | `/dashboards/{slug}/exercises` | Saisie d'exercice |
| DELETE | `/dashboards/{slug}/exercises/{exercise_id}` | Suppression d'une saisie |

## Endpoints supprimés — `/handball` (3)

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/handball/prep` | Suivi de prépa physique |
| POST | `/handball/exercises` | Saisie d'exercice |
| DELETE | `/handball/exercises/{exercise_id}` | Suppression d'une saisie |

## Contrat modifié — `GET /auth/me`

Le champ `custom_dashboards` disparaît de la réponse. Tous les autres champs sont inchangés.

**Avant**

```json
{
  "id": 1,
  "email": "...",
  "nav_preferences": { "hidden_tabs": ["sleep"] },
  "custom_dashboards": [
    { "id": 1, "name": "Prépa Handball", "slug": "prepa-handball", "icon": "🤾", "position": 0 }
  ]
}
```

**Après**

```json
{
  "id": 1,
  "email": "...",
  "nav_preferences": { "hidden_tabs": ["sleep"] }
}
```

`nav_preferences` est **conservé** (FR-016).

## Contrat modifié — `DELETE /auth/account`

Comportement observable **inchangé** : le compte et toutes ses données sont supprimés, réponse
`{"status": "ok"}`. Seule l'implémentation change — la purge des tableaux de bord, widgets et
saisies d'exercices disparaît, ces tables n'existant plus.

Point de vigilance (Principe I) : la purge des tables conservées doit rester filtrée sur le seul
`user_id` courant.

## Endpoints inchangés

`/auth` (hors les deux points ci-dessus), `/activities`, `/health`, `/stats`, `/profile`,
`/preferences` — aucune modification de contrat.

`/preferences/nav` en particulier reste pleinement fonctionnel : il porte les préférences de
masquage d'onglets, conservées.

## Contrat d'interface — routes frontend

| Route | Avant | Après |
|---|---|---|
| `/d/:slug` | Vue de tableau de bord personnalisé | **Redirection vers `/`** (FR-005) |
| `/`, `/activities`, `/activities/:id`, `/health`, `/sleep`, `/profile`, `/login` | — | Inchangées |

Aucune route handball n'existe aujourd'hui côté frontend : rien à retirer de ce côté, seulement
la vue orpheline.
