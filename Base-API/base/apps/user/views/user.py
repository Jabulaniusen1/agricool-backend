from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.user.models import Farmer, Operator, User
from base.apps.user.serializers.user import UserSerializer
from base.apps.user.services.user import delete_user_account, operator_delete_farmer


class UserViewSet(GenericViewSet):
    """
    ViewSet for CRUD operations on User objects.
    """

    model = User
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return self.model.objects.all()

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = self.serializer_class(qs, many=True, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        instance = get_object_or_404(User, pk=self.kwargs.get("pk"))
        serializer = self.serializer_class(
            instance=instance,
            data=request.data,
            context={"request": request},
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    def retrieve(self, request, pk=None, *args, **kwargs):
        instance = get_object_or_404(User, pk=pk)
        data = self.serializer_class(instance, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        """
        Allows a user to delete (deactivate) their own account.
        """
        user_to_delete = get_object_or_404(User, pk=self.kwargs.get("pk"))

        if request.user.id != user_to_delete.id:
            return Response(
                {"error": "You can only delete your own account"},
                status=status.HTTP_403_FORBIDDEN,
            )

        delete_user_account(user_to_delete)
        return Response(
            {"success": "Successfully deleted user"}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["delete"], url_path="operator-proxy-delete")
    def operator_proxy_delete(self, request, pk=None, **kwargs):
        """
        Endpoint allowing an authenticated operator to deactivate a farmer account.
        Business logic is delegated to a service (operator_delete_farmer).
        """
        operator = Operator.objects.filter(user=request.user).first()
        if not operator:
            return Response(
                {"error": "Only users with the operator role can perform this action"},
                status=status.HTTP_403_FORBIDDEN,
            )

        target_user = get_object_or_404(User, id=pk)
        farmer = Farmer.objects.filter(user=target_user).first()
        if not farmer:
            return Response(
                {"error": "Target user is not a farmer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # same company check
        if not farmer.companies.filter(id=operator.company_id).exists():
            return Response(
                {"error": "The farmer does not belong to your company"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # smartphone user check
        if farmer.user_code is not None or farmer.smartphone:
            return Response(
                {"error": "Cannot delete smartphone users"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        operator_delete_farmer(target_user)
        return Response(
            {"success": "User deleted by operator"},
            status=status.HTTP_200_OK,
        )
