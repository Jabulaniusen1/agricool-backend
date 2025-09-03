from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.user.models import Farmer, Operator
from base.apps.user.serializers.farmer import FarmerSerializer, FarmerWithPublicUserSerializer

# Request parameter constants
USER_ID_PARAM = "user_id"
OPERATOR_PARAM = "operator"
USER_CODE_PARAM = "user_code"
CREATE_USER_PARAM = "create_user"

# Default values
DEFAULT_IS_ACTIVE = True

# Error messages
ERROR_MISSING_USER_CODE = "Missing user_code param"
ERROR_NOT_OPERATOR = "Requesting user is not an operator"
ERROR_FARMER_NOT_FOUND = "Farmer not found"


class FarmerViewSet(
    GenericViewSet, ListModelMixin, UpdateModelMixin, RetrieveModelMixin
):
    model = Farmer
    serializer_class = FarmerSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        if self.request.query_params.get(USER_ID_PARAM):
            return self.model.objects.filter(
                Q(user__id=self.request.query_params.get(USER_ID_PARAM))
            )

        if self.request.query_params.get(OPERATOR_PARAM):
            operator_user_id = self.request.query_params.get(OPERATOR_PARAM)

            return self.model.objects.filter(
                Q(created_by__company__operator_company__user_id=operator_user_id)
                | Q(companies__operator_company__user_id=operator_user_id),
                user__is_active=DEFAULT_IS_ACTIVE,
            ).distinct()

        return self.model.objects.all()

    def create(self, request, *args, **kwargs):
        if not request.data[CREATE_USER_PARAM] and (
            not request.user or not request.user.is_authenticated
        ):
            raise PermissionDenied()
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied()

        pk = self.kwargs.get("pk", None)
        instance = get_object_or_404(Farmer, id=pk)
        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
            instance=instance,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=["GET"], url_path="by-code")
    def get_farmer_by_code(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied()

        user_code = request.query_params.get(USER_CODE_PARAM)
        if not user_code:
            return Response({"error": ERROR_MISSING_USER_CODE}, status=status.HTTP_400_BAD_REQUEST)

        try:
            Operator.objects.get(user=request.user)
        except Operator.DoesNotExist:
            return Response({"error": ERROR_NOT_OPERATOR}, status=status.HTTP_403_FORBIDDEN)

        try:
            farmer = Farmer.objects.get(user_code=user_code, user__is_active=DEFAULT_IS_ACTIVE)
        except Farmer.DoesNotExist:
            return Response({"error": ERROR_FARMER_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        serializer = FarmerWithPublicUserSerializer(
            farmer, context=self.get_serializer_context()
        )
        return Response(serializer.data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return super().get_serializer(*args, **kwargs)
