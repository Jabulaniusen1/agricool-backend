from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from base.apps.user.models import Company, User


class CompanyDeliveryContact(models.Model):
    created_by_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_company_delivery_contacts')
    created_at = models.DateTimeField(_("created_at"), auto_now_add=True)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, null=False, blank=True, related_name='delivery_contacts')

    delivery_company_name = models.CharField(_("delivery_company_name"), max_length=255, null=False)
    contact_name = models.CharField(_("contact_name"), max_length=255, null=False)
    phone = PhoneNumberField(_("phone"), null=False)

    def __str__(self):
        return f"CompanyDeliveryContact {self.id}# {self.contact_name}"
