from django import forms

from .models import CostCenter, CostLine, CostScenario


class CostScenarioForm(forms.ModelForm):
    class Meta:
        model = CostScenario
        fields = ["name", "period", "description"]


class CostCenterForm(forms.ModelForm):
    class Meta:
        model = CostCenter
        fields = ["scenario", "code", "name", "is_auxiliary"]


class CostLineForm(forms.ModelForm):
    class Meta:
        model = CostLine
        fields = ["scenario", "label", "amount", "center", "is_direct"]
