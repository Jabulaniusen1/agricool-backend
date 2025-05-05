from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from .user import User
from .company import Company

class Operator(models.Model):
    company = models.ForeignKey(
        Company,
        verbose_name=_("company"),
        related_name="operator_company",
        on_delete=models.CASCADE,
    )
    user = models.OneToOneField(
        User,
        verbose_name=_("user"),
        related_name="operator",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return gettext("{}").format(self.user)

    @staticmethod
    def is_operator(user):
        return Operator.objects.filter(user=user).exists()

    @staticmethod
    def is_operator_of_company(user, company):
        return Operator.objects.filter(company=company, user=user).exists()
