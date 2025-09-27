from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SavingsAccountViewSet, SavingsGoalViewSet, SavingsTemplateViewSet,
    SavingsSettingsViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'account', SavingsAccountViewSet, basename='savingsaccount')
router.register(r'goals', SavingsGoalViewSet, basename='savingsgoal')
router.register(r'templates', SavingsTemplateViewSet, basename='savingstemplate')
router.register(r'settings', SavingsSettingsViewSet, basename='savingssettings')

app_name = 'savings'

urlpatterns = [
    path('', include(router.urls)),
]
