from django.contrib import admin
from .models import Transaction
from project_apps.transactions.models import Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'is_income_category', 'created_at']
    list_filter = ['is_income_category', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['description', 'amount', 'type', 'user', 'date', 'created_at']
    list_filter = ['type', 'date', 'created_at']
    search_fields = ['description', 'user__username']
    readonly_fields = ['id', 'signed_amount', 'created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)