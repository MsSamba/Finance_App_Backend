from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
from django.db.models import Sum
from decimal import Decimal
from project_apps.transactions.models import Transaction
from .models import Budget


def recalc_budget(user, category):
    """Recalculate and update spent amount for a user's budget in a given category."""
    if not user or not category:
        return

    Transaction = apps.get_model("transactions", "Transaction")

    try:
        budget = Budget.objects.get(
            user=user,
            category=category,
            status="active"
        )

        total_spent = Transaction.objects.filter(
            user=user,
            category=category,
            type="expense",
            date__gte=budget.period_start,
            date__lte=budget.period_end,
        ).aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00")

        budget.spent = total_spent
        budget.save(update_fields=["spent", "updated_at"])

        # check alerts
        from .tasks import create_budget_alert
        if budget.is_alert_threshold_reached or budget.is_over_budget:
            create_budget_alert.delay(budget.id)

    except Budget.DoesNotExist:
        pass


@receiver(pre_save, sender=Transaction)
def track_old_category(sender, instance, **kwargs):
    """Store old category before updating a transaction"""
    if not instance.pk:  # new transaction, nothing to compare
        return

    try:
        old_instance = Transaction.objects.get(pk=instance.pk)
        instance._old_category = old_instance.category
    except Transaction.DoesNotExist:
        instance._old_category = None


@receiver(post_save, sender=Transaction)
def update_budget_spent_on_transaction_save(sender, instance, created, **kwargs):
    """Update budget spent when a transaction is created or updated"""

    # if category was changed, recalc old one too
    if hasattr(instance, "_old_category") and instance._old_category != instance.category:
        recalc_budget(instance.user, instance._old_category)

    # always recalc current category
    recalc_budget(instance.user, instance.category)


@receiver(post_delete, sender=Transaction)
def update_budget_spent_on_transaction_delete(sender, instance, **kwargs):
    """Update budget spent when a transaction is deleted"""
    recalc_budget(instance.user, instance.category)

