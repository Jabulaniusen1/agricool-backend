from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail

from base.apps.storage.models import Crate
from base.apps.storage.services.comsol import (compute_dt_crate,
                                               comsol_parse_output_crate)
from base.celery import app


@app.task
def recompute_digital_twin():
    # Email Sending constants
    subject = "Celery issue in: " + settings.ENVIRONMENT
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = ["app@yourvcca.org"] # TODO: Removed abc's dev email, maybe this should be a setting

    # get all crates, where the digital twin is computed and that are not checked out
    crates = Crate.objects.filter(
        cooling_unit__location__company__digital_twin=True,
        weight__gt=0,
        runDT=True,
        produce__crop__digital_twin_identifier__isnull=False,
    ).distinct("produce")

    # we want to recompute shelf life every six hours, with a 30min time margin of error
    five_hours_ago = datetime.now().astimezone() - timedelta(hours=5, minutes=30)

    for c in crates.iterator():
        print(f"recompute_digital_twin task: considering computing crate id: {c.id}")

        # Bypass the ones that are already computed within a 5 hours time margin
        if c.modified_dt != None and (c.modified_dt.astimezone() > five_hours_ago):
            print(f"recompute_digital_twin task: crate id: {c.id} {c} - already computed within 5 hours margin, skipping")
            continue

        try:
            comsol_context_tmp = compute_dt_crate(c.id)

            if comsol_context_tmp == None:
                raise Exception("comsol context directoy is set to None")

            comsol_parse_output_crate(c.id, comsol_context_tmp)

        # Capture exception and send over an email
        except Exception as e:
            print(f"crate id: {c.id} {c} - exception {e}, sending email")
            message = f"Dear Admin,\n\n Crate Id: {c.id}, TTPU : Kg {c} failed to recompute because of exception {e}. Last Recompute: {c.modified_dt} \n\nKind regards,\n\nthe Coldtivate team"
            send_mail(subject, message, email_from, recipient_list)
            continue
