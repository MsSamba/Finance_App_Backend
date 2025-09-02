from rest_framework import serializers
from .models import Transaction
from django.contrib.auth.models import User

# class CategorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Category
#         fields = ['id', 'name', 'icon', 'is_income_category', 'created_at', 'updated_at']
#         read_only_fields = ['id', 'created_at', 'updated_at']

class TransactionSerializer(serializers.ModelSerializer):
    signed_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'amount', 'description', 'type', 'date', 
            'signed_amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'signed_amount']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class TransactionSummarySerializer(serializers.Serializer):
    """Serializer for transaction summary statistics"""
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    transaction_count = serializers.IntegerField()
    income_count = serializers.IntegerField()
    expense_count = serializers.IntegerField()