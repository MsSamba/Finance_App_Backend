from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RecurringBillViewSet

# Create a router and register our viewset
router = DefaultRouter()
router.register(r'bills', RecurringBillViewSet, basename='recurringbill')

app_name = 'recurring_bills'

urlpatterns = [
    path('', include(router.urls)),
]
