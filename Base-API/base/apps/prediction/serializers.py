from rest_framework import serializers
from .models import State, Market, StateNg


class StateSerializer(serializers.ModelSerializer):
    state_markets = serializers.SerializerMethodField()

    class Meta:
        model = State
        fields = "__all__"

    def get_state_markets(self, instance):
        items = Market.objects.filter(state=instance)
        serializer = MarketSerializer(instance=items, many=True, read_only=True)
        return serializer.data


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


class StateNgSerializer(serializers.ModelSerializer):

    class Meta:
        model = StateNg
        fields = "__all__"
