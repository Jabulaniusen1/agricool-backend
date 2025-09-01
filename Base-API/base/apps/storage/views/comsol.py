from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from base.apps.storage.models import Crate
from base.apps.storage.tasks.digital_twins import (
    send_crate_failure_email,
    update_produce_crates_dts,
)
from base.settings import ENVIRONMENT


class ComsolCallbackViewSet(ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["post"], url_path="callback")
    def callback(self, request, *args, **kwargs):
        """
        POST /storage/v1/comsol/callback
        Requires header: X-Comsol-Callback-Key: <API_KEY>
        """
        auth_header = request.headers.get("X-Comsol-Callback-Key")

        if not auth_header or auth_header != settings.COMSOL_CALLBACK_KEY:
            return Response(
                {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
            )

        print("COMSOL DT Resulting Callback received:", request.data)

        if request.data.get("error"):
            try:
                crate_id = request.data.get("crate_id")
                crate = Crate.objects.filter(id=crate_id).first()

                if ENVIRONMENT in ("development", "e2e"):
                    print(
                        f"Skipping sending recomputation failure email for crate {crate.id}."
                    )
                else:
                    send_crate_failure_email(crate)
                return Response({"status": "success"}, status=status.HTTP_200_OK)
            except Crate.DoesNotExist:
                return Response(
                    {"error": "Crate not found"}, status=status.HTTP_404_NOT_FOUND
                )

        outputs = request.data.get("outputs", {})
        crate_id = request.data.get("crate_id")
        shelf_life = outputs.get("shelf_life")
        quality_dt = outputs.get("quality_dt")
        temperature_dt = outputs.get("temperature_dt")

        if (
            crate_id is None
            or shelf_life is None
            or quality_dt is None
            or temperature_dt is None
        ):
            return Response(
                {"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST
            )

        crate = get_object_or_404(Crate, id=crate_id)

        try:
            update_produce_crates_dts(
                crate.produce_id, temperature_dt, quality_dt, shelf_life
            )
        except Crate.DoesNotExist:
            return Response(
                {"error": "Crate not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response({"status": "success"}, status=status.HTTP_200_OK)
