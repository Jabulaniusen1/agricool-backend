from django.db import models
from django.utils.translation import gettext_lazy as _

# Field length constants
ACCOUNT_NAME_MAX_LENGTH = 64
ACCOUNT_NUMBER_MAX_LENGTH = 64
BANK_NAME_MAX_LENGTH = 64

# TODO: should this be removed?
class BankAccount(models.Model):
    account_name = models.CharField(_("account_name"), max_length=ACCOUNT_NAME_MAX_LENGTH)

    account_number = models.CharField(_("account_number"), max_length=ACCOUNT_NUMBER_MAX_LENGTH)

    bank_name = models.CharField(_("bank_name"), max_length=BANK_NAME_MAX_LENGTH)

    class Meta:
        verbose_name_plural = "bank_accounts"

    def __str__(self):
        return "{} - {} - {}".format(
            self.account_name, self.account_number, self.bank_name,
        )
