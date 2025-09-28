# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.utils import timezone
# from decimal import Decimal
# import logging

# from .models import SavingsAccount, SavingsSettings, SavingsTransaction, SavingsGoal

# logger = logging.getLogger(__name__)


# @receiver(post_save, sender='finance.Transaction')
# def auto_save_on_income(sender, instance, created, **kwargs):
#     """
#     Automatically save percentage of income when income transaction is created
#     """
#     # Only process new income transactions
#     if not created or instance.transaction_type != 'income':
#         return
    
#     try:
#         # Get or create savings account for the user
#         savings_account, account_created = SavingsAccount.objects.get_or_create(
#             user=instance.user,
#             defaults={
#                 'balance': Decimal('0.00'),
#                 'auto_save_percentage': Decimal('20.00'),
#                 'is_auto_save_enabled': True
#             }
#         )
        
#         # Get user's savings settings
#         try:
#             settings = SavingsSettings.objects.get(user=instance.user)
#             auto_save_enabled = settings.auto_save_enabled
#             auto_save_percentage = settings.auto_save_percentage
#         except SavingsSettings.DoesNotExist:
#             # Use account settings as fallback
#             auto_save_enabled = savings_account.is_auto_save_enabled
#             auto_save_percentage = savings_account.auto_save_percentage
        
#         # Check if auto-save is enabled
#         if not auto_save_enabled or auto_save_percentage <= 0:
#             logger.info(f"Auto-save disabled for user {instance.user.username}")
#             return
        
#         # Calculate savings amount (20% of income)
#         income_amount = Decimal(str(instance.amount))
#         savings_amount = income_amount * (auto_save_percentage / 100)
        
#         # Add to savings account
#         old_balance = savings_account.balance
#         savings_account.balance += savings_amount
#         savings_account.save(update_fields=['balance', 'updated_at'])
        
#         # Create savings transaction record
#         SavingsTransaction.objects.create(
#             savings_account=savings_account,
#             transaction_type='auto_save',
#             amount=savings_amount,
#             description=f"Auto-save {auto_save_percentage}% from income: {instance.description}",
#             balance_before=old_balance,
#             balance_after=savings_account.balance,
#             reference_transaction_id=instance.id
#         )
        
#         # Auto-allocate to goals if enabled
#         auto_allocate_to_goals(savings_account, savings_amount)
        
#         logger.info(
#             f"Auto-saved KES {savings_amount} ({auto_save_percentage}%) from income "
#             f"transaction {instance.id} for user {instance.user.username}"
#         )
        
#     except Exception as e:
#         logger.error(f"Error in auto_save_on_income: {str(e)}")


# def auto_allocate_to_goals(savings_account, amount):
#     """
#     Auto-allocate savings to goals with auto-allocation enabled
#     """
#     try:
#         # Get goals with auto-allocation enabled
#         auto_goals = SavingsGoal.objects.filter(
#             user=savings_account.user,
#             status='active',
#             auto_allocate_enabled=True,
#             auto_allocate_percentage__gt=0
#         ).order_by('priority', 'created_at')
        
#         if not auto_goals.exists():
#             return
        
#         # Calculate total auto-allocation percentage
#         total_percentage = sum(goal.auto_allocate_percentage for goal in auto_goals)
        
#         if total_percentage <= 0:
#             return
        
#         # Allocate proportionally
#         remaining_amount = amount
        
#         for goal in auto_goals:
#             if remaining_amount <= 0:
#                 break
            
#             # Calculate allocation amount
#             allocation_percentage = goal.auto_allocate_percentage / total_percentage
#             allocation_amount = amount * allocation_percentage
            
#             # Don't exceed the remaining goal amount
#             max_allocation = min(allocation_amount, goal.remaining_amount, remaining_amount)
            
#             if max_allocation > 0:
#                 # Withdraw from savings account
#                 if savings_account.withdraw_funds(
#                     max_allocation, 
#                     f"Auto-allocated to {goal.name}"
#                 ):
#                     # Add to goal
#                     goal.add_funds(
#                         max_allocation, 
#                         source='auto_allocation',
#                         description=f"Auto-allocation ({goal.auto_allocate_percentage}%)"
#                     )
#                     remaining_amount -= max_allocation
                    
#                     logger.info(
#                         f"Auto-allocated KES {max_allocation} to goal '{goal.name}' "
#                         f"for user {savings_account.user.username}"
#                     )
        
#     except Exception as e:
#         logger.error(f"Error in auto_allocate_to_goals: {str(e)}")


# @receiver(post_save, sender='django.contrib.auth.models.User')
# def create_savings_account_and_settings(sender, instance, created, **kwargs):
#     """
#     Create savings account and settings for new users
#     """
#     if created:
#         try:
#             # Create savings account
#             SavingsAccount.objects.get_or_create(
#                 user=instance,
#                 defaults={
#                     'balance': Decimal('0.00'),
#                     'auto_save_percentage': Decimal('20.00'),
#                     'is_auto_save_enabled': True
#                 }
#             )
            
#             # Create savings settings
#             SavingsSettings.objects.get_or_create(
#                 user=instance,
#                 defaults={
#                     'auto_save_enabled': True,
#                     'auto_save_percentage': Decimal('20.00'),
#                     'email_notifications': True,
#                     'goal_reminders': True,
#                     'monthly_reports': True,
#                     'achievement_notifications': True
#                 }
#             )
            
#             logger.info(f"Created savings account and settings for new user: {instance.username}")
            
#         except Exception as e:
#             logger.error(f"Error creating savings account for user {instance.username}: {str(e)}")


from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
import logging

from .models import SavingsAccount, SavingsSettings, SavingsTransaction, SavingsGoal

logger = logging.getLogger(__name__)


@receiver(post_save, sender='finance.Transaction')
def auto_save_on_income(sender, instance, created, **kwargs):
    """
    Automatically save percentage of income when income transaction is created
    """
    # Only process new income transactions
    if not created or instance.transaction_type != 'income':
        return
    
    try:
        # Get or create savings account for the user
        savings_account, account_created = SavingsAccount.objects.get_or_create(
            user=instance.user,
            defaults={
                'balance': Decimal('0.00'),
                'auto_save_percentage': Decimal('20.00'),
                'is_auto_save_enabled': True
            }
        )
        
        # Get user's savings settings
        try:
            settings = SavingsSettings.objects.get(user=instance.user)
            auto_save_enabled = settings.auto_save_enabled
            auto_save_percentage = settings.auto_save_percentage
        except SavingsSettings.DoesNotExist:
            # Use account settings as fallback
            auto_save_enabled = savings_account.is_auto_save_enabled
            auto_save_percentage = savings_account.auto_save_percentage
        
        # Check if auto-save is enabled
        if not auto_save_enabled or auto_save_percentage <= 0:
            logger.info(f"Auto-save disabled for user {instance.user.username}")
            return
        
        # Calculate savings amount (20% of income)
        income_amount = Decimal(str(instance.amount))
        savings_amount = income_amount * (auto_save_percentage / 100)
        
        # Add to savings account
        old_balance = savings_account.balance
        savings_account.balance += savings_amount
        savings_account.save(update_fields=['balance', 'updated_at'])
        
        # Create savings transaction record
        SavingsTransaction.objects.create(
            savings_account=savings_account,
            transaction_type='auto_save',
            amount=savings_amount,
            description=f"Auto-save {auto_save_percentage}% from income: {instance.description}",
            balance_before=old_balance,
            balance_after=savings_account.balance,
            reference_transaction_id=instance.id
        )
        
        # Auto-allocate to goals if enabled
        auto_allocate_to_goals(savings_account, savings_amount)
        
        logger.info(
            f"Auto-saved KES {savings_amount} ({auto_save_percentage}%) from income "
            f"transaction {instance.id} for user {instance.user.username}"
        )
        
    except Exception as e:
        logger.error(f"Error in auto_save_on_income: {str(e)}")


def auto_allocate_to_goals(savings_account, amount):
    """
    Auto-allocate savings to goals with auto-allocation enabled
    """
    try:
        # Get goals with auto-allocation enabled
        auto_goals = SavingsGoal.objects.filter(
            user=savings_account.user,
            status='active',
            auto_allocate_enabled=True,
            auto_allocate_percentage__gt=0
        ).order_by('priority', 'created_at')
        
        if not auto_goals.exists():
            return
        
        # Calculate total auto-allocation percentage
        total_percentage = sum(goal.auto_allocate_percentage for goal in auto_goals)
        
        if total_percentage <= 0:
            return
        
        # Allocate proportionally
        remaining_amount = amount
        
        for goal in auto_goals:
            if remaining_amount <= 0:
                break
            
            # Calculate allocation amount
            allocation_percentage = goal.auto_allocate_percentage / total_percentage
            allocation_amount = amount * allocation_percentage
            
            # Don't exceed the remaining goal amount
            max_allocation = min(allocation_amount, goal.remaining_amount, remaining_amount)
            
            if max_allocation > 0:
                # Withdraw from savings account
                if savings_account.withdraw_funds(
                    max_allocation, 
                    f"Auto-allocated to {goal.name}"
                ):
                    # Add to goal
                    goal.add_funds(
                        max_allocation, 
                        source='auto_allocation',
                        description=f"Auto-allocation ({goal.auto_allocate_percentage}%)"
                    )
                    remaining_amount -= max_allocation
                    
                    logger.info(
                        f"Auto-allocated KES {max_allocation} to goal '{goal.name}' "
                        f"for user {savings_account.user.username}"
                    )
        
    except Exception as e:
        logger.error(f"Error in auto_allocate_to_goals: {str(e)}")


@receiver(post_save, sender='django.contrib.auth.models.User')
def create_savings_account_and_settings(sender, instance, created, **kwargs):
    """
    Create savings account and settings for new users
    """
    if created:
        try:
            # Create savings account
            SavingsAccount.objects.get_or_create(
                user=instance,
                defaults={
                    'balance': Decimal('0.00'),
                    'auto_save_percentage': Decimal('20.00'),
                    'is_auto_save_enabled': True
                }
            )
            
            # Create savings settings
            SavingsSettings.objects.get_or_create(
                user=instance,
                defaults={
                    'auto_save_enabled': True,
                    'auto_save_percentage': Decimal('20.00'),
                    'email_notifications': True,
                    'goal_reminders': True,
                    'monthly_reports': True,
                    'achievement_notifications': True
                }
            )
            
            logger.info(f"Created savings account and settings for new user: {instance.username}")
            
        except Exception as e:
            logger.error(f"Error creating savings account for user {instance.username}: {str(e)}")
