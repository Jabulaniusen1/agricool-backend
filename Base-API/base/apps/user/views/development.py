from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ViewSet

from base.celery import app


class DevelopmentViewSet(ViewSet):
    permission_classes = (AllowAny,)
    lookup_field = "id"

    @action(methods=["GET"], url_path="test", detail=False)
    def test(self, request):
        return Response({"message": "Hello World!"}, status=HTTP_200_OK)

    @action(methods=["GET"], url_path="last-sent-sms", detail=False)
    def last_sent_sms(self, request):
        phone_number = request.query_params.get("phoneNumber")

        if not phone_number:
            return Response({"sent": None}, status=HTTP_400_BAD_REQUEST)

        result = app.send_task(
            "base.apps.user.tasks.sms.get_last_sent_sms", args=[phone_number]
        )
        last_sms_sent = result.get(timeout=10)  # Wait up to 10 seconds for the result
        if not last_sms_sent:
            return Response({"sent": None}, status=HTTP_200_OK)

        return Response({"last_sms_sent": last_sms_sent}, status=HTTP_200_OK)
