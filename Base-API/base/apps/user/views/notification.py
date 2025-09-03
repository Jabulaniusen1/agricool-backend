from datetime import datetime, timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.user.models import Notification
from base.apps.user.serializers.notification import NotificationSerializer


class NotificationViewSet(
    GenericViewSet,
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
):
    model = Notification
    serializer_class = NotificationSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")

        authenticated_user = self.request.user

        if user_id is None or user_id != str(authenticated_user.id):
            raise AuthenticationFailed(
                "You are not authorized to view these notifications."
            )

        week_delta = datetime.now().astimezone() - timedelta(days=7)
        return Notification.objects.filter(
            Q(user=authenticated_user) & (Q(seen=False) | Q(date__gt=week_delta))
        ).order_by("-date")

    def create(self, request, *args, **kwargs):
        user_id = self.request.user.id
        hours_delta = datetime.now().astimezone() - timedelta(hours=6)
        last_sensor_notification = (
            Notification.objects.filter(
                Q(user=user_id),
                Q(date__gt=hours_delta),
                event_type=Notification.NotificationType.SENSOR_ERROR,
            ).last()
            if user_id
            else None
        )
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            if user_id is not None and last_sensor_notification is None:
                serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    def update(self, request, *args, **kwargs):
        instance = get_object_or_404(Notification, pk=self.kwargs.get("pk", None))
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
            instance=instance,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)
