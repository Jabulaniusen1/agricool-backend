from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from base.apps.marketplace.payment_processor.paystack import paystack
from base.apps.user.models import Company, User


class PaystackAccount(models.Model):
    """
    Represents a Paystack account used for payment processing.
    
    This model stores bank and Paystack-specific details for both personal and business
    accounts. It includes methods to set an account as the default account and to create
    a new Paystack subaccount via the Paystack API.
    
    Note: While some business logic is embedded in this model (such as account creation
    and default account management), it is relatively thin compared to "fat models."
    If the logic grows more complex, consider moving it to a dedicated service layer.
    """
    class AccountType(models.TextChoices):
        PERSONAL = 1, _('Personal')
        BUSINESS = 2, _('Business')

    created_at = models.DateTimeField(_("created_at"), auto_now_add=True)
    created_by_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_paystack_accounts')
    owned_by_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='own_paystack_accounts')
    owned_on_behalf_of_company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='paystack_accounts', null=True, blank=True)
    is_default_account = models.BooleanField(_("is_default_account"), default=False)

    # Bank details
    account_type = models.SmallIntegerField(_("account_type"), null=False, blank=False, choices=AccountType.choices)
    bank_code = models.CharField(_("bank_code"), max_length=9, null=False, blank=False)
    country_code = models.CharField(_("country_code"), max_length=2, null=False, blank=False)
    account_number = models.CharField(_("account_number"), max_length=30)
    account_name = models.CharField(_("account_name"), max_length=100)

    # Paystack details
    paystack_subaccount_code = models.CharField(_("paystack_subaccount_code"), max_length=20)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owned_by_user', 'is_default_account'], condition=models.Q(is_default_account=True, owned_on_behalf_of_company__isnull=True), name='unique_default_user_account'),
            models.UniqueConstraint(fields=['owned_on_behalf_of_company', 'is_default_account'], condition=models.Q(is_default_account=True, owned_on_behalf_of_company__isnull=False), name='unique_default_owned_on_behalf_of_company_account'),
        ]


    @transaction.atomic
    def set_as_default_account(self):
        # Remove any prior default accounts
        PaystackAccount.objects.filter(
            owned_by_user=self.owned_by_user,
            owned_on_behalf_of_company=self.owned_on_behalf_of_company,
            is_default_account=True,
        ).update(
            is_default_account=False,
        )

        self.is_default_account = True
        self.save()


    @staticmethod
    @transaction.atomic
    def create(
        created_by_user=None,
        owned_by_user=None,
        owned_on_behalf_of_company=None,
        account_type=None,
        bank_code=None,
        country_code=None,
        account_number=None,
        account_name=None,
    ):
        # Create a Paystack account
        paystack_account = PaystackAccount.objects.create(
            created_by_user=created_by_user or owned_by_user,
            owned_on_behalf_of_company=owned_on_behalf_of_company,
            owned_by_user=owned_by_user,
            account_type=account_type,
            bank_code=bank_code,
            country_code=country_code,
            account_number=account_number,
            account_name=account_name,
            paystack_subaccount_code="", # Will be set after the paystack subaccount is created
            is_default_account=False,
        )

        # Create a Paystack subaccount with 0 percent charge
        paystack_response = paystack.subaccount.create(
            business_name=f"PaystackAccount #{paystack_account.id} - Company #{owned_on_behalf_of_company.id}" if owned_on_behalf_of_company else f"PaystackAccount #{paystack_account.id} - User #{owned_by_user.id}",
            settlement_bank=paystack_account.bank_code,
            account_number=paystack_account.account_number,
            percentage_charge=0,
        )

        if paystack_response['status'] is False:
            paystack_account.delete()
            reason = paystack_response['message'] or "Unknown reason"
            raise Exception(f"Failed to create Paystack subaccount. Reason: {reason}")

        # Update the paystack_subaccount_code
        paystack_account.paystack_subaccount_code = paystack_response['data']['subaccount_code']
        paystack_account.set_as_default_account() # This will also save the account

        return paystack_account


    @staticmethod
    def company_has_default_account(owned_on_behalf_of_company_id):
        """
        Check if a default Paystack account exists for a specific company.

        :param owned_on_behalf_of_company_id: The ID of the company to check.
        :return: Boolean indicating if a default account exists for the company.
        """
        return PaystackAccount.objects.filter(owned_on_behalf_of_company_id=owned_on_behalf_of_company_id, is_default_account=True).exists()


    @staticmethod
    def user_has_default_account(owned_by_user_id):
        """
        Check if a default Paystack account exists for a specific company.

        :param owned_by_user_id: The ID of the company to check.
        :return: Boolean indicating if a default account exists for the company.
        """
        return PaystackAccount.objects.filter(owned_by_user=owned_by_user_id, is_default_account=True, owned_on_behalf_of_company__isnull=True).exists()


    @staticmethod
    def get_company_default_account(owned_on_behalf_of_company_id):
        """
        Get the default Paystack account for a company.

        :param owned_on_behalf_of_company_id: The ID of the company.
        :return: The default Paystack account for the company.
        """
        return PaystackAccount.objects.filter(owned_on_behalf_of_company=owned_on_behalf_of_company_id, is_default_account=True).first()


    @staticmethod
    def get_user_default_account(owned_by_user_id):
        """
        Get the default Paystack account for a user.

        :param owned_by_user_id: The ID of the company.
        :return: The default Paystack account for the user.
        """
        return PaystackAccount.objects.filter(owned_by_user=owned_by_user_id, is_default_account=True, owned_on_behalf_of_company__isnull=True).first()
