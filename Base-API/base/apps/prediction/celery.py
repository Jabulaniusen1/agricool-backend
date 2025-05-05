from celery.schedules import crontab

beat_schedule = {
    "prediction_calls": {
        "task": "base.apps.prediction.tasks.ml4.prediction_calls",
        "schedule": crontab(minute=30, hour=3),
    },
    "india_markets_data_db_insert": {
        "task": "base.apps.prediction.tasks.ml4.india_markets_data_db_insert",
        "schedule": crontab(minute=0, hour=3),
    },
    "prediction_calls_ng": {
        "task": "base.apps.prediction.tasks.ml4_ng.prediction_calls_ng",
        "schedule": crontab(minute="30", hour="2"),
    },
    "nigeria_markets_data_db_insert": {
        "task": "base.apps.prediction.tasks.ml4_ng.nigeria_states_data_db_insert",
        "schedule": crontab(minute="0", hour="2"),
    },
}
