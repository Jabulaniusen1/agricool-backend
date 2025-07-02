import json
import math
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.core.mail import send_mail

from base.apps.storage.models import Crate
from base.apps.storage.services.ttpu import get_set_t
from base.celery import app
from base.settings import ENVIRONMENT

from ..models import CoolingUnitSpecifications, Crate

# Default shelf life buffer in days, can be adjusted as needed
DEFAULT_SHELF_LIFE_BUFFER = 0.5

@app.task
def recompute_digital_twin():
    five_hours_ago = datetime.now().astimezone() - timedelta(hours=5, minutes=30)

    crates = Crate.objects.filter(
        cooling_unit__location__company__digital_twin=True,
        weight__gt=0,
        runDT=True,
        produce__crop__digital_twin_identifier__isnull=False,
    ).distinct("produce")

    cooling_unit_temperatures = {}

    for crate in crates.iterator():
        if crate.modified_dt and crate.modified_dt.astimezone() > five_hours_ago:
            continue

        try:
            cu = crate.cooling_unit
            if cu.id not in cooling_unit_temperatures:
                cooling_unit_temperatures[cu.id] = {
                    "last_temperature": get_set_t(crate.id),
                    "temperature_history": get_temperature_lines(crate),
                }

            cached = cooling_unit_temperatures[cu.id]

            payload = {
                "callback_url": f"{settings.URL_BASE_API}/storage/v1/comsol/callback/",
                "context": {"crate_id": crate.id},
                "params": {
                    "fruit_index": crate.produce.crop.digital_twin_identifier,
                    "quality_dt": crate.quality_dt,
                    "shelf_life_buffer": DEFAULT_SHELF_LIFE_BUFFER,
                    "temperature_dt": crate.temperature_dt,
                    "last_temperature": cached["last_temperature"],
                    "temperature_history": cached["temperature_history"],
                },
            }

            response = requests.post(
                f"{settings.URL_COMSOL_DT_API}schedule",
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=30,
            )
            response.raise_for_status()
            print(
                f"Crate id {crate.id} - scheduling successful: {response.status_code}"
            )

        except Exception as e:
            print(f"[ERROR] Failed to schedule crate id {crate.id}: {e}")
            if ENVIRONMENT in ("development", "e2e"):
                print(f"Skipping sending recomputation failure email for crate {crate.id}.")
                return
            send_crate_failure_email(crate)
            continue


def get_temperature_lines(crate, six_hours_ago=None):
    if six_hours_ago is None:
        six_hours_ago = datetime.now().astimezone() - timedelta(hours=6)

    temp_qs = (
        CoolingUnitSpecifications.objects.filter(
            cooling_unit=crate.cooling_unit, specification_type="TEMPERATURE"
        )
        .exclude(datetime_stamp__lte=six_hours_ago)
        .order_by("datetime_stamp")
    )

    lines = []
    if not temp_qs.exists():
        return f"0\t{get_set_t(crate.id)}"

    for i, t in enumerate(temp_qs):
        seconds = (t.datetime_stamp - six_hours_ago).total_seconds()
        seconds_rounded = 0 if i == 0 else math.floor(float(seconds))
        lines.append(f"{seconds_rounded}\t{t.value}")

    return "\n".join(lines)


def send_crate_failure_email(crate):
    subject = f"Celery issue in: {settings.ENVIRONMENT}"
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = ["app@yourvcca.org"]

    crate_repr = f"TTPU : Kg {crate}" if crate else "Unknown crate"
    last_recompute = getattr(crate, "modified_dt", "N/A")

    message = (
        f"Dear Admin,\n\n"
        f"Crate Id: {crate.id}, {crate_repr} failed to recompute.\n"
        f"Last Recompute: {last_recompute}\n\n"
        "Kind regards,\n\n"
        "The Coldtivate team"
    )

    send_mail(subject, message, email_from, recipient_list)
