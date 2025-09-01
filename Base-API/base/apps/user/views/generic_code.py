
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.user.serializers.generic_code import GenericCodeSerializer


class GenericCodeViewSet(GenericViewSet):
    serializer_class = GenericCodeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data, status=200)
