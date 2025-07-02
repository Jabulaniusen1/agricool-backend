from celery.schedules import crontab

beat_schedule = {
    "storage_recompute_computed_fields": {
        "task": "base.apps.storage.tasks.computed_fields.recompute_computed_fields",
        "schedule": crontab(minute=0, hour=1),
    },
    "update_temperature": {
        "task": "base.apps.storage.tasks.ecozen_call.update_temperature",
        "schedule": crontab(minute=0, hour="*/4"),
    },
    "recompute_digital_twin": {
        "task": "base.apps.storage.tasks.digital_twins.recompute_digital_twin",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "market_survey_checks": {
        "task": "base.apps.storage.tasks.notifications.market_survey_checks",
        "schedule": crontab(minute=0, hour=1, day_of_week=1),
    },
    "time_to_pick_up_notifications": {
        "task": "base.apps.storage.tasks.notifications.time_to_pick_up_notifications",
        "schedule": crontab(minute=0, hour="*/12"),
    },
}
