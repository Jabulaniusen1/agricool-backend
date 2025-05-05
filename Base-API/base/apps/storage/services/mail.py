from datetime import date

from django.conf import settings
from django.core.mail import send_mail

from base.settings import ENVIRONMENT


def invitation_mail_service(user_type, url, phone, recipient_list, date_limit):
    subject = "Invite " + user_type
    email_from = settings.DEFAULT_FROM_EMAIL
    message = f'Dear user,\n\n You have invited a new {user_type} with phone number: {phone} to join your company on Coldtivate on {date.today().strftime("%m/%d/%Y")}. In case the user has not received any invitation via SMS, please forward him/her the following invitation link: {url}. The invitation link remains valid until {date_limit}, or until a new invitation is sent.\n\nKind regards,\n\nthe Coldtivate team'

    if ENVIRONMENT == "development":
        print(f"Skipping sending email to {recipient_list} on development environment.")
        print("<<EOM")
        print(f"From:\n{email_from}")
        print(f"Subject:\n{subject}")
        print(f"Message:\n{message}")
        print("EOM")
        return

    send_mail(subject, message, email_from, recipient_list)
