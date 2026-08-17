# Phase 1 — Guide de validation

**Date**: 2026-08-17 | **Plan**: [plan.md](./plan.md)

Procédure de vérification du retrait, conforme au Principe III de la constitution
(type-check + vérification manuelle, deux comptes distincts).

## Prérequis

- Backend et frontend **arrêtés** avant l'étape 1.
- Deux comptes utilisateurs disponibles (la base en compte 3).
- Sauvegarde de `backend/garmin.db` prise **hors du dépôt** — jamais dans l'arborescence du
  projet, où elle risquerait d'être commitée (voir [research.md](./research.md), constat hors
  périmètre).

## Étape 1 — Témoin avant migration

Relever les compteurs des tables conservées, à comparer après coup :

```bash
cd backend
python3 -c "
import sqlite3
c = sqlite3.connect('garmin.db')
for t in ('users','activities','daily_health','sleep','hrv'):
    print(t, c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0])
"
```

Conserver cette sortie.

## Étape 2 — Sauvegarde obligatoire (FR-011a)

```bash
cp backend/garmin.db ~/sauvegardes/garmin-avant-retrait-dashboards.db
```

Vérifier que la copie est lisible avant de continuer :

```bash
python3 -c "
import sqlite3, os
p = os.path.expanduser('~/sauvegardes/garmin-avant-retrait-dashboards.db')
print(sqlite3.connect(p).execute('SELECT COUNT(*) FROM users').fetchone())
"
```

L'opération suivante est **irréversible** sans cette sauvegarde.

## Étape 3 — Migration destructive

À n'exécuter qu'après le retrait de `_migrate_handball_to_custom_dashboards()` du code
(voir [data-model.md](./data-model.md), préconditions) :

```bash
cd backend && python3 scripts/drop_dashboards.py
```

Attendu : les quatre tables sont supprimées, les compteurs conservés sont identiques à
l'étape 1. Le script échoue bruyamment sinon.

## Étape 4 — Contrôle du schéma

```bash
python3 -c "
import sqlite3
c = sqlite3.connect('backend/garmin.db')
t = {r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")}
retirees = {'custom_dashboards','dashboard_widgets','custom_exercise_log','prep_exercise_log'}
print('résiduelles :', t & retirees or 'aucune ✓')
"
```

Attendu : `aucune ✓` (SC-008).

## Étape 5 — Démarrage et non-recréation

```bash
cd backend && python main.py      # démarrage normal, aucune erreur attendue
```

Relancer l'étape 4 après démarrage. Attendu : toujours `aucune ✓`. Un échec ici signale que la
migration automatique n'a pas été retirée (SC-009, piège principal du plan).

## Étape 6 — Contrat de service

Avec un jeton valide, vérifier que **les 16 opérations retirées** répondent 404, une par une
(SC-002). La méthode HTTP compte : un GET sur un chemin exposé uniquement en POST renverrait 405
et masquerait un routeur encore monté.

```bash
TOKEN="<jeton valide>"

verifier() {  # $1 = méthode, $2 = chemin
  code=$(curl -s -o /dev/null -w '%{http_code}' -X "$1" \
         -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
         -d '{}' "http://localhost:8000$2")
  [ "$code" = "404" ] && etat="OK" || etat="ÉCHEC"
  printf '%-6s %-46s %s  %s\n' "$1" "$2" "$code" "$etat"
}

# 13 opérations /dashboards
verifier GET    /dashboards/
verifier POST   /dashboards/
verifier PUT    /dashboards/reorder
verifier GET    /dashboards/prepa-handball
verifier GET    /dashboards/prepa-handball/data
verifier PUT    /dashboards/prepa-handball
verifier DELETE /dashboards/prepa-handball
verifier POST   /dashboards/prepa-handball/widgets
verifier PUT    /dashboards/prepa-handball/widgets/reorder
verifier PUT    /dashboards/prepa-handball/widgets/1
verifier DELETE /dashboards/prepa-handball/widgets/1
verifier POST   /dashboards/prepa-handball/exercises
verifier DELETE /dashboards/prepa-handball/exercises/1

# 3 opérations /handball
verifier GET    /handball/prep
verifier POST   /handball/exercises
verifier DELETE /handball/exercises/1
```

Attendu : `404 OK` sur les 16 lignes. Toute autre valeur (200, 401, 405, 422) signale un routeur
encore monté.

Vérifier que `/auth/me` ne renvoie plus `custom_dashboards` :

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/auth/me | python3 -m json.tool
```

Attendu : `nav_preferences` présent, `custom_dashboards` absent.

## Étape 7 — Type-check frontend

```bash
cd frontend && npm run type-check
```

Attendu : aucune erreur. C'est le filet principal contre les imports laissés en place vers les
fichiers supprimés (Principe III).

## Étape 8 — Vérification manuelle, deux comptes

Pour **chacun des deux comptes** :

| Contrôle | Attendu |
|---|---|
| Connexion | Aboutit, redirection vers le dashboard |
| Navigation desktop | Cinq onglets uniquement, aucun séparateur ni onglet personnalisé |
| Navigation mobile (largeur réduite) | Idem, menu hamburger et bottom nav corrects |
| Panneau « Personnaliser » | Section « Onglets natifs » seule ; ni liste de tableaux de bord, ni bouton de création |
| Masquer puis réafficher un onglet | Fonctionne, persiste après rechargement (FR-016) |
| Ouvrir `/d/prepa-handball` | Redirection vers `/`, sans page blanche ni erreur (FR-005) |
| Dashboard, Activités, détail d'activité, Santé, Sommeil, Profil | Se chargent avec les mêmes données qu'avant (SC-003) |
| Console navigateur | Aucune erreur, aucun appel en échec vers `/dashboards` |

**Contrôle d'isolation (Principe I, SC-004)** : sur le second compte, vérifier qu'aucune donnée
du premier n'apparaît dans les sections conservées.

## Étape 9 — Suppression de compte (SC-006)

Sur un compte de test **jetable uniquement** :

```bash
curl -s -X DELETE -H "Authorization: Bearer $TOKEN_TEST" http://localhost:8000/auth/account
```

Attendu : `{"status": "ok", ...}`, aucune erreur serveur. Vérifier ensuite qu'aucune ligne
rattachée à cet utilisateur ne subsiste dans les tables conservées.

## Étape 10 — Documentation (SC-007)

```bash
grep -rniE "widget|dashboard-editor|custom_dashboard|handball" README.md CLAUDE.md
```

Attendu : aucune occurrence — hormis, dans `CLAUDE.md`, les mentions du dashboard principal qui
n'ont aucun rapport avec la fonctionnalité retirée.

## En cas d'échec

Restaurer la sauvegarde :

```bash
cp ~/sauvegardes/garmin-avant-retrait-dashboards.db backend/garmin.db
```

puis `git checkout` sur les fichiers modifiés.
