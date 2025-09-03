from datetime import datetime, timedelta

from django.db.models import Exists, Q

from base.apps.operation.models import MarketsurveyPreprocessing, Movement
from base.apps.storage.models import Crate, CratePartialCheckout, Produce
from base.apps.user.models import Notification
from base.celery import app


@app.task
def time_to_pick_up_notifications():
    checkedin_crates_subquery = Crate.generate_checkedin_crates_subquery()

    produces = Produce.objects.filter(
        Q(checkin__movement__operator__company__digital_twin=True) &
        Exists(checkedin_crates_subquery)
    )
    checked_out_produces = Produce.objects.filter(
        Q(checkin__movement__operator__company__digital_twin=True) &
        ~Exists(checkedin_crates_subquery)
    )

    for produce in produces:

        if (
            Crate.objects.filter(produce=produce).first() is not None
            and Crate.objects.filter(produce=produce).first().modified_dt is not None
            and 2 > Crate.objects.filter(produce=produce).first().remaining_shelf_life
        ):
            notification_instance = Notification.objects.filter(
                specific_id=produce.id, event_type=Notification.NotificationType.TIME_TO_PICKUP
            )
            if not notification_instance:
                Notification.objects.create(
                    user=produce.checkin.movement.operator.user,
                    specific_id=produce.id,
                    event_type=Notification.NotificationType.TIME_TO_PICKUP,
                )

                user = produce.checkin.owned_by_user
                farmer = user.farmer

                if farmer:
                    if not farmer.smartphone:
                        if farmer.user.phone != None and farmer.user.phone != "":
                            """
                            MESSAGE :

                            Only 2 days left to pick up and sell your crates of NAME_OF_CROP !
                            (check in date: RANDOM_DATE,
                            cooling unit ID: NUMBER_TYPE,
                            check in ID: NUMBER_TYPE )'

                            """

                            # schedule an sms to be sent
                            app.send_task("base.apps.storage.tasks.sms.send_sms_ttpu_2_days_left", [farmer.id, produce.id])
                    else:
                        Notification.objects.create(
                            user=farmer.user,
                            specific_id=produce.id,
                            event_type=Notification.NotificationType.TIME_TO_PICKUP,
                        )

    for produce in checked_out_produces:
        notification_instance = Notification.objects.filter(specific_id=produce.id)
        if notification_instance:
            Notification.objects.filter(
                specific_id=produce.id, event_type=Notification.NotificationType.TIME_TO_PICKUP
            ).delete()


@app.task
def market_survey_checks():
    # disregard previous preprocessing entries .
    seven_days_ago = datetime.now().astimezone() - timedelta(days=7)
    fourteen_days_ago = datetime.now().astimezone() - timedelta(days=14)
    twenty_one_days_ago = datetime.now().astimezone() - timedelta(days=21)

    # 21 days account for 7 days checkout window  and leaving the market survey preprocessing  open for 14 days
    MarketsurveyPreprocessing.objects.filter(is_active=True, checkout_at__lte=twenty_one_days_ago).update(is_active=False)

    # Create preprocessing entries for checkouts completed in the last 7 days
    partial_checkouts = (
        CratePartialCheckout.objects
        .filter(
            Q(checkout__movement__initiated_for=Movement.InitiatedFor.CHECK_OUT) &
            Q(checkout__movement__date__gte=seven_days_ago) &
            Q(crate__produce__checkin__owned_by_user__farmer__isnull=False) &
            Q(crate__produce__checkin__movement__initiated_for=Movement.InitiatedFor.CHECK_IN)
        )
        .prefetch_related(
            "crate",
            "checkout__movement__operator",
            "checkout__movement",
            "crate__produce",
            "crate__produce__checkin__owned_by_user__farmer",
        )
    )

    for partial_checkout in partial_checkouts:
        # get latest partial checkout
        crate = partial_checkout.crate
        checkout = partial_checkout.checkout

        operator = checkout.movement.operator
        timestamp = checkout.movement.date
        crop = crate.produce.crop
        farmer = crate.produce.checkin.owned_by_user.farmer

        if not farmer:
            continue

        # upsert market survey preprocessing entry
        if not MarketsurveyPreprocessing.objects.filter(
            crop=crop,
            farmer=farmer,
            operator=operator,
            checkout_at=timestamp,
            checkout=checkout,
        ).exists():
            MarketsurveyPreprocessing.objects.create(
                crop=crop,
                farmer=farmer,
                operator=operator,
                checkout_at=timestamp,
                checkout=checkout,
            )


    # SEND NOTIFICATION to Farmer and operators for these checkouts

    valid_combinations = MarketsurveyPreprocessing.objects.filter(
        is_active=True
    ).distinct("crop", "farmer", "operator")

    for i in valid_combinations:
        # Avoid duplication
        if not Notification.objects.filter(
            specific_id=i.checkout.id, event_type=Notification.NotificationType.MARKET_SURVEY
        ).exists():
            if i.farmer:
                Notification.objects.create(
                    user=i.farmer.user,
                    specific_id=i.checkout.id,
                    event_type=Notification.NotificationType.MARKET_SURVEY,
                )

            if i.operator:
                Notification.objects.create(
                    user=i.operator.user,
                    specific_id=i.checkout.id,
                    event_type=Notification.NotificationType.MARKET_SURVEY,
                )


    # REMOVE ALL EXPIRED(OUTDATED) NOTIFICATIONS
    # get notifications older than 14 days ago and delete

    Notification.objects.filter(
        date__lte=fourteen_days_ago, event_type=Notification.NotificationType.MARKET_SURVEY
    ).delete()
