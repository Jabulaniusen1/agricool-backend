from celery.schedules import crontab

# Schedule constants
RECOMPUTE_FIELDS_MINUTE = 0
RECOMPUTE_FIELDS_HOUR = 1
EVERY_MINUTE = "*"

# Task name constants
RECOMPUTE_TASK = "base.apps.marketplace.tasks.computed_fields.recompute_computed_fields"
EXPIRE_ORDERS_TASK = "base.apps.marketplace.tasks.orders.expire_unpaid_orders"

beat_schedule = {
    "marketplace_recompute_computed_fields": {
        "task": RECOMPUTE_TASK,
        "schedule": crontab(minute=RECOMPUTE_FIELDS_MINUTE, hour=RECOMPUTE_FIELDS_HOUR),
    },
    "expire_unpaid_orders": {
        "task": EXPIRE_ORDERS_TASK,
        "schedule": crontab(minute=EVERY_MINUTE), # Every minute
    },
}
