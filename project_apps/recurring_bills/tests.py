from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta
from .models import RecurringBill
from .services import RecurringBillService

class RecurringBillModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_recurring_bill(self):
        bill = RecurringBill.objects.create(
            user=self.user,
            name='Rent',
            amount=Decimal('1500.00'),
            due_date=date.today(),
            frequency='monthly'
        )
        
        self.assertEqual(bill.name, 'Rent')
        self.assertEqual(bill.amount, Decimal('1500.00'))
        self.assertEqual(bill.frequency, 'monthly')
        self.assertFalse(bill.paid)
        self.assertEqual(bill.status, 'Pending')
    
    def test_mark_paid(self):
        bill = RecurringBill.objects.create(
            user=self.user,
            name='Utilities',
            amount=Decimal('200.00'),
            due_date=date.today(),
            frequency='monthly'
        )
        
        bill.mark_paid()
        self.assertTrue(bill.paid)
        self.assertEqual(bill.status, 'Paid')

class RecurringBillAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.bill_data = {
            'name': 'Internet',
            'amount': '80.00',
            'dueDate': '2024-01-15',
            'frequency': 'monthly'
        }
    
    def test_create_bill(self):
        response = self.client.post('/api/bills/', self.bill_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RecurringBill.objects.count(), 1)
        
        bill = RecurringBill.objects.first()
        self.assertEqual(bill.name, 'Internet')
        self.assertEqual(bill.user, self.user)
    
    def test_list_bills_with_stats(self):
        RecurringBill.objects.create(
            user=self.user,
            name='Rent',
            amount=Decimal('1500.00'),
            due_date=date.today(),
            frequency='monthly'
        )
        
        response = self.client.get('/api/bills/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('stats', response.data)
        self.assertEqual(response.data['stats']['total_count'], 1)
    
    def test_bulk_mark_paid(self):
        RecurringBill.objects.create(
            user=self.user,
            name='Bill 1',
            amount=Decimal('100.00'),
            due_date=date.today(),
            frequency='monthly'
        )
        RecurringBill.objects.create(
            user=self.user,
            name='Bill 2',
            amount=Decimal('200.00'),
            due_date=date.today(),
            frequency='monthly'
        )
        
        response = self.client.post('/api/bills/bulk_operations/', {
            'action': 'mark_all_paid'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)
        
        # Verify bills are marked as paid
        paid_bills = RecurringBill.objects.filter(paid=True).count()
        self.assertEqual(paid_bills, 2)

class RecurringBillServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_calculate_monthly_budget_impact(self):
        # Create bills with different frequencies
        RecurringBill.objects.create(
            user=self.user,
            name='Monthly Bill',
            amount=Decimal('100.00'),
            due_date=date.today(),
            frequency='monthly'
        )
        RecurringBill.objects.create(
            user=self.user,
            name='Weekly Bill',
            amount=Decimal('25.00'),
            due_date=date.today(),
            frequency='weekly'
        )
        
        impact = RecurringBillService.calculate_monthly_budget_impact(self.user)
        
        # Monthly: 100 + Weekly: 25 * 4.33 = 208.25
        expected = 100.00 + (25.00 * 4.33)
        self.assertAlmostEqual(impact, expected, places=2)
