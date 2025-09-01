from rest_framework import serializers

from base.apps.prediction.models import Market, State

from .market import MarketSerializer


class StateSerializer(serializers.ModelSerializer):
    state_markets = serializers.SerializerMethodField()

    class Meta:
        model = State
        fields = "__all__"

    def get_state_markets(self, instance):
        items = Market.objects.filter(state=instance)
        serializer = MarketSerializer(instance=items, many=True, read_only=True)
        return serializer.data
