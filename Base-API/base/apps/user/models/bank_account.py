from django.db import models
from django.utils.translation import gettext_lazy as _

# TODO: should this be removed?
class BankAccount(models.Model):
    account_name = models.CharField(_("account_name"), max_length=64)

    account_number = models.CharField(_("account_number"), max_length=64)

    bank_name = models.CharField(_("bank_name"), max_length=64)

    class Meta:
        verbose_name_plural = "bank_accounts"

    def __str__(self):
        return "{} - {} - {}".format(
            self.account_name, self.account_number, self.bank_name,
        )
