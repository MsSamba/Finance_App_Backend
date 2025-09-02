from django.core.management.base import BaseCommand
from budgets.models import BudgetTemplate, BudgetTemplateItem


class Command(BaseCommand):
    help = 'Create default budget templates'

    def handle(self, *args, **options):
        # Basic Monthly Budget Template
        basic_template, created = BudgetTemplate.objects.get_or_create(
            name='Basic Monthly Budget',
            defaults={
                'description': 'A simple monthly budget covering essential categories',
                'is_default': True
            }
        )

        if created:
            basic_items = [
                {'category': 'Food & Dining', 'limit': 15000, 'color': 'bg-green-500'},
                {'category': 'Transportation', 'limit': 8000, 'color': 'bg-blue-500'},
                {'category': 'Shopping', 'limit': 10000, 'color': 'bg-purple-500'},
                {'category': 'Entertainment', 'limit': 5000, 'color': 'bg-pink-500'},
                {'category': 'Bills & Utilities', 'limit': 12000, 'color': 'bg-red-500'},
                {'category': 'Healthcare', 'limit': 3000, 'color': 'bg-indigo-500'},
            ]

            for item_data in basic_items:
                BudgetTemplateItem.objects.create(
                    template=basic_template,
                    **item_data
                )

        # Comprehensive Monthly Budget Template
        comprehensive_template, created = BudgetTemplate.objects.get_or_create(
            name='Comprehensive Monthly Budget',
            defaults={
                'description': 'A detailed monthly budget with all major spending categories',
                'is_default': False
            }
        )

        if created:
            comprehensive_items = [
                {'category': 'Food & Dining', 'limit': 20000, 'color': 'bg-green-500'},
                {'category': 'Transportation', 'limit': 12000, 'color': 'bg-blue-500'},
                {'category': 'Shopping', 'limit': 15000, 'color': 'bg-purple-500'},
                {'category': 'Entertainment', 'limit': 8000, 'color': 'bg-pink-500'},
                {'category': 'Bills & Utilities', 'limit': 15000, 'color': 'bg-red-500'},
                {'category': 'Healthcare', 'limit': 5000, 'color': 'bg-indigo-500'},
                {'category': 'Education', 'limit': 7000, 'color': 'bg-yellow-500'},
                {'category': 'Personal Care', 'limit': 4000, 'color': 'bg-gray-500'},
                {'category': 'Travel', 'limit': 10000, 'color': 'bg-blue-500'},
                {'category': 'Gifts & Donations', 'limit': 3000, 'color': 'bg-green-500'},
            ]

            for item_data in comprehensive_items:
                BudgetTemplateItem.objects.create(
                    template=comprehensive_template,
                    **item_data
                )

        # Student Budget Template
        student_template, created = BudgetTemplate.objects.get_or_create(
            name='Student Budget',
            defaults={
                'description': 'A budget template designed for students',
                'is_default': False
            }
        )

        if created:
            student_items = [
                {'category': 'Food & Dining', 'limit': 8000, 'color': 'bg-green-500'},
                {'category': 'Transportation', 'limit': 3000, 'color': 'bg-blue-500'},
                {'category': 'Education', 'limit': 10000, 'color': 'bg-yellow-500'},
                {'category': 'Entertainment', 'limit': 3000, 'color': 'bg-pink-500'},
                {'category': 'Personal Care', 'limit': 2000, 'color': 'bg-gray-500'},
                {'category': 'Shopping', 'limit': 4000, 'color': 'bg-purple-500'},
            ]

            for item_data in student_items:
                BudgetTemplateItem.objects.create(
                    template=student_template,
                    **item_data
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully created budget templates')
        )
