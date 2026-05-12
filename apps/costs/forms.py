from django import forms
from decimal import Decimal

from .models import CostCenter, CostLine, CostScenario, Product


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


class ScenarioSettingsForm(forms.ModelForm):
    class Meta:
        model = CostScenario
        fields = ["input_mode", "preset", "ui_mode", "use_reciprocal_allocation", "use_seasonality"]
        labels = {
            "input_mode": "Mode de saisie des produits",
            "preset": "Template métier",
            "ui_mode": "Niveau de détail",
            "use_reciprocal_allocation": "Activer la répartition réciproque",
            "use_seasonality": "Activer la saisonnalité",
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
    entry_mode = forms.ChoiceField(
        label="Mode de saisie",
        choices=[("ca_total", "Je fournis le CA"), ("pv_volume", "Je fournis PV et volumes")],
        required=True,
    )
    revenue_total = forms.DecimalField(
        label="Chiffre d'affaires total",
        max_digits=14,
        decimal_places=2,
        required=False,
        min_value=Decimal("0"),
    )

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
        if scenario:
            self.fields["entry_mode"].initial = scenario.input_mode

    def clean(self):
        cleaned_data = super().clean()
        entry_mode = cleaned_data.get("entry_mode")
        quantity = cleaned_data.get("quantity")
        unit_price = cleaned_data.get("unit_price")
        revenue_total = cleaned_data.get("revenue_total")

        if entry_mode == "ca_total":
            if not revenue_total:
                self.add_error("revenue_total", "Le CA total est requis avec ce mode.")
            if not quantity or quantity <= 0:
                self.add_error("quantity", "La quantité est requise et doit être > 0.")
        else:
            if unit_price is None:
                self.add_error("unit_price", "Le prix unitaire est requis avec ce mode.")

        return cleaned_data
