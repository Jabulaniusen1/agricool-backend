from django.conf import settings
from django.core.mail import send_mail

from base.apps.storage.models import CoolingUnit, Location
from base.apps.user.models import Operator, ServiceProvider, User
from base.settings import ENVIRONMENT


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
                user__is_active=True
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
            company.name = f"Deleted company {company.id}"
            company.logo.delete()
            company.save()
            CoolingUnit.objects.filter(
                location__company_id=company.id, deleted=False
            ).update(name="Deleted cooling unit", deleted=True)
            Location.objects.filter(company_id=company.id, deleted=False).update(
                deleted=True,
                name=None,
                state="",
                city="",
                street="",
                street_number=None,
                zip_code="",
                point=[0, 0],
            )
            Operator.objects.filter(company_id=company.id, user__is_active=True).update(
                user__is_active=False,
                user__first_name="User",
                user__last_name="Disable",
                user__phone=None,
                user__email=None,
            )

    # Operator cleanup
    operator = Operator.objects.filter(user=user).first()
    if operator:
        remaining_operators = (
            Operator.objects.filter(
                company=operator.company, user__is_active=True
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
    if ENVIRONMENT != "development":
        try:
            send_mail(
                "User deletion",
                message,
                settings.DEFAULT_FROM_EMAIL,
                ["app@yourvcca.org"],
            )
        except Exception as e:
            print(f"Error sending mail: {e}")

    # Finally, anonymize user
    user.is_active = False
    user.first_name = "User"
    user.last_name = "Disable"
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
    target_user.first_name = "User"
    target_user.last_name = "Disable"
    target_user.phone = None
    target_user.email = None
    target_user.save()

