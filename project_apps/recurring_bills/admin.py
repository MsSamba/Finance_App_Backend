from django.contrib import admin
from .models import RecurringBill

@admin.register(RecurringBill)
class RecurringBillAdmin(admin.ModelAdmin):
    list_display = ['name', 'amount', 'due_date', 'frequency', 'paid', 'user', 'created_at']
    list_filter = ['frequency', 'paid', 'due_date', 'created_at']
    search_fields = ['name', 'user__username']
    list_editable = ['paid']
    date_hierarchy = 'due_date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
