from datetime import date

from django.conf import settings
from django.core.mail import send_mail

from base.settings import ENVIRONMENT

# Environment constants
DEVELOPMENT_ENV = "development"

# Email template constants
INVITE_SUBJECT_TEMPLATE = "Invite {}"
EMAIL_SEPARATOR = "<<EOM"
FROM_LABEL = "From:"
SUBJECT_LABEL = "Subject:"
MESSAGE_LABEL = "Message:"
END_OF_MESSAGE = "EOM"

# Development message template
DEV_SKIP_MESSAGE_TEMPLATE = "Skipping sending email to {} on development environment."


def invitation_mail_service(user_type, url, phone, recipient_list, date_limit):
    subject = INVITE_SUBJECT_TEMPLATE.format(user_type)
    email_from = settings.DEFAULT_FROM_EMAIL
    message = f'Dear user,\n\n You have invited a new {user_type} with phone number: {phone} to join your company on Coldtivate on {date.today().strftime("%m/%d/%Y")}. In case the user has not received any invitation via SMS, please forward him/her the following invitation link: {url}. The invitation link remains valid until {date_limit}, or until a new invitation is sent.\n\nKind regards,\n\nthe Coldtivate team'

    if ENVIRONMENT == DEVELOPMENT_ENV:
        print(DEV_SKIP_MESSAGE_TEMPLATE.format(recipient_list))
        print(EMAIL_SEPARATOR)
        print(f"{FROM_LABEL}\n{email_from}")
        print(f"{SUBJECT_LABEL}\n{subject}")
        print(f"{MESSAGE_LABEL}\n{message}")
        print(END_OF_MESSAGE)
        return

    send_mail(subject, message, email_from, recipient_list)
