from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

class RecurringBill(models.Model):
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recurring_bills')
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['due_date', 'name']
        
    def __str__(self):
        return f"{self.name} - KES {self.amount} ({self.frequency})"
    
    @property
    def status(self):
        return "Paid" if self.paid else "Pending"
    
    def mark_paid(self):
        """Mark this bill as paid"""
        self.paid = True
        self.save()
    
    def mark_unpaid(self):
        """Mark this bill as unpaid"""
        self.paid = False
        self.save()
