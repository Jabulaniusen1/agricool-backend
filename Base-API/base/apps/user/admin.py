from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import (
    ServiceProvider,
    Company,
    Farmer,
    Operator,
    InvitationUser,
    FarmerSurvey,
    FarmerSurveyCommodity,
    GenericUserCode,
    Notification,
    Country,
)


class CustomUserAdmin(UserAdmin):
    """Define admin model for custom User model with no username field."""

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "phone", "gender", "language")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    list_display = ("username", "first_name", "email", "last_name", "phone", "is_staff")
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("email",)


class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ("company", "user")
    search_fields = ("company", "user")


class CompanyAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name",)


class OperatorAdmin(admin.ModelAdmin):
    search_fields = ("user",)
    list_display = ("user", "company")


class FarmerAdmin(admin.ModelAdmin):
    search_fields = (
        "user__first_name",
        "parent_name",
    )
    list_display = ("user", "birthday", "parent_name")


class InvitationUserAdmin(admin.ModelAdmin):
    search_fields = (
        "sender",
        "phone",
    )
    list_display = ("sender", "phone", "expiration_date")


class NotificationAdmin(admin.ModelAdmin):
    search_fields = (
        "date",
        "user",
    )
    list_display = (
        "date",
        "seen",
        "user",
    )


class FarmerSurveyAdmin(admin.ModelAdmin):
    search_fields = (
        "farmer",
        "experience",
    )
    list_display = ("farmer", "experience")

    def farmer(self, obj):
        return obj.farmer.user.first_name


class FarmerSurveyCommodityAdmin(admin.ModelAdmin):
    search_fields = (
        "farmer",
        "crop",
    )
    list_display = ("farmer", "crop")

    def farmer(self, obj):
        return obj.farmer_survey.farmer.user.first_name


class GenericUserCodeAdmin(admin.ModelAdmin):
    search_fields = ("user", "type")
    list_display = ("user", "type")

    def user(self, obj):
        return obj.user.first_name


class CountryAdmin(admin.ModelAdmin):
    list_display = ("country",)
    search_fields = ("country",)

    def country(self, obj):
        return obj.country.name


admin.site.register(ServiceProvider, ServiceProviderAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(Operator, OperatorAdmin)
admin.site.register(Farmer, FarmerAdmin)
admin.site.register(get_user_model(), CustomUserAdmin)
admin.site.register(InvitationUser, InvitationUserAdmin)
admin.site.register(Notification, NotificationAdmin)

admin.site.register(FarmerSurvey, FarmerSurveyAdmin)
admin.site.register(FarmerSurveyCommodity, FarmerSurveyCommodityAdmin)
admin.site.register(GenericUserCode, GenericUserCodeAdmin)
admin.site.register(Country, CountryAdmin)
