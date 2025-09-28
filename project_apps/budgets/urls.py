from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BudgetViewSet, BudgetHistoryViewSet, BudgetAlertViewSet, BudgetTemplateViewSet

router = DefaultRouter()
router.register(r'budgets', BudgetViewSet, basename='budget')
router.register(r'budget-history', BudgetHistoryViewSet, basename='budgethistory')
router.register(r'budget-alerts', BudgetAlertViewSet, basename='budgetalert')
router.register(r'budget-templates', BudgetTemplateViewSet, basename='budgettemplate')

urlpatterns = [
    path('', include(router.urls)),
]
