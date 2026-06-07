# projet_M1

Application Django de comptabilité analytique (gestion des coûts) à usage pédagogique. Les utilisateurs créent des **scénarios** et analysent leurs coûts selon trois méthodes, avec des templates adaptés à leur secteur d'activité.

## Méthodes de calcul

| Méthode | Description |
|---|---|
| **Direct costing** | Sépare charges variables et charges fixes. Calcule MCV, seuil de rentabilité, point mort. |
| **Direct costing évolué** | Ajoute charges fixes spécifiques/communes par produit, saisonnalité mensuelle. |
| **Centres d'analyse** | Répartit les charges via centres auxiliaires → centres principaux, calcule le taux de cession par unité d'œuvre. |

## Templates métier (presets)

Chaque scénario peut adopter un template qui adapte l'affichage des résultats :

- **Industriel** — focus production : CMP, volumes, marges sur coût de production
- **Commercial** — focus rentabilité produit : classement par marge spécifique, taux de marge, contribution au résultat
- **Services** — focus charges fixes : cascade CA → MSCV → marge spécifique → résultat, détail CF communes/spécifiques

## Architecture

```
projet_M1/
├── manage.py
├── projet_m1/          # Config Django (settings, urls)
├── apps/
│   ├── dashboard/      # Page d'accueil
│   └── costs/          # Toute la logique métier
│       ├── models.py
│       ├── views.py
│       ├── forms.py
│       ├── services/   # Calculs purs (direct_costing.py, center_analysis_full.py)
│       ├── templatetags/
│       ├── management/commands/createdemo.py
│       └── fixtures/
├── templates/          # base.html, registration/
└── static/
```

## Installation et lancement

Toutes les commandes s'exécutent depuis `projet_M1/`.

```powershell
# 1. Environnement virtuel
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Dépendances
python -m pip install -r requirements.txt

# 3. Base de données
python manage.py migrate

# 4. (Optionnel) Données de démonstration
python manage.py createdemo
# Identifiants : demo / demo123

# 5. Serveur
python manage.py runserver
# ou sur un autre port :
python manage.py runserver 8080
```

Accès : `http://127.0.0.1:8000/`

## Scénarios de démonstration

`python manage.py createdemo` crée 9 scénarios couvrant les 3 méthodes × 3 templates :

| Nom | Méthode | Template |
|---|---|---|
| Industrie Alpha | Direct costing | Industriel |
| Commerce Beta | Direct costing | Commercial |
| Services Gamma | Direct costing | Services |
| Industrie Zeta — Évolué | Direct costing évolué | Industriel |
| Commerce Eta — Évolué | Direct costing évolué | Commercial |
| Services Iota — Évolué | Direct costing évolué | Services |
| Menuiserie Delta — Centres | Centres d'analyse | Industriel |
| Agence Epsilon — Centres | Centres d'analyse | Services |
| Distribution Kappa — Centres | Centres d'analyse | Commercial |

## Autres commandes utiles

```powershell
# Charger les fixtures (scénarios sans user associé)
python manage.py loaddata apps/costs/fixtures/sample_scenarios.json

# Lancer les tests
python manage.py test apps.costs

# Migrations après modification des modèles
python manage.py makemigrations
python manage.py migrate
```
