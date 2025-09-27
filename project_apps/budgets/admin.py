from django.contrib import admin
from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "category",
        "limit",
        "spent",
        "status",
        "is_over_budget_display",
        "is_alert_threshold_reached_display",
        "updated_at",
    )
    list_filter = ("status", "category")
    search_fields = ("user__username", "category")

    # --- Custom display methods ---
    @admin.display(boolean=True, description="Over Budget?")
    def is_over_budget_display(self, obj):
        return obj.is_over_budget

    @admin.display(boolean=True, description="Alert Threshold Reached?")
    def is_alert_threshold_reached_display(self, obj):
        return obj.is_alert_threshold_reached