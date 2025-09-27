from rest_framework import serializers
from .models import Category, Transaction
from django.contrib.auth.models import User

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'is_income_category', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class TransactionSerializer(serializers.ModelSerializer):
    signed_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'amount', 'description', 'category', 'type', 'date', 
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


# from rest_framework import serializers
# from .models import Transaction
# from django.contrib.auth.models import User

# class TransactionSerializer(serializers.ModelSerializer):
#     signed_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
#     class Meta:
#         model = Transaction
#         fields = [
#             'id', 'amount', 'description', 'category', 'type', 'date', 
#             'signed_amount', 'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at', 'signed_amount']
    
#     def validate(self, data):
#         if data.get('type') == 'expense' and not data.get('category'):
#             raise serializers.ValidationError({
#                 'category': 'Category is required for expense transactions.'
#             })
        
#         if data.get('type') == 'expense' and data.get('category'):
#             from budgets.models import Budget
#             user = self.context['request'].user
            
#             budget_exists = Budget.objects.filter(
#                 user=user,
#                 category=data['category'],
#                 status='active'
#             ).exists()
            
#             if not budget_exists:
#                 raise serializers.ValidationError({
#                     'category': f'No active budget found for category "{data["category"]}". Please create a budget for this category first.'
#                 })
        
#         return data
    
#     def create(self, validated_data):
#         validated_data['user'] = self.context['request'].user
#         transaction = super().create(validated_data)
        
#         if transaction.type == 'expense':
#             transaction.update_budget_spent()
        
#         return transaction

#     def update(self, instance, validated_data):
#         if instance.type == 'expense':
#             instance.reverse_budget_spent()
        
#         transaction = super().update(instance, validated_data)
        
#         if transaction.type == 'expense':
#             transaction.update_budget_spent()
        
#         return transaction

# class TransactionSummarySerializer(serializers.Serializer):
#     """Serializer for transaction summary statistics"""
#     total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
#     net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
#     transaction_count = serializers.IntegerField()
#     income_count = serializers.IntegerField()
#     expense_count = serializers.IntegerField()

