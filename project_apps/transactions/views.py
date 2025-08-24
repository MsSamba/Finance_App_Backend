from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from decimal import Decimal
from .models import Transaction, Category
from .serializers import TransactionSerializer, CategorySerializer, TransactionSummarySerializer

class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing transaction categories"""
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Return all categories"""
        return Category.objects.all()
    
    @action(detail=False, methods=['post'])
    def create_defaults(self, request):
        """Create default categories"""
        default_categories = [
            {'name': 'Income', 'icon': '💰', 'is_income_category': True},
            {'name': 'Bills and Utilities', 'icon': '🏠', 'is_income_category': False},
            {'name': 'Education and Self Improvement', 'icon': '📚', 'is_income_category': False},
            {'name': 'Entertainment and Leisure', 'icon': '🎬', 'is_income_category': False},
            {'name': 'Family and Kids', 'icon': '👨‍👩‍👧‍👦', 'is_income_category': False},
            {'name': 'Food and Dining', 'icon': '🍽️', 'is_income_category': False},
            {'name': 'Health and Wellness', 'icon': '🏥', 'is_income_category': False},
            {'name': 'Savings and Investments', 'icon': '📈', 'is_income_category': False},
            {'name': 'Shopping and Personal Care', 'icon': '🛍️', 'is_income_category': False},
            {'name': 'Transportation', 'icon': '🚗', 'is_income_category': False},
        ]
        
        created_categories = []
        for cat_data in default_categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            if created:
                created_categories.append(category)
        
        serializer = self.get_serializer(created_categories, many=True)
        return Response({
            'message': f'Created {len(created_categories)} default categories',
            'categories': serializer.data
        })

class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing transactions"""
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'category', 'date']
    search_fields = ['description']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date', '-created_at']
    
    def get_queryset(self):
        """Return transactions for current user"""
        queryset = Transaction.objects.filter(user=self.request.user)
        
        # Date range filtering
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get transaction summary statistics"""
        queryset = self.get_queryset()
        
        # Calculate totals
        income_total = queryset.filter(type='income').aggregate(
            total=Coalesce(Sum('amount'), Decimal('0'))
        )['total']
        
        expense_total = queryset.filter(type='expense').aggregate(
            total=Coalesce(Sum('amount'), Decimal('0'))
        )['total']
        
        # Count transactions
        counts = queryset.aggregate(
            total_count=Count('id'),
            income_count=Count('id', filter=Q(type='income')),
            expense_count=Count('id', filter=Q(type='expense'))
        )
        
        summary_data = {
            'total_income': income_total,
            'total_expenses': expense_total,
            'net_amount': income_total - expense_total,
            'transaction_count': counts['total_count'],
            'income_count': counts['income_count'],
            'expense_count': counts['expense_count']
        }
        
        serializer = TransactionSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent transactions"""
        limit = int(request.query_params.get('limit', 10))
        queryset = self.get_queryset()[:limit]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)