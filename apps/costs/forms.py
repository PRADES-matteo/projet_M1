from django import forms
from datetime import date

from .models import CostCenter, CostCenterAllocation, CostLine, CostScenario, Product, ProductCenterUsage, VariableCost, FixedCost


class CostScenarioForm(forms.ModelForm):
    PERIOD_CHOICES = [
        ("Mensuel", "Mensuel"),
        ("Trimestriel", "Trimestriel"),
        ("Semestriel", "Semestriel"),
        ("Annuel", "Annuel"),
        ("Personnalisé", "Personnalisé"),
    ]
    MONTH_CHOICES = [
        (1, "Janvier"), (2, "Février"), (3, "Mars"), (4, "Avril"),
        (5, "Mai"), (6, "Juin"), (7, "Juillet"), (8, "Août"),
        (9, "Septembre"), (10, "Octobre"), (11, "Novembre"), (12, "Décembre"),
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
        fields = ["name", "period", "description", "method", "preset"]
        widgets = {
            "name": forms.TextInput(attrs={
                "maxlength": "25",
                "placeholder": "Max 25 caractères",
            }),
        }
        labels = {
            "name": "Nom du scénario",
            "period": "Période",
            "description": "Description",
            "method": "Méthode de calcul",
            "preset": "Template métier",
        }
        help_texts = {
            "method": "Choisissez la méthode principale pour ce scénario.",
            "preset": "Préconfiguration adaptée à votre contexte.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_year = date.today().year
        year_choices = [(year, str(year)) for year in range(current_year - 2, current_year + 3)]
        if "period" in self.fields:
            self.fields["period"].widget = forms.HiddenInput()
        self.fields["period_year"].choices = year_choices
        self.fields["period_year"].initial = current_year
        if "preset" in self.fields:
            choices = list(self.fields["preset"].choices)
            if not choices or choices[0][0] != "":
                self.fields["preset"].choices = [("", "Aucun")] + choices
            self.fields["preset"].required = False
            self.fields["preset"].initial = ""

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
        fields = ["code", "name", "is_auxiliary", "unit_of_work", "total_units"]
        widgets = {
            "code": forms.TextInput(attrs={"placeholder": "Ex: CA, CF, ATM..."}),
            "name": forms.TextInput(attrs={"placeholder": "Ex: Centre Atelier"}),
            "unit_of_work": forms.TextInput(attrs={"placeholder": "Ex: heure machine"}),
            "total_units": forms.NumberInput(attrs={"step": "0.01"}),
        }
        labels = {
            "code": "Code",
            "name": "Nom du centre",
            "is_auxiliary": "Centre auxiliaire",
            "unit_of_work": "Unité d'œuvre",
            "total_units": "Nombre total d'unités d'œuvre",
        }
        help_texts = {
            "is_auxiliary": "Un centre auxiliaire répartit ses coûts vers d'autres centres.",
            "unit_of_work": "Laisser vide pour les centres auxiliaires.",
            "total_units": "Laisser à 0 pour les centres auxiliaires.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"


class CostCenterAllocationForm(forms.ModelForm):
    class Meta:
        model = CostCenterAllocation
        fields = ["to_center", "percentage"]
        widgets = {
            "percentage": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
        }
        labels = {
            "to_center": "Vers le centre",
            "percentage": "Pourcentage (%)",
        }

    def __init__(self, *args, scenario=None, from_center=None, **kwargs):
        super().__init__(*args, **kwargs)
        if scenario and from_center:
            self.fields["to_center"].queryset = CostCenter.objects.filter(
                scenario=scenario
            ).exclude(id=from_center.id)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class CostLineForm(forms.ModelForm):
    class Meta:
        model = CostLine
        fields = ["label", "amount", "is_direct", "center"]
        labels = {
            "label": "Libellé",
            "amount": "Montant",
            "is_direct": "Direct (lié à l'unité)",
            "center": "Centre de coût",
        }
        help_texts = {
            "is_direct": "Cocher si ce coût varie directement avec le volume du produit.",
            "center": "Sélectionnez le centre de coût associé (laisser vide si non applicable).",
        }

    def __init__(self, *args, scenario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if scenario:
            self.fields["center"].queryset = CostCenter.objects.filter(scenario=scenario)
            self.fields["center"].required = False
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        # AJOUTEZ "stock_initial" et "stock_final" ICI :
        fields = ["name", "quantity", "unit_price", "stock_initial", "stock_final"]
        labels = {
            "name": "Nom du produit",
            "quantity": "Quantité vendue prévue",
            "unit_price": "Prix de vente unitaire",
            "stock_initial": "Stock initial (unités)",
            "stock_final": "Stock final visé (unités)",
        }

    def __init__(self, *args, scenario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scenario = scenario
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"


class ProductCenterUsageForm(forms.ModelForm):
    class Meta:
        model = ProductCenterUsage
        fields = ["units_used"]
        widgets = {
            "units_used": forms.NumberInput(attrs={"step": "0.01", "min": "0", "class": "form-control"}),
        }
        labels = {
            "units_used": "Unités d'œuvre consommées",
        }


class VariableCostForm(forms.ModelForm):
    class Meta:
        model = VariableCost
        fields = ["name", "category", "amount", "product"]
        labels = {
            "name": "Nom",
            "category": "Catégorie",
            "amount": "Montant",
            "product": "Produit",
        }

    def __init__(self, *args, scenario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if scenario and scenario.method == "direct_costing":
            self.fields.pop("product", None)
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"


class FixedCostForm(forms.ModelForm):
    is_common = forms.TypedChoiceField(
        label="Type",
        choices=[("true", "Commune"), ("false", "Spécifique")],
        coerce=lambda value: value == "true",
        widget=forms.RadioSelect,
        required=True,
    )

    class Meta:
        model = FixedCost
        fields = ["name", "category", "amount", "is_common", "product"]
        labels = {
            "name": "Nom",
            "category": "Catégorie",
            "amount": "Montant",
            "product": "Produit",
        }
        help_texts = {
            "is_common": "Cochez pour une charge commune, décochez pour une charge spécifique.",
            "product": "Associez le coût fixe à un produit uniquement s'il est spécifique.",
        }

    def __init__(self, *args, scenario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scenario = scenario
        if scenario and scenario.method == "direct_costing":
            self.fields.pop("is_common", None)
            self.fields.pop("product", None)
        else:
            self.fields["is_common"].initial = "true" if getattr(self.instance, "is_common", True) else "false"
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        if "is_common" not in self.fields:
            return cleaned_data
        is_common = cleaned_data.get("is_common")
        product = cleaned_data.get("product")
        if not is_common and not product:
            self.add_error("product", "Sélectionnez un produit pour une charge spécifique.")
        return cleaned_data
