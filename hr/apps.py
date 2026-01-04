from django.apps import AppConfig
from django.db.models.signals import post_migrate

class HrConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hr"

    def ready(self):
        from accounts.groups import setup_hr_groups

        def handler(sender, **kwargs):
            # sender is the app config that just migrated
            if sender.name == "hr":
                setup_hr_groups()

        post_migrate.connect(handler, dispatch_uid="hr_setup_groups")