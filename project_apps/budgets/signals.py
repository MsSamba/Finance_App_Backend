from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from decimal import Decimal
from project_apps.transactions.models import Transaction


@receiver(post_save, sender=Transaction)
def update_budget_spent_on_transaction_save(sender, instance, created, **kwargs):
    """Update budget spent amount when a transaction is created or updated"""
    from .models import Budget

    if not instance.user:
        return

    try:
        budget = Budget.objects.get(
            user=instance.user,
            # category=instance.category,
            status="active"
        )

        from django.apps import apps
        Transaction = apps.get_model("transactions", "Transaction") 

        total_spent = Transaction.objects.filter(
            user=instance.user,
            # category=instance.category,
            transaction_type="expense",
            date__gte=budget.period_start,
            date__lte=budget.period_end
        ).aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00")

        budget.spent = total_spent
        budget.save(update_fields=["spent", "updated_at"])

        if budget.is_alert_threshold_reached or budget.is_over_budget:
            from .tasks import create_budget_alert
            create_budget_alert.delay(budget.id)

    except Budget.DoesNotExist:
        pass


@receiver(post_delete, sender=Transaction)
def update_budget_spent_on_transaction_delete(sender, instance, **kwargs):
    """Update budget spent amount when a transaction is deleted"""
    from .models import Budget

    if not instance.user:
        return

    try:
        budget = Budget.objects.get(
            user=instance.user,
            # category=instance.category,
            status="active"
        )

        from django.apps import apps
        Transaction = apps.get_model("transactions", "Transaction")  # ✅ FIXED

        total_spent = Transaction.objects.filter(
            user=instance.user,
            # category=instance.category,
            transaction_type="expense",
            date__gte=budget.period_start,
            date__lte=budget.period_end
        ).aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00")

        budget.spent = total_spent
        budget.save(update_fields=["spent", "updated_at"])

    except Budget.DoesNotExist:
        pass
