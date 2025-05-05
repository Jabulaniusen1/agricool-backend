from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from .company import Company
from .user import User

class ServiceProvider(models.Model):
    company = models.ForeignKey(
        Company,
        verbose_name=_("company"),
        related_name="service_provider_company",
        on_delete=models.CASCADE,
    )
    user = models.OneToOneField(
        User,
        verbose_name=_("user"),
        related_name="service_provider",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return gettext("{}").format(self.user)

    @staticmethod
    def is_employee(user):
        return ServiceProvider.objects.filter(user=user).exists()

    @staticmethod
    def is_employee_of_company(user, company):
        return ServiceProvider.objects.filter(company=company, user=user).exists()
