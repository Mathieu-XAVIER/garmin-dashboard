"""Migration destructive one-shot — retrait des dashboards personnalisés.

Supprime définitivement les quatre tables devenues inutiles après le retrait de
la fonctionnalité de tableaux de bord personnalisés et de la prépa handball :

    custom_exercise_log, dashboard_widgets, custom_dashboards, prep_exercise_log

Ce script n'est JAMAIS appelé au démarrage de l'application. Il doit être lancé
manuellement, une seule fois, après avoir :

    1. arrêté le backend,
    2. pris une sauvegarde de garmin.db hors du dépôt,
    3. retiré `_migrate_handball_to_custom_dashboards()` de database.py
       (sans quoi les données seraient recréées au prochain démarrage).

Usage :
    python3 scripts/drop_dashboards.py [--base chemin/vers/garmin.db]

L'opération est irréversible. Les compteurs des tables conservées sont relevés
avant et après : toute divergence interrompt le script avec un code d'erreur.
"""

import argparse
import os
import sqlite3
import sys

# Tables supprimées, des feuilles vers la racine (dépendances descendantes)
TABLES_A_SUPPRIMER = [
    "custom_exercise_log",
    "dashboard_widgets",
    "custom_dashboards",
    "prep_exercise_log",
]

# Tables dont le contenu doit rester strictement identique
TABLES_CONSERVEES = ["users", "activities", "daily_health", "sleep", "hrv"]

CHEMIN_DEFAUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "garmin.db")


def compter(con, tables):
    """Retourne le nombre de lignes de chaque table existante."""
    presentes = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables if t in presentes}


def main():
    parseur = argparse.ArgumentParser(description="Supprime les tables des dashboards personnalisés.")
    parseur.add_argument("--base", default=CHEMIN_DEFAUT, help="chemin vers garmin.db")
    args = parseur.parse_args()

    if not os.path.exists(args.base):
        print(f"ERREUR : base introuvable : {args.base}", file=sys.stderr)
        return 1

    con = sqlite3.connect(args.base)
    try:
        print(f"Base : {args.base}\n")

        avant = compter(con, TABLES_CONSERVEES)
        print("Tables conservées — avant :")
        for table, nb in avant.items():
            print(f"  {table:16} {nb}")

        a_supprimer = compter(con, TABLES_A_SUPPRIMER)
        if not a_supprimer:
            print("\nAucune table à supprimer : la migration a déjà été appliquée.")
            return 0

        print("\nTables à supprimer :")
        for table, nb in a_supprimer.items():
            print(f"  {table:22} {nb} ligne(s)")

        print()
        for table in TABLES_A_SUPPRIMER:
            con.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"  DROP {table} ✓")
        con.commit()

        apres = compter(con, TABLES_CONSERVEES)
        if apres != avant:
            print("\nERREUR : le contenu des tables conservées a changé.", file=sys.stderr)
            print(f"  avant : {avant}", file=sys.stderr)
            print(f"  après : {apres}", file=sys.stderr)
            print("  Restaurer la sauvegarde immédiatement.", file=sys.stderr)
            return 2

        residuelles = compter(con, TABLES_A_SUPPRIMER)
        if residuelles:
            print(f"\nERREUR : tables encore présentes : {sorted(residuelles)}", file=sys.stderr)
            return 3

        print("\nTables conservées — après : inchangées ✓")
        print("Migration appliquée avec succès.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
