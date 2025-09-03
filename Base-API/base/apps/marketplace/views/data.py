from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from rest_framework.viewsets import ViewSet

from base.apps.marketplace.payment_processor.paystack import paystack
from base.utils.decorators.cache import cache_response

# Cache timeout constants
BANKS_CACHE_TIMEOUT = 3600  # 1 hour


class MarketplaceDataViewSet(ViewSet):
    """
    A viewset for retrieving various marketplace-related data.
    
    Currently implemented endpoints:
      - GET /marketplace/data/banks/ : Retrieves a list of supported banks from Paystack.
    """
    permission_classes = (AllowAny,)

    @action(detail=False, methods=['get'], url_path='banks', url_name='banks')
    @cache_response(timeout=BANKS_CACHE_TIMEOUT)  # Cache the response for 1 hour.
    def banks(self, request):
        """
        Retrieve a list of supported banks from Paystack.
        
        GET /marketplace/data/banks/
        
        Returns:
            HTTP 200: A JSON response containing the bank list.
            HTTP 503: If an error occurred while fetching the list from Paystack.
        """
        response = paystack.misc.list_banks()
        
        # Check if the response indicates a failure.
        if response.get('status') is not True:
            return Response({'error': "Error while fetching the list of banks"}, status=HTTP_503_SERVICE_UNAVAILABLE)

        # Return the bank list extracted from the response.
        return Response({'banks': response.get('data')}, status=HTTP_200_OK)
