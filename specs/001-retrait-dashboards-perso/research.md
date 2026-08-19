# Phase 0 — Recherche : Retrait des dashboards personnalisés

**Date**: 2026-08-17 | **Plan**: [plan.md](./plan.md)

Toutes les inconnues techniques ont été levées par lecture directe du code et inspection de la
base en service. Aucune ne subsiste.

---

## D1 — Une installation neuve cessera-t-elle de créer les tables ?

**Décision** : Oui, il suffit de supprimer les classes de modèles de `backend/database.py`.

**Rationale** : `init_db()` appelle `Base.metadata.create_all(bind=engine)`. `Base.metadata` est
peuplé par la déclaration des classes héritant de `Base`. Retirer les quatre classes les retire
du metadata, donc de la création. Aucune définition de table n'existe ailleurs (pas d'Alembic,
pas de SQL de schéma).

**Alternatives considérées** : conserver les modèles et filtrer `create_all(tables=[...])` —
rejeté, cela laisserait du code mort et contredirait FR-010.

---

## D2 — Comment supprimer les tables d'une base déjà en service ?

**Décision** : Un script one-shot `backend/scripts/drop_dashboards.py`, exécuté manuellement,
qui effectue un `DROP TABLE IF EXISTS` sur les quatre tables et vérifie les comptages avant/après.

**Rationale** : le projet n'utilise pas d'outil de migration ; les évolutions de schéma sont des
blocs impératifs dans `init_db()`. Y ajouter un `DROP` serait dangereux : il s'exécuterait à
chaque démarrage et sur toute base, y compris celle d'un développeur qui n'a pas encore
sauvegardé. Un script séparé rend l'opération explicite, unique et intentionnelle — cohérent avec
FR-011 (« exécutée une seule fois ») et FR-011a (sauvegarde préalable).

`DROP TABLE IF EXISTS` est idempotent et ne casse pas sur une base déjà nettoyée ou sur une
installation neuve.

**Alternatives considérées** :
- Bloc dans `init_db()` — rejeté (destructif, répété, non intentionnel).
- Ne rien supprimer, laisser les tables orphelines — proposé à l'utilisateur, écarté par lui.

---

## D3 — Ordre entre la migration destructive et le retrait de la migration automatique

**Décision** : retirer `_migrate_handball_to_custom_dashboards()` **avant** d'exécuter le DROP.

**Rationale** : `init_db()` appelle cette fonction dès que la table `prep_exercise_log` existe.
Elle crée, pour chaque utilisateur ayant des identifiants Garmin, un tableau de bord
« Prépa Handball » et cinq widgets, puis recopie `prep_exercise_log` vers `custom_exercise_log`.
Elle est **la source du tableau de bord et des cinq widgets actuellement en base** — ce ne sont
pas des créations de l'utilisateur.

Conséquence : un DROP exécuté alors que la fonction existe encore serait annulé au démarrage
suivant, la table étant recréée par `create_all` puis repeuplée. L'inversion de l'ordre produit
un échec silencieux, sans erreur visible.

**Alternatives considérées** : garder la fonction avec un garde-fou — rejeté, du code mort qui
réintroduit un risque à chaque démarrage.

---

## D4 — Que renvoyer sur les adresses de tableaux de bord supprimées ?

**Décision** : remplacer la route `/d/:slug` par une redirection vers `/`.

**Rationale** : le routeur ne comporte pas de route « catch-all » ; supprimer purement la route
laisserait vue-router sans correspondance et afficherait un `<router-view>` vide — un écran
blanc, contraire à l'edge case « adresse directe » et à FR-005. Une redirection explicite est
d'une ligne et couvre les liens en favori.

**Alternatives considérées** :
- Suppression sèche de la route — rejeté (écran blanc).
- Route catch-all globale — rejeté, changement de comportement plus large que le périmètre.

---

## D5 — Impact du retrait de `custom_dashboards` sur le contrat `/auth/me`

**Décision** : retirer le champ de la réponse et l'aligner côté frontend dans `syncFromAuth`.

**Rationale** : `/auth/me` renvoie aujourd'hui `custom_dashboards`, consommé par
`nav.ts:syncFromAuth()` qui alimente la navigation. Le champ étant optionnel côté TypeScript
(`custom_dashboards?`), son absence ne casserait pas le typage — mais laisser le code de lecture
en place serait du code mort. Les deux côtés sont donc nettoyés ensemble.

`nav_preferences` reste dans la même réponse et n'est pas touché (FR-016).

**Alternatives considérées** : renvoyer un tableau vide pour compatibilité — rejeté, aucun client
tiers ne consomme cette API, la compatibilité n'a pas d'objet.

---

## D6 — Sort des préférences de navigation référençant un onglet disparu

**Décision** : aucune action corrective nécessaire.

**Rationale** : `nav.ts` filtre les onglets par `NATIVE_TABS.filter(t => !hiddenTabs.includes(t.id))`.
Un identifiant résiduel dans `hidden_tabs` qui ne correspond à aucun onglet natif est simplement
sans effet. `NATIVE_TABS` ne contient d'ailleurs que les cinq onglets conservés — la prépa
handball n'y a jamais figuré, ce qui confirme son inaccessibilité.

**Alternatives considérées** : script de nettoyage des préférences — rejeté, sans bénéfice
observable.

---

## D7 — La prépa handball est-elle réellement inatteignable ?

**Décision** : oui, constat vérifié ; elle est retirée avec le reste (US4).

**Rationale** : trois vérifications concordantes.
1. `frontend/src/router/index.ts` ne déclare aucune route vers `HandballPrepView.vue`.
2. Aucun fichier n'importe `HandballPrepView.vue` ni ne mentionne « handball » hors de la vue
   et de son store.
3. `ExerciseTrackerWidget.vue` importe `stores/dashboards`, pas `stores/handball` : le suivi
   d'exercices réellement utilisé passait par les widgets.

La migration D3 confirme l'intention : la prépa handball a été convertie en tableau de bord
personnalisé, et l'ancienne vue laissée en place sans être débranchée proprement.

**Alternatives considérées** : restaurer la route `/handball` pour préserver le suivi
d'exercices, ou ne rien faire — les deux ont été proposées à l'utilisateur, qui a choisi le
retrait complet.

---

## D8 — Volume de données réellement détruit

**Décision** : la suppression est sans conséquence sur les données saisies.

**Rationale** : inspection de `backend/garmin.db` au 2026-08-17 —

| Table | Lignes |
|---|---|
| `users` | 3 |
| `custom_dashboards` | 1 |
| `dashboard_widgets` | 5 |
| `custom_exercise_log` | **0** |
| `prep_exercise_log` | **0** |

Les deux tables de saisie manuelle sont vides. Le tableau de bord et les cinq widgets sont ceux
générés par la migration automatique (D3), pas une création de l'utilisateur. Aucune donnée
Garmin n'est touchée.

**Alternatives considérées** : export préalable des configurations — rejeté, sans valeur puisque
la fonctionnalité disparaît.

---

## Constat hors périmètre — `backend/garmin.db.bak` suivi par Git

**Non traité par cette feature.** Consigné pour décision séparée.

`git ls-files` confirme que `backend/garmin.db.bak` (9,1 Mo) est suivi par Git. Le `.gitignore`
couvre `*.db` mais pas le suffixe `.bak`. Ce fichier contient les mots de passe Garmin chiffrés
Fernet, les hashes bcrypt et l'historique de santé des trois comptes.

Cela contredit le Principe II de la constitution (« `backend/.env` et `*.db` MUST rester hors du
dépôt »). Le remède exige une réécriture d'historique Git et, par prudence, une rotation de
`GARMIN_CREDENTIAL_KEY` et `JWT_SECRET_KEY` — hors périmètre d'un retrait de fonctionnalité.

**Point d'attention immédiat** : la sauvegarde exigée par FR-011a ne doit pas reproduire cette
erreur. Le quickstart impose de l'écrire hors du dépôt.
