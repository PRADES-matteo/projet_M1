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
Exécuter les commandes depuis le dossier `projet_M1/`.

1. Créer un environnement virtuel (si besoin) :
```powershell
py -m venv .venv
```
2. Activer l'environnement virtuel (PowerShell) :
```powershell
.\.venv\Scripts\Activate.ps1
```
3. Installer les dépendances :
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
4. Créer et appliquer les migrations :
```powershell
python manage.py makemigrations
python manage.py migrate
```
4.5 (optionnel) Créer un utilisateur de démonstration et peupler la base avec des scénarios réalistes :
```powershell
python manage.py createdemo
```
Identifiants générés : `demo` / `demo123`
5. Lancer le serveur :
```powershell
python manage.py runserver
```

## Charger les scénarios de test
Pour importer les données d'exemple dans la base SQLite :
```powershell
python manage.py loaddata apps/costs/fixtures/sample_scenarios.json
```

Pour vérifier ensuite que les scénarios sont bien présents :
```powershell
python manage.py test apps.costs
```

## Accès au site
Une fois le serveur lancé, ouvrir :
- `http://127.0.0.1:8000/`

Si le port 8000 est déjà utilisé :
```powershell
python manage.py runserver 8080
```

## Suite logique
- ajouter l’authentification utilisateur
- ajouter des formulaires de saisie complets
- enrichir les calculs par marges et rapports exportables