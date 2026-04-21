from django.contrib import admin
from .models import Prediction


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'result', 'accuracy', 'feedback', 'source')
    list_filter = ('result', 'feedback', 'source', 'created_at')
    search_fields = ('message', 'explanation', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
