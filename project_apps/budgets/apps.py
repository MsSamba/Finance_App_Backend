from django.apps import AppConfig


class BudgetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'project_apps.budgets'
    verbose_name = 'Budget Management'

    def ready(self):
        import project_apps.budgets.signals
