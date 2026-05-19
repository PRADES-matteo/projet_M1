from django import forms
from datetime import date

from .models import CostCenter, CostLine, CostScenario, Product, VariableCost, FixedCost


class CostScenarioForm(forms.ModelForm):
    PERIOD_CHOICES = [
        ("Mensuel", "Mensuel"),
        ("Trimestriel", "Trimestriel"),
        ("Semestriel", "Semestriel"),
        ("Annuel", "Annuel"),
        ("Personnalisé", "Personnalisé"),
    ]
    MONTH_CHOICES = [
        (1, "Janvier"),
        (2, "Février"),
        (3, "Mars"),
        (4, "Avril"),
        (5, "Mai"),
        (6, "Juin"),
        (7, "Juillet"),
        (8, "Août"),
        (9, "Septembre"),
        (10, "Octobre"),
        (11, "Novembre"),
        (12, "Décembre"),
    ]
    QUARTER_CHOICES = [("T1", "T1"), ("T2", "T2"), ("T3", "T3"), ("T4", "T4")]
    SEMESTER_CHOICES = [("S1", "S1"), ("S2", "S2")]

    period_year = forms.ChoiceField(label="Année", required=False)
    period_month = forms.ChoiceField(label="Mois", choices=MONTH_CHOICES, required=False)
    period_quarter = forms.ChoiceField(label="Trimestre", choices=QUARTER_CHOICES, required=False)
    period_semester = forms.ChoiceField(label="Semestre", choices=SEMESTER_CHOICES, required=False)
    period_start = forms.DateField(label="Date de début", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    period_end = forms.DateField(label="Date de fin", required=False, widget=forms.DateInput(attrs={"type": "date"}))

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_year = date.today().year
        year_choices = [(year, str(year)) for year in range(current_year - 2, current_year + 3)]
        self.fields["period"].widget = forms.HiddenInput()
        self.fields["period_year"].choices = year_choices
        self.fields["period_year"].initial = current_year

    def clean(self):
        cleaned_data = super().clean()
        period = cleaned_data.get("period")
        year = cleaned_data.get("period_year")
        month = cleaned_data.get("period_month")
        quarter = cleaned_data.get("period_quarter")
        semester = cleaned_data.get("period_semester")
        period_start = cleaned_data.get("period_start")
        period_end = cleaned_data.get("period_end")

        if not period:
            self.add_error("period", "Choisissez un type de période.")
            return cleaned_data

        if period in {"Mensuel", "Trimestriel", "Semestriel", "Annuel"} and not year:
            self.add_error("period_year", "Sélectionnez une année.")

        if period == "Mensuel" and not month:
            self.add_error("period_month", "Sélectionnez un mois.")

        if period == "Trimestriel" and not quarter:
            self.add_error("period_quarter", "Sélectionnez un trimestre.")

        if period == "Semestriel" and not semester:
            self.add_error("period_semester", "Sélectionnez un semestre.")

        if period == "Personnalisé":
            if not period_start:
                self.add_error("period_start", "Sélectionnez une date de début.")
            if not period_end:
                self.add_error("period_end", "Sélectionnez une date de fin.")
            if period_start and period_end and period_end < period_start:
                self.add_error("period_end", "La date de fin doit être postérieure à la date de début.")

        return cleaned_data


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


class FixedCostForm(forms.ModelForm):
    class Meta:
        model = FixedCost
        fields = ["name", "category", "amount", "is_common", "product"]
