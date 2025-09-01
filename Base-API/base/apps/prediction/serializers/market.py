from rest_framework import serializers

from base.apps.prediction.models import Market, State


class MarketSerializer(serializers.ModelSerializer):

    class Meta:
        model = Market
        fields = "__all__"

    def create(self, validated_data):
        state = self.context["state"]
        country = self.context["country"]

        try:
            state_instance = State.objects.get(name=state)
        except:
            state_instance = State.objects.create(name=state, country=country)

        market_instance = Market.objects.create(**validated_data, state=state_instance)
        return market_instance
