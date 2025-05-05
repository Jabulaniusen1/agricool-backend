from django.contrib import admin
from .models import Checkin, Movement, Checkout, MarketSurvey


class MovementAdmin(admin.ModelAdmin):
    list_display = ("date",)


class CheckinAdmin(admin.ModelAdmin):
    list_display = ("movement",)


class CheckoutAdmin(admin.ModelAdmin):
    list_display = ("movement",)


class MarketSurveyAdmin(admin.ModelAdmin):
    list_display = (
        "checkout",
        "selling_place",
        "price",
    )


admin.site.register(Movement, MovementAdmin)
admin.site.register(Checkin, CheckinAdmin)
admin.site.register(Checkout, CheckoutAdmin)
admin.site.register(MarketSurvey, MarketSurveyAdmin)
