from django.conf import settings
from django.core.mail import send_mail

from base.apps.storage.models import CoolingUnit, Location
from base.apps.user.models import Operator, ServiceProvider, User
from base.settings import ENVIRONMENT

# Environment constants
DEVELOPMENT_ENV = "development"

# Email constants
USER_DELETION_SUBJECT = "User deletion"
ADMIN_EMAIL = "app@yourvcca.org"

# Default values
DEFAULT_IS_ACTIVE = True
DEFAULT_DELETED = False
DEFAULT_COORDINATE = 0

# Anonymization constants
ANONYMOUS_FIRST_NAME = "User"
ANONYMOUS_LAST_NAME = "Disable"
DELETED_COMPANY_NAME_TEMPLATE = "Deleted company {}"
DELETED_COOLING_UNIT_NAME = "Deleted cooling unit"
EMPTY_STRING = ""
DEFAULT_COORDINATES = [0, 0]

# Error message templates
MAIL_ERROR_TEMPLATE = "Error sending mail: {}"


def delete_user_account(user: User) -> None:
    """
    Deletes/deactivates a user account and performs all related cascading actions.
    This is used when the user deletes their own account.
    """
    # ServiceProvider cleanup
    service_provider = ServiceProvider.objects.filter(user=user).first()
    if service_provider:
        company = service_provider.company
        remaining_count = (
            service_provider.company.service_provider_company.filter(
                user__is_active=DEFAULT_IS_ACTIVE
            ).count()
            - 1
        )

        message = (
            f"The Registered Employee with the id {user.id} of the company {company.name} has deleted their account.\n\n"
            f"Name: {user.first_name} {user.last_name}\n"
            f"Phone: {user.phone} Email: {user.email}\n\n"
            f"In this company, there are {remaining_count} Registered employees left."
        )

        # if last service provider, anonymize/delete company information
        if remaining_count == 0:
            company.name = DELETED_COMPANY_NAME_TEMPLATE.format(company.id)
            company.logo.delete()
            company.save()
            CoolingUnit.objects.filter(
                location__company_id=company.id, deleted=DEFAULT_DELETED
            ).update(name=DELETED_COOLING_UNIT_NAME, deleted=True)
            Location.objects.filter(company_id=company.id, deleted=DEFAULT_DELETED).update(
                deleted=True,
                name=None,
                state=EMPTY_STRING,
                city=EMPTY_STRING,
                street=EMPTY_STRING,
                street_number=None,
                zip_code=EMPTY_STRING,
                point=DEFAULT_COORDINATES,
            )
            Operator.objects.filter(company_id=company.id, user__is_active=DEFAULT_IS_ACTIVE).update(
                user__is_active=False,
                user__first_name=ANONYMOUS_FIRST_NAME,
                user__last_name=ANONYMOUS_LAST_NAME,
                user__phone=None,
                user__email=None,
            )

    # Operator cleanup
    operator = Operator.objects.filter(user=user).first()
    if operator:
        remaining_operators = (
            Operator.objects.filter(
                company=operator.company, user__is_active=DEFAULT_IS_ACTIVE
            ).count()
            - 1
        )

        message = (
            f"The operator with the id {user.id} of the company {operator.company.name} has deleted their account.\n\n"
            f"Name: {user.first_name} {user.last_name}\n"
            f"Phone: {user.phone}\n\n"
            f"In this company, there are {remaining_operators} Operators left."
        )

        # remove user from cooling units
        CoolingUnit.objects.filter(operators=user).update(operators=None)

    # Send email unless in development
    if ENVIRONMENT != DEVELOPMENT_ENV:
        try:
            send_mail(
                USER_DELETION_SUBJECT,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [ADMIN_EMAIL],
            )
        except Exception as e:
            print(MAIL_ERROR_TEMPLATE.format(e))

    # Finally, anonymize user
    user.is_active = False
    user.first_name = ANONYMOUS_FIRST_NAME
    user.last_name = ANONYMOUS_LAST_NAME
    user.phone = None
    user.email = None
    user.save()



def operator_delete_farmer(target_user):
    """
    Deactivate (soft delete) a farmer from an operator.
    Called by UserViewSet.operator_proxy_delete.
    """
    # remove operator from all cooling units
    for cu in CoolingUnit.objects.filter(operators=target_user):
        cu.operators.remove(target_user)

    # soft delete user
    target_user.is_active = False
    target_user.first_name = ANONYMOUS_FIRST_NAME
    target_user.last_name = ANONYMOUS_LAST_NAME
    target_user.phone = None
    target_user.email = None
    target_user.save()

