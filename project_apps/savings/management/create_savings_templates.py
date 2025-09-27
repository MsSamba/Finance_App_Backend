from django.core.management.base import BaseCommand
from savings.models import SavingsTemplate
from decimal import Decimal

class Command(BaseCommand):
    help = 'Create default savings goal templates'

    def handle(self, *args, **options):
        templates_data = [
            {
                'name': 'Emergency Fund',
                'description': 'Build an emergency fund to cover 3-6 months of expenses',
                'suggested_amount': Decimal('100000.00'),
                'suggested_timeline_months': 12,
                'color': 'bg-red-500',
                'priority': 'urgent',
                'category': 'security',
                'is_default': True,
            },
            {
                'name': 'Vacation Fund',
                'description': 'Save for your dream vacation or holiday trip',
                'suggested_amount': Decimal('50000.00'),
                'suggested_timeline_months': 6,
                'color': 'bg-blue-500',
                'priority': 'medium',
                'category': 'lifestyle',
                'is_default': True,
            },
            {
                'name': 'New Car',
                'description': 'Save for a down payment or full purchase of a vehicle',
                'suggested_amount': Decimal('200000.00'),
                'suggested_timeline_months': 18,
                'color': 'bg-green-500',
                'priority': 'high',
                'category': 'transportation',
                'is_default': True,
            },
            {
                'name': 'Home Down Payment',
                'description': 'Save for a house down payment or real estate investment',
                'suggested_amount': Decimal('500000.00'),
                'suggested_timeline_months': 24,
                'color': 'bg-purple-500',
                'priority': 'high',
                'category': 'housing',
                'is_default': True,
            },
            {
                'name': 'Wedding Fund',
                'description': 'Save for your dream wedding celebration',
                'suggested_amount': Decimal('150000.00'),
                'suggested_timeline_months': 12,
                'color': 'bg-pink-500',
                'priority': 'medium',
                'category': 'lifestyle',
                'is_default': True,
            },
            {
                'name': 'Education Fund',
                'description': 'Save for education, courses, or skill development',
                'suggested_amount': Decimal('75000.00'),
                'suggested_timeline_months': 8,
                'color': 'bg-indigo-500',
                'priority': 'high',
                'category': 'education',
                'is_default': True,
            },
            {
                'name': 'Business Startup',
                'description': 'Build capital for starting your own business',
                'suggested_amount': Decimal('300000.00'),
                'suggested_timeline_months': 18,
                'color': 'bg-yellow-500',
                'priority': 'high',
                'category': 'business',
                'is_default': True,
            },
            {
                'name': 'Gadget Fund',
                'description': 'Save for electronics, gadgets, or tech upgrades',
                'suggested_amount': Decimal('25000.00'),
                'suggested_timeline_months': 4,
                'color': 'bg-gray-500',
                'priority': 'low',
                'category': 'technology',
                'is_default': True,
            },
        ]

        created_count = 0
        
        for template_data in templates_data:
            template, created = SavingsTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Template already exists: {template.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nCreated {created_count} new savings templates')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Total templates available: {SavingsTemplate.objects.count()}')
        )
