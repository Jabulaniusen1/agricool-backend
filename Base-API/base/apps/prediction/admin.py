from django.contrib import admin

from .models import State, Market, MLPredictionData, MLMarketDataIndia


class StateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
    )


class MarketAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "state",
    )


class MLPredictionDataAdmin(admin.ModelAdmin):
    list_display = ("market", "crop")
    readonly_fields = ("fetched_at",)


class MLMarketDataIndiaAdmin(admin.ModelAdmin):
    list_display = ("date", "state_label", "commodity_label")
    readonly_fields = ("date",)


admin.site.register(State, StateAdmin)
admin.site.register(Market, MarketAdmin)
admin.site.register(MLPredictionData, MLPredictionDataAdmin)
admin.site.register(MLMarketDataIndia, MLMarketDataIndiaAdmin)
