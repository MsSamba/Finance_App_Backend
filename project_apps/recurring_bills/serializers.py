# from rest_framework import serializers
# from .models import RecurringBill

# class RecurringBillSerializer(serializers.ModelSerializer):
#     status = serializers.ReadOnlyField()
    
#     class Meta:
#         model = RecurringBill
#         fields = ['id', 'name', 'amount', 'due_date', 'frequency', 'paid', 'status', 'created_at', 'updated_at']
#         read_only_fields = ['created_at', 'updated_at']
    
#     def to_representation(self, instance):
#         """Convert the data to match frontend expectations"""
#         data = super().to_representation(instance)
#         # Convert due_date to string format expected by frontend
#         data['dueDate'] = data.pop('due_date')
#         return data
    
#     def to_internal_value(self, data):
#         """Convert frontend data to Django model format"""
#         # Handle camelCase to snake_case conversion
#         if 'dueDate' in data:
#             data['due_date'] = data.pop('dueDate')
#         return super().to_internal_value(data)

# class BulkOperationSerializer(serializers.Serializer):
#     """Serializer for bulk operations like mark all paid or reset all"""
#     action = serializers.ChoiceField(choices=['mark_all_paid', 'reset_all'])
    
# class BillStatsSerializer(serializers.Serializer):
#     """Serializer for bill statistics"""
#     total_monthly_bills = serializers.DecimalField(max_digits=10, decimal_places=2)
#     paid_count = serializers.IntegerField()
#     unpaid_count = serializers.IntegerField()
#     total_count = serializers.IntegerField()

from rest_framework import serializers
from .models import RecurringBill


class RecurringBillSerializer(serializers.ModelSerializer):
    status = serializers.ReadOnlyField()

    class Meta:
        model = RecurringBill
        fields = [
            'id',
            'name',
            'amount',
            'due_date',
            'frequency',
            'paid',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def to_representation(self, instance):
        """Convert the data to match frontend expectations"""
        data = super().to_representation(instance)

        # Convert due_date to camelCase
        data['dueDate'] = data.pop('due_date')

        # Ensure amount is always a number (float)
        if 'amount' in data and data['amount'] is not None:
            data['amount'] = float(data['amount'])

        return data

    def to_internal_value(self, data):
        """Convert frontend data to Django model format"""
        # Handle camelCase to snake_case conversion
        if 'dueDate' in data:
            data['due_date'] = data.pop('dueDate')
        return super().to_internal_value(data)


class BulkOperationSerializer(serializers.Serializer):
    """Serializer for bulk operations like mark all paid or reset all"""
    action = serializers.ChoiceField(choices=['mark_all_paid', 'reset_all'])


class BillStatsSerializer(serializers.Serializer):
    """Serializer for bill statistics"""
    total_monthly_bills = serializers.FloatField()  # ✅ always return number
    paid_count = serializers.IntegerField()
    unpaid_count = serializers.IntegerField()
    total_count = serializers.IntegerField()
