from django import forms

from .models import CostCenter, CostLine, CostScenario, Product, VariableCost


class CostScenarioForm(forms.ModelForm):
    class Meta:
        model = CostScenario
        fields = [
            "name",
            "period",
            "description",
            "method",
            "preset",
            "ui_mode",
        ]
        labels = {
            "name": "Nom du scénario",
            "period": "Période",
            "description": "Description",
            "method": "Méthode de calcul",
            "preset": "Template métier",
            "ui_mode": "Niveau de détail",
        }
        help_texts = {
            "method": "Choisissez la méthode principale pour ce scénario.",
            "preset": "Préconfiguration adaptée à votre contexte.",
            "ui_mode": "Simple pour aller vite, Expert pour options avancées.",
        }


class CostCenterForm(forms.ModelForm):
    class Meta:
        model = CostCenter
        fields = ["scenario", "code", "name", "is_auxiliary"]


class CostLineForm(forms.ModelForm):
    class Meta:
        model = CostLine
        fields = ["label", "amount", "is_direct", "center"]

    def __init__(self, *args, scenario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if scenario and scenario.ui_mode == "simple":
            self.fields.pop("center")


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "quantity", "unit_price"]
        labels = {
            "name": "Nom du produit",
            "quantity": "Quantité",
            "unit_price": "Prix de vente unitaire",
        }

    def __init__(self, *args, scenario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scenario = scenario


class VariableCostForm(forms.ModelForm):
    class Meta:
        model = VariableCost
        fields = ["name", "category", "amount", "product"]
