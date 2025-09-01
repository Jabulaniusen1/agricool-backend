
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from base.apps.storage.apps import ANDROID_VERSION_CODE, IOS_VERSION_CODE


class MobileAppMinimumVersionCodesViewSet(ViewSet):
    """
    ViewSet to get the latest version code per platform.

    * Any authenticated user is able to access this view.
    """

    permission_classes = (permissions.AllowAny,)

    @action(methods=["GET"], url_path="android", detail=False)
    def android(self, request):
        return Response(ANDROID_VERSION_CODE)

    @action(methods=["GET"], url_path="ios", detail=False)
    def ios(self, request):
        return Response(IOS_VERSION_CODE)
