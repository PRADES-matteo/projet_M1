# projet_M1

Application Django de gestion des coûts pensée pour un usage simple et pédagogique.

## Objectif
L'utilisateur saisit ses données de coûts dans l'application, puis le système calcule les résultats selon deux méthodes :
- la méthode des centres d'analyse
- le direct costing, y compris une vue d'évaluation du direct costing

## Architecture proposée

### `projet_m1/`
Configuration globale du projet Django.
- `settings.py` : réglages Django, base de données SQLite, templates et static files
- `urls.py` : routage principal
- `asgi.py` / `wsgi.py` : points d'entrée serveur

### `apps/dashboard/`
Espace d'accueil et navigation utilisateur.
- page d'accueil
- accès vers les scénarios de coût

### `apps/costs/`
Cœur fonctionnel du site.
- modèles pour scénario, centre de coût et lignes de coût
- formulaires de saisie
- services de calcul métier
- pages liste et détail des scénarios

### `templates/`
Templates globaux partagés par le front Django.

## Flux utilisateur
1. L'utilisateur crée un scénario de coûts.
2. Il renseigne les centres et les lignes de coûts.
3. L'application calcule automatiquement les montants.
4. Les résultats sont affichés pour les centres d'analyse et pour le direct costing.

## Arborescence
```text
projet_M1/
├─ manage.py
├─ projet_m1/
├─ apps/
│  ├─ dashboard/
│  └─ costs/
├─ templates/
└─ requirements.txt
```

## Lancement
1. Installer les dépendances : `pip install -r requirements.txt`
2. Créer les migrations : `python manage.py makemigrations`
3. Appliquer les migrations : `python manage.py migrate`
4. Lancer le serveur : `python manage.py runserver`

## Suite logique
- ajouter l’authentification utilisateur
- ajouter des formulaires de saisie complets
- enrichir les calculs par marges et rapports exportables