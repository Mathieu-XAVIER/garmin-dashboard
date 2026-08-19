# Feature Specification: Retrait des dashboards personnalisés

**Feature Branch**: `001-retrait-dashboards-perso`

**Created**: 2026-08-17

**Status**: Draft (amendée le 2026-08-17 — voir « Amendement »)

**Amendement**: L'analyse technique préalable au plan a établi que la prépa handball n'est
**plus accessible** dans le produit : sa vue n'est reliée à aucune adresse et son suivi
d'exercices a été migré vers un tableau de bord personnalisé généré automatiquement. Le suivi
d'exercices ne survivait donc que par les widgets. Décision prise : **retirer également la prépa
handball**, devenue du code inatteignable. Le périmètre conservé passe de six à cinq sections.
Sections impactées : US4 (ajoutée), US1 scénario 1, US3 Independent Test, FR-011, FR-011b,
FR-011c, FR-013, FR-015, FR-016, Key Entities, Edge Cases, SC-001, SC-002, SC-003, SC-008,
SC-009, Assumptions.

**Input**: User description: "Retirer complètement la fonctionnalité de dashboards personnalisés (widgets configurables : métriques, graphiques, objectifs, exercices) du projet : backend (route /dashboards, modèles associés), frontend (store dashboards, vues et composants widgets/ et dashboard-editor/, routes), et documentation. Les autres fonctionnalités (dashboard principal, activités, santé, sommeil, profil, handball, navigation personnalisable) doivent rester intactes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Plus aucun point d'entrée vers les tableaux de bord personnalisés (Priority: P1)

En tant qu'utilisateur du dashboard, je ne vois plus nulle part la possibilité de créer,
consulter ou modifier un tableau de bord personnalisé. Le panneau de réglages de navigation
ne propose plus que le masquage/affichage des onglets standard. Aucun lien mort, aucun bouton
sans effet ne subsiste.

**Why this priority**: C'est la seule tranche visible par l'utilisateur. Livrée seule, elle
suffit à retirer la fonctionnalité du produit — le reste est du nettoyage interne invisible.
Elle constitue donc le MVP.

**Independent Test**: Se connecter avec un compte possédant au moins un tableau de bord
personnalisé et parcourir toute l'interface (barre latérale desktop, navigation mobile,
réglages de navigation) : aucune mention, aucun bouton, aucun onglet lié aux tableaux de bord
personnalisés n'apparaît, et toutes les autres pages restent accessibles.

**Acceptance Scenarios**:

1. **Given** un compte possédant deux tableaux de bord personnalisés, **When** l'utilisateur
   se connecte, **Then** la navigation n'affiche que les cinq onglets standard (dashboard,
   activités, santé, sommeil, profil) et aucun onglet personnalisé.
2. **Given** l'utilisateur ouvre le panneau de réglages de navigation, **When** il consulte
   les options, **Then** il peut toujours masquer et afficher les onglets standard, et il n'y
   a plus ni liste de tableaux de bord, ni bouton de création, ni bouton de suppression.
3. **Given** un utilisateur ayant conservé en favori l'adresse d'un tableau de bord
   personnalisé, **When** il ouvre cette adresse, **Then** il est redirigé vers le dashboard
   principal sans page d'erreur ni écran vide.
4. **Given** un utilisateur avait masqué des onglets standard, **When** le retrait est livré,
   **Then** ses préférences de masquage sont conservées et toujours appliquées.

---

### User Story 2 - Le service ne répond plus aux demandes de tableaux de bord personnalisés (Priority: P2)

En tant qu'exploitant du service, je veux que plus aucune opération de lecture ou d'écriture
sur les tableaux de bord personnalisés ne soit possible, y compris pour un client obsolète ou
un appel forgé à la main. Les informations de compte renvoyées à la connexion ne mentionnent
plus les tableaux de bord.

**Why this priority**: Sans cette tranche, la fonctionnalité reste atteignable hors interface
et continue de créer des données. Elle n'est pas visible par l'utilisateur, d'où la priorité
inférieure à US1.

**Independent Test**: Interroger directement le service sur chacune des opérations de tableaux
de bord personnalisés avec un compte valide : toutes répondent « ressource inexistante ».
Consulter les informations du compte connecté : elles ne contiennent plus de liste de tableaux
de bord, et l'interface se charge normalement.

**Acceptance Scenarios**:

1. **Given** un utilisateur authentifié, **When** il tente une opération de lecture,
   de création, de modification, de réorganisation ou de suppression sur un tableau de bord
   personnalisé ou l'un de ses widgets, **Then** le service répond « ressource inexistante »
   pour chacune des opérations.
2. **Given** un onglet resté ouvert avant la livraison, **When** il déclenche un appel lié aux
   tableaux de bord personnalisés, **Then** l'application affiche un message d'erreur lisible
   ou ignore l'appel, sans page blanche ni déconnexion de l'utilisateur.
3. **Given** un utilisateur demande la suppression de son compte, **When** l'opération
   s'exécute, **Then** le compte et toutes ses données sont supprimés sans erreur.

---

### User Story 3 - Le projet ne conserve aucune trace de la fonctionnalité (Priority: P3)

En tant que mainteneur, je veux que le schéma de données, la documentation et l'architecture
décrite ne mentionnent plus les tableaux de bord personnalisés, afin qu'un nouvel arrivant ne
découvre pas une fonctionnalité fantôme.

**Why this priority**: Purement interne, sans effet sur le service rendu. À traiter en dernier
car cette tranche dépend des décisions prises sur les données existantes.

**Independent Test**: Rechercher les termes liés aux tableaux de bord personnalisés et aux
widgets dans la documentation et la description d'architecture : aucune occurrence. Inspecter
le schéma de la base : les quatre entités retirées en ont été supprimées (FR-011).

**Acceptance Scenarios**:

1. **Given** la documentation du projet, **When** on la relit intégralement, **Then** ni la
   liste des fonctionnalités, ni la description de l'architecture, ni les guides de
   contribution ne mentionnent les tableaux de bord personnalisés ou les widgets configurables.
2. **Given** une installation neuve du projet, **When** on la démarre, **Then** aucune entité
   de stockage liée aux tableaux de bord personnalisés n'est créée.

---

### User Story 4 - Le code inatteignable de la prépa handball disparaît (Priority: P4)

En tant que mainteneur, je veux que la prépa handball — dont la vue n'est reliée à aucune
adresse et dont le suivi d'exercices n'était plus atteignable que par un widget — soit retirée
avec le reste, plutôt que de rester en place sous forme de code inatteignable qui suggère une
fonctionnalité inexistante.

**Why this priority**: Aucun effet sur le service rendu, la fonctionnalité n'étant déjà plus
atteignable par les utilisateurs. À traiter en dernier, une fois le retrait principal validé.

**Independent Test**: Rechercher les termes liés à la prépa handball dans l'ensemble du projet :
aucune occurrence hors historique. L'application démarre et toutes les sections conservées
fonctionnent.

**Acceptance Scenarios**:

1. **Given** l'application après retrait, **When** un utilisateur parcourt l'interface,
   **Then** aucune mention de prépa handball ni de suivi d'exercices n'apparaît.
2. **Given** le service après retrait, **When** on appelle les opérations de prépa handball,
   **Then** elles répondent toutes « ressource inexistante ».
3. **Given** une base existante, **When** l'application démarre, **Then** la génération
   automatique du tableau de bord de prépa handball n'a plus lieu et aucune erreur n'est levée.

---

### Edge Cases

- **Adresse directe vers un tableau de bord supprimé** : un lien en favori ou partagé doit
  mener à une redirection propre, jamais à une erreur technique ou une page vide.
- **Préférence de masquage pointant vers un tableau de bord personnalisé** : une préférence
  résiduelle référençant un onglet qui n'existe plus doit être ignorée sans casser le reste des
  préférences de navigation.
- **Session ouverte pendant la livraison** : un client chargé avant la mise à jour ne doit ni
  déconnecter l'utilisateur, ni bloquer l'interface lorsqu'il appelle une opération disparue.
- **Compte sans aucun tableau de bord personnalisé** : le retrait doit être totalement
  transparent, sans changement de comportement.
- **Suivi d'exercices enregistré dans un widget** : ces saisies manuelles n'existent nulle part
  ailleurs dans le produit. Leur sort a été tranché explicitement — suppression définitive
  (FR-011) — au vu du constat que la table est vide dans la base en service.
- **Suppression de compte** : elle nettoyait explicitement les données de tableaux de bord ;
  elle doit continuer à s'exécuter sans erreur une fois ces données retirées du modèle.

## Requirements *(mandatory)*

### Functional Requirements

#### Retrait de la surface utilisateur (US1)

- **FR-001**: Le système MUST supprimer tout point d'entrée permettant de créer un tableau de
  bord personnalisé.
- **FR-002**: Le système MUST supprimer tout point d'entrée permettant d'ajouter, configurer,
  réordonner ou supprimer un widget.
- **FR-003**: La navigation (desktop et mobile) MUST n'afficher que les onglets standard et
  MUST cesser d'afficher les tableaux de bord personnalisés.
- **FR-004**: Le panneau de réglages de navigation MUST conserver intégralement le masquage et
  l'affichage des onglets standard, et MUST perdre toute gestion de tableaux de bord.
- **FR-005**: Une adresse pointant vers un tableau de bord personnalisé MUST rediriger vers le
  dashboard principal.

#### Retrait des opérations de service (US2)

- **FR-006**: Le système MUST cesser d'exposer toute opération de consultation, création,
  modification, réorganisation ou suppression de tableaux de bord personnalisés et de leurs
  widgets — soit 13 opérations aujourd'hui disponibles.
- **FR-007**: Les informations du compte connecté MUST cesser d'inclure la liste des tableaux
  de bord personnalisés, sans rompre le chargement de l'application.
- **FR-008**: La suppression de compte MUST continuer à supprimer intégralement le compte et
  ses données, sans erreur.
- **FR-009**: Un appel à une opération retirée MUST produire une réponse « ressource
  inexistante » et MUST NOT provoquer de déconnexion ni d'erreur interne.

#### Nettoyage du projet (US3)

- **FR-010**: Le système MUST cesser de créer les entités de stockage propres aux tableaux de
  bord personnalisés sur une installation neuve.
- **FR-011**: Les quatre entités de stockage retirées — tableaux de bord, widgets, suivi
  d'exercices de widget et suivi d'exercices de prépa handball — MUST être supprimées
  définitivement de toute base déjà en service, via une opération de migration documentée et
  exécutée une seule fois.
- **FR-011a**: Une sauvegarde de la base MUST être prise et vérifiée avant l'exécution de cette
  suppression, l'opération étant irréversible.
- **FR-011b**: La suppression MUST NOT toucher aux entités conservées : comptes, activités,
  santé quotidienne, sommeil, HRV et préférences de navigation.
- **FR-011c**: La génération automatique d'un tableau de bord de prépa handball au démarrage
  MUST être retirée, faute de quoi elle recréerait les données supprimées au prochain lancement.
- **FR-012**: La documentation du projet MUST être mise à jour pour ne plus mentionner les
  tableaux de bord personnalisés ni les widgets configurables.

#### Préservation du périmètre existant

- **FR-013**: Le dashboard principal, les activités, la santé quotidienne, le sommeil et le
  profil MUST rester fonctionnellement identiques — soit les cinq sections conservées.
- **FR-014**: L'inscription, la connexion, la gestion des identifiants Garmin et la
  synchronisation périodique MUST rester fonctionnellement identiques.
- **FR-015**: La prépa handball MUST être retirée intégralement — vue, opérations de service et
  stockage — conformément à l'amendement, la fonctionnalité n'étant plus atteignable et son
  suivi d'exercices ne survivant que par les widgets eux-mêmes retirés.
- **FR-016**: Les préférences de navigation (masquage des onglets standard) MUST être conservées
  et continuer de s'appliquer aux cinq sections restantes.

### Key Entities

- **Tableau de bord personnalisé**: Regroupement nommé, créé par un utilisateur, portant un
  identifiant d'affichage, une icône et une position dans la navigation. Appartient à un
  utilisateur unique. À retirer.
- **Widget**: Élément d'affichage configuré (métrique, graphique, objectif, suivi d'exercice,
  liste d'activités) rattaché à un tableau de bord personnalisé, avec un titre, une largeur et
  une position. Disparaît avec son tableau de bord. À retirer.
- **Suivi d'exercice de widget**: Saisie manuelle (date, type d'exercice, répétitions)
  rattachée à un tableau de bord personnalisé. Produite par l'utilisateur et non reconstituable
  par synchronisation Garmin, mais **vide dans la base en service**. À retirer (FR-011).
- **Suivi d'exercice de prépa handball**: Entité distincte de la précédente, dont elle est
  l'ancêtre : son contenu a été migré vers celle-ci. Également **vide dans la base en service**.
  À retirer (FR-015).
- **Préférences de navigation**: Onglets masqués par l'utilisateur. **Conservée** — seule sa
  partie liée aux tableaux de bord personnalisés disparaît.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un utilisateur parcourant l'intégralité de l'interface ne rencontre aucune mention
  des tableaux de bord personnalisés ni de la prépa handball — zéro occurrence sur l'ensemble
  des écrans.
- **SC-002**: Les 16 opérations retirées — 13 de tableaux de bord personnalisés et 3 de prépa
  handball — répondent toutes « ressource inexistante », vérifiées une à une : taux de
  disponibilité résiduelle de 0 %.
- **SC-003**: Les cinq sections conservées (dashboard, activités, santé, sommeil, profil) se
  chargent et affichent les mêmes données qu'avant le retrait, vérifié sur au moins deux comptes
  distincts.
- **SC-004**: Aucune régression d'isolation des données : chaque compte testé ne voit que ses
  propres données après le retrait.
- **SC-005**: Une installation neuve démarre sans erreur et sans créer d'entité liée aux
  tableaux de bord personnalisés.
- **SC-006**: La suppression d'un compte s'exécute sans erreur et ne laisse aucune donnée
  résiduelle rattachée à ce compte.
- **SC-007**: Une recherche des termes du domaine retiré dans la documentation retourne zéro
  occurrence.
- **SC-008**: Après migration, la base en service ne contient plus aucune des quatre entités
  retirées, et le nombre d'enregistrements de chaque entité conservée est strictement identique
  à celui relevé avant la migration.
- **SC-009**: Après un redémarrage complet de l'application, aucune des entités retirées n'est
  recréée — la vérification de SC-008 donne le même résultat au second démarrage.

## Assumptions

- La fonctionnalité est retirée parce qu'elle n'apporte pas la valeur attendue au regard de sa
  complexité ; aucun remplacement n'est prévu et aucune migration des configurations existantes
  vers une autre fonctionnalité n'est attendue.
- Le retrait est définitif : la restauration éventuelle du code passerait par l'historique Git,
  et celle des données par la sauvegarde exigée en FR-011a.
- L'état réel de la base au moment de la spécification a été relevé : 3 comptes, 1 tableau de
  bord personnalisé, 5 widgets et **0 saisie de suivi d'exercice de widget**. La suppression
  définitive ne détruit donc aucune donnée saisie manuellement, seulement une configuration
  d'affichage. C'est ce constat qui a permis de trancher FR-011 en faveur de la suppression
  plutôt que de la conservation des tables.
- Le nombre de comptes concernés est faible (projet personnel auto-hébergé) ; aucune campagne
  d'information ni période de préavis n'est nécessaire avant le retrait.
- Aucun export préalable des configurations de tableaux de bord n'est demandé, ces
  configurations étant reconstituables à la main si besoin.
- La navigation personnalisable (masquage d'onglets standard) est une fonctionnalité distincte
  et conservée, bien qu'elle partage aujourd'hui son panneau de réglages avec la gestion des
  tableaux de bord.
- La prépa handball était déjà inatteignable avant ce retrait : sa vue n'est reliée à aucune
  adresse et n'est importée nulle part. Son retrait ne prive donc aucun utilisateur d'un usage
  en cours. Ses deux entités de stockage sont vides.
- Le produit annonçait la prépa handball dans sa documentation alors qu'elle n'était plus
  atteignable ; la documentation était donc déjà inexacte sur ce point avant le retrait.
- Le retrait est livré en une fois ; il n'est pas nécessaire de faire coexister l'ancienne et la
  nouvelle version du service.
