from datetime import datetime

import requests
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import SensorIntegration
from base.apps.storage.serializers.sensors import SensorIntegrationSerializer
from base.apps.storage.services.sensors.utils import build_integration
from base.utils.secure_errors import (
    handle_authentication_error,
    handle_external_service_error,
    handle_internal_error,
    handle_authorization_error
)


class EcozenViewSet(GenericViewSet):
    permission_classes = (permissions.AllowAny,)

    @action(detail=False, methods=["POST"], url_path="test-connection")
    def test_connection(self, request, *args, **kwargs):
        """
        Authenticates with Ecozen API and fetches Ecofrost temperature data.
        Expected request format:
        {
            "username": "user@mail.com",
            "password": "Hello123",
            "source_id": "12345"
        }
        """
        params = {
            "username": request.data.get("username"),
            "password": request.data.get("password"),
        }

        if not params["username"] or not params["password"]:
            return Response(
                {"error": "Username and password are required."}, status=400
            )

        login_url = "https://api.ecozen.ai/api/dashboard/auth/login/"

        login_request = requests.post(login_url, json=params)

        if login_request.status_code == 401:
            return Response({"error": "Unknown user"}, status=401)

        try:
            access_token = login_request.json().get("accessToken")
        except ValueError as e:
            return handle_external_service_error(e, "Ecozen API token parsing")

        if not access_token:
            return Response(
                {"error": "Authentication failed, no access token received"}, status=401
            )

        # Fetch temperature data
        room_headers = {"Authorization": f"Bearer {access_token}"}
        data_url = "https://api.ecozen.ai/api/dashboard/ecofrost/graph/"
        today = datetime.today().strftime("%Y/%m/%d")
        body = {"from": today, "to": today, "paramList": "Room_1_T, Set_T"}

        machine_id = request.data.get("source_id")
        if not machine_id:
            return Response({"error": "Machine ID is required."}, status=400)

        response = requests.post(data_url + machine_id, headers=room_headers, json=body)

        if response.status_code in [200, 201]:
            return Response({"success": "Successfully connected"}, status=200)
        elif response.status_code == 401:
            return Response({"error": "Unknown Machine ID"}, status=404)
        else:
            return Response({"error": "Unknown Error"}, status=400)


class SensorIntegrationViewSet(GenericViewSet, CreateModelMixin, DestroyModelMixin):
    model = SensorIntegration
    permission_classes = (permissions.AllowAny,)

    @action(detail=False, methods=["POST"], url_path="sources")
    def list_sources(self, request, *args, **kwargs):
        """
        Tests credentials and returns available sources.
        Expected request format:
        {
            "integration_type": "figorr",
            "username": "user@mail.com",
            "password": "Hello123"
        }
        """

        integration_type = request.data.get("integration_type")
        username = request.data.get("username")
        password = request.data.get("password")

        if not integration_type or not username or not password:
            return Response(
                {"error": "Missing required fields (integration, username, password)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        credentials = {
            "username": username,
            "password": password,
            "type": integration_type,
        }
        integration = build_integration(None, credentials)

        if not integration:
            return Response(
                {"error": "Invalid integration type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            integration.authorize()
        except Exception as e:
            return handle_authentication_error(e, "sensor integration authorization")

        try:
            raw_sources = integration.list_sources()

            serializer = SensorIntegrationSerializer(data=raw_sources, many=True)

            if serializer.is_valid():
                return Response({"sources": serializer.data}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "Invalid data format from integration"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except Exception as e:
            return handle_external_service_error(e, "sensor sources retrieval")

    def destroy(self, request, *args, **kwargs):
        user = self.request.user

        try:
            sensor = self.model.objects.get(id=kwargs.get("pk"))
        except Exception as e:
            return handle_internal_error(e, "sensor lookup")

        if not user.service_provider or not (
            sensor.cooling_unit.location.company == user.service_provider.company
        ):
            return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

        # delete the sensor passed in
        sensor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
