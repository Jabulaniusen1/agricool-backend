from celery.schedules import crontab

beat_schedule = {
    "marketplace_recompute_computed_fields": {
        "task": "base.apps.marketplace.tasks.computed_fields.recompute_computed_fields",
        "schedule": crontab(minute=0, hour=1),
    },
    "expire_unpaid_orders": {
        "task": "base.apps.marketplace.tasks.orders.expire_unpaid_orders",
        "schedule": crontab(minute="*"), # Every minute
    },
}
