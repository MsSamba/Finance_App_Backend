from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Q
from decimal import Decimal
from .models import RecurringBill
from .serializers import RecurringBillSerializer, BulkOperationSerializer, BillStatsSerializer

class RecurringBillViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringBillSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return bills for the current user only"""
        return RecurringBill.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Set the user when creating a new bill"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def toggle_paid(self, request, pk=None):
        """Toggle the paid status of a specific bill"""
        bill = self.get_object()
        bill.paid = not bill.paid
        bill.save()
        
        serializer = self.get_serializer(bill)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_operations(self, request):
        """Handle bulk operations like mark all paid or reset all"""
        serializer = BulkOperationSerializer(data=request.data)
        if serializer.is_valid():
            action_type = serializer.validated_data['action']
            queryset = self.get_queryset()
            
            if action_type == 'mark_all_paid':
                updated_count = queryset.filter(paid=False).update(paid=True)
                return Response({
                    'message': f'Marked {updated_count} bills as paid',
                    'updated_count': updated_count
                })
            
            elif action_type == 'reset_all':
                updated_count = queryset.filter(paid=True).update(paid=False)
                return Response({
                    'message': f'Reset {updated_count} bills to unpaid',
                    'updated_count': updated_count
                })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics about bills"""
        queryset = self.get_queryset()
        
        # Calculate total monthly bills
        monthly_bills_total = queryset.filter(
            frequency='monthly'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Count paid and unpaid bills
        paid_count = queryset.filter(paid=True).count()
        unpaid_count = queryset.filter(paid=False).count()
        total_count = queryset.count()
        
        stats_data = {
            'total_monthly_bills': float(monthly_bills_total),
            'paid_count': paid_count,
            'unpaid_count': unpaid_count,
            'total_count': total_count
        }
        
        serializer = BillStatsSerializer(stats_data)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """Override list to include stats in response"""
        response = super().list(request, *args, **kwargs)
        
        # Add stats to the response
        queryset = self.get_queryset()
        monthly_bills_total = queryset.filter(
            frequency='monthly'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        response.data = {
            'results': response.data,
            'stats': {
                'total_monthly_bills': float(monthly_bills_total),
                'paid_count': queryset.filter(paid=True).count(),
                'unpaid_count': queryset.filter(paid=False).count(),
                'total_count': queryset.count()
            }
        }
        
        return response
