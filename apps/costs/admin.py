from django.contrib import admin

from .models import CostCenter, CostLine, CostScenario

admin.site.register(CostScenario)
admin.site.register(CostCenter)
admin.site.register(CostLine)
