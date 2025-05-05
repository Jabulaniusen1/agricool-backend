from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, FloatField, OuterRef, Q, Subquery
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED,
                                   HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN)
from rest_framework.viewsets import ViewSet

from base.apps.marketplace.models import (CompanyDeliveryContact,
                                          MarketListedCrate, Order,
                                          OrderCrateItem, OrderPickupDetails)
from base.apps.marketplace.payment_processor.paystack.order_payment import (
    get_checkout_url_for_order, set_the_order_as_pending_payment)
from base.apps.marketplace.serializers.buyer_requests import (
    BuyerAddItemToCartRequestSerializer,
    BuyerApplyOrClearCouponRequestSerializer,
    BuyerMarketListingQueryParamsSerializer,
    BuyerSetPickupDetailsRequestSerializer)
from base.apps.marketplace.serializers.buyer_responses import (
    BuyerCartSerializer, BuyerOrderSerializer)
from base.apps.marketplace.serializers.common import (
    CompanyDeliveryContactSerializer, MarketListedCrateSerializer)
from base.apps.marketplace.views.utils import (get_cart, get_cart_prefetched,
                                               get_or_create_cart)
from base.apps.storage.models import Crate
from base.utils.serializers.paginator import PaginationSerializer

from .company import get_company


# -----------------------------------------------------------------------------
# Marketplace listings related views
# -----------------------------------------------------------------------------
class BuyerAvailableMarketListingViewSet(ViewSet):
    """
    ViewSet for listing available marketplace listings for buyers.
    
    This ViewSet retrieves a paginated list of active market listings based on the
    user's location, cooling unit filters, and sorting preferences.
    """
    model = MarketListedCrate
    serializer_class = MarketListedCrateSerializer
    permission_classes = (AllowAny,)
    permissions_get = []

    def get_queryset(self, data, owned_by_user_id=None, owned_on_behalf_of_company_id=None):
        """
        Return a queryset of MarketListedCrate objects based on filtering and sorting criteria.
        
        Filtering criteria:
         - Only active listings (not delisted) with available weight (cmp_available_weight_in_kg > 0).
         - Annotation of the distance between the crate's cooling unit and the user location.
         - Filter by cooling unit IDs, if provided.
         - Exclude listings belonging to the user's own cart if applicable.
         - Filter by maximum distance, if provided.
         
        Sorting:
         - By ascending price (price-asc) or descending price (price-desc) if specified.
         - Otherwise, by distance.
         
        Args:
            data (dict): Cleaned data from the query parameters serializer.
            owned_by_user_id (int, optional): The ID of the user owning the cart; used for exclusion.
            owned_on_behalf_of_company_id (int, optional): The company ID from the user's cart (if any).
        
        Returns:
            QuerySet: The filtered and sorted list of market listed crates.
        """
        # Extract user's latitude and longitude from the data
        lat, lng = data['location']
        user_location = Point(lng, lat, srid=4326)

        # Filter active market listed crates with available weight; annotate with distance in km.
        market_listed_crates = MarketListedCrate.objects.filter(
            delisted_at__isnull=True,
            cmp_available_weight_in_kg__gt=0
        ).annotate(
            distance=Cast(
                Distance('crate__cooling_unit__location__point', user_location),
                FloatField()
            ) / 1000.0
        )

        # Filter by specified cooling unit IDs if provided.
        if data['filter_by_cooling_units_ids']:
            market_listed_crates = market_listed_crates.filter(
                crate__cooling_unit__id__in=data['filter_by_cooling_units_ids']
            )

        # Exclude listings that belong to the user's own cart.
        if owned_by_user_id:
            market_listed_crates = market_listed_crates.exclude(
                Q(crate__produce__checkin__owned_by_user_id=owned_by_user_id) &
                (Q(crate__produce__checkin__owned_on_behalf_of_company_id=owned_on_behalf_of_company_id)
                 if owned_on_behalf_of_company_id else
                 Q(crate__produce__checkin__owned_on_behalf_of_company_id__isnull=True))
            )

        # Apply distance filter if provided.
        if data['filter_by_max_distance_in_km']:
            market_listed_crates = market_listed_crates.filter(
                distance__lte=data['filter_by_max_distance_in_km']
            )

        # Sort the queryset based on price or distance.
        if data['sort_by'] == 'price-asc':
            market_listed_crates = market_listed_crates.order_by('prices__produce_price_per_kg')
        elif data['sort_by'] == 'price-desc':
            market_listed_crates = market_listed_crates.order_by('-prices__produce_price_per_kg')
        else:
            market_listed_crates = market_listed_crates.order_by('distance')

        return market_listed_crates

    def list(self, request):
        """
        GET /marketplace/buyer/available-listings/
        
        Retrieves a paginated list of marketplace listings based on query parameters.
        The view uses the BuyerMarketListingQueryParamsSerializer to validate input and
        applies filtering and sorting rules, then paginates the results.
        
        Returns:
            Response: A JSON response containing pagination metadata and the serialized list of market listings.
        """
        input_serializer = BuyerMarketListingQueryParamsSerializer(data=request.query_params)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        # Retrieve the user's active cart (if authenticated) to potentially exclude their own listings.
        cart = get_cart(request.user) if request.user.is_authenticated else None

        queryset = self.get_queryset(
            data,
            owned_by_user_id=cart.created_by_user.id if cart else None,
            owned_on_behalf_of_company_id=cart.owned_on_behalf_of_company_id if cart else None
        )

        # Paginate the queryset using the provided items per page.
        paginator = Paginator(queryset, data['items_per_page'])
        page = paginator.get_page(data['page'])

        # Serialize the paginated results.
        response_data = {
            'pagination': PaginationSerializer(page).data,
            'nodes': MarketListedCrateSerializer(page, many=True).data
        }
        return Response(response_data, status=HTTP_200_OK)



# -----------------------------------------------------------------------------
# Cart related views
# -----------------------------------------------------------------------------

class BuyerCartViewSet(ViewSet):
    """
    API viewset for managing the buyer's cart and related actions (except for item management).

    Endpoints include:
      - GET /marketplace/buyer/cart/ : Retrieve the current user's active cart.
      - POST /marketplace/buyer/cart/ : Create or recompute the cart.
      - POST /marketplace/buyer/cart/set-pickup-details/ : Set pickup details for the cart.
      - GET /marketplace/buyer/cart/delivery-contacts/ : Retrieve delivery contacts related to the cart.
      - POST /marketplace/buyer/cart/apply-coupon/ : Apply a coupon to the cart.
      - POST /marketplace/buyer/cart/clear-coupon/ : Remove an applied coupon from the cart.
      - POST /marketplace/buyer/cart/toggle-ownership/ : Toggle cart ownership.
      - POST /marketplace/buyer/cart/checkout-with-paystack/ : Initialize checkout with Paystack.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = BuyerCartSerializer

    def list(self, request, *args, **kwargs):
        """
        GET /marketplace/buyer/cart/
        
        Returns the active cart of the authenticated buyer. If no cart exists,
        a message indicating that the cart is empty is returned.
        """
        user = request.user
        cart = get_cart_prefetched(user)
        if not cart:
            return Response({"message": "Cart is empty."}, status=HTTP_200_OK)
        serializer = self.serializer_class(cart)
        return Response({"cart": serializer.data}, status=HTTP_200_OK)

    def create(self, request):
        """
        POST /marketplace/buyer/cart/
        
        Retrieves or creates the active cart for the buyer and computes its fields.
        Returns a 201 response if a new cart was created, or a 200 response if an existing
        cart was recomputed.
        """
        user = request.user
        cart, created = get_or_create_cart(user)
        cart.compute(save=True, compute_dependencies=True)

        if created:
            return Response({"message": "Cart created."}, status=HTTP_201_CREATED)

        serializer = self.serializer_class(cart)
        return Response({"message": "Cart recomputed.", "cart": serializer.data}, status=HTTP_200_OK)

    @action(methods=['POST'], url_path='set-pickup-details', detail=False)
    @transaction.atomic
    def set_pickup_details(self, request):
        """
        POST /marketplace/buyer/cart/set-pickup-details/
        
        Sets the pickup details for the buyer's cart.
        This endpoint validates the provided pickup details, clears existing pickup 
        details, and creates new ones for each cooling unit in the cart.
        """
        user = request.user
        serializer = BuyerSetPickupDetailsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = get_cart_prefetched(user)
        if not cart:
            return Response({"message": "Cart is empty."}, status=HTTP_200_OK)

        # Build a dictionary mapping cooling_unit_id to the pickup method
        pickup_details = {}
        for pickup_detail in serializer.validated_data['pickup_details']:
            pickup_details[pickup_detail['cooling_unit_id']] = pickup_detail['pickup_method']


        # Clear existing pickup details for the current cart.
        OrderPickupDetails.objects.filter(order=cart).delete()

        # Iterate over each cooling unit in the cart and create a new pickup detail.
        for cooling_unit_id in cart.get_cooling_unit_ids():
            pickup_method = pickup_details.get(
                cooling_unit_id, OrderPickupDetails.PickUpMethod.PICK_UP_SAME_DAY
            )
            OrderPickupDetails.objects.create(
                order=cart,
                cooling_unit_id=cooling_unit_id,
                pickup_method=pickup_method,
            )

        serializer = self.serializer_class(cart)
        return Response({"message": "Pickup details were saved.", "cart": serializer.data}, status=HTTP_200_OK)

    @action(methods=['GET'], url_path='delivery-contacts', detail=False)
    def delivery_contacts(self, request):
        """
        GET /marketplace/buyer/cart/delivery-contacts/
        
        Retrieves the delivery contacts for the buyer's cart.
        This endpoint uses a subquery to extract company IDs related to the order's items
        and returns the corresponding CompanyDeliveryContact records.
        """
        user = request.user
        cart = get_cart(user)
        if not cart:
            return Response({"message": "Cart is empty."}, status=HTTP_200_OK)

        companies_subquery = (
            OrderCrateItem.objects.filter(order_id=cart.id)
            .annotate(
                cooling_unit_id=F('market_listed_crate__crate__cooling_unit_id'),
                company_id=F('market_listed_crate__crate__cooling_unit__location__company_id'),
            )
            .filter(company_id=OuterRef('company_id'))
            .values('cooling_unit_id', 'company_id')
        )

        company_delivery_contacts = (
            CompanyDeliveryContact.objects
            .annotate(
                cooling_unit_id=Subquery(companies_subquery.values('cooling_unit_id'))
            )
            .filter(
                company_id__in=Subquery(companies_subquery.values('company_id'))
            )
        )

        serializer = CompanyDeliveryContactSerializer(company_delivery_contacts, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    @action(methods=['POST'], url_path='apply-coupon', detail=False)
    @transaction.atomic
    def apply_coupon(self, request):
        """
        POST /marketplace/buyer/cart/apply-coupon/
        
        Applies a coupon to the buyer's cart.
        Validates the coupon using BuyerApplyOrClearCouponRequestSerializer and applies it to the cart.
        """
        user = request.user
        serializer = BuyerApplyOrClearCouponRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = get_cart(user)
        if not cart:
            return Response({"message": "Cart is empty."}, status=HTTP_200_OK)

        cart.apply_coupon_code(serializer.validated_data['coupon_code'])
        cart_serializer = self.serializer_class(cart)
        return Response({"message": "Coupon applied.", "cart": cart_serializer.data}, status=HTTP_200_OK)

    @action(methods=['POST'], url_path='clear-coupon', detail=False)
    @transaction.atomic
    def clear_coupon(self, request):
        """
        POST /marketplace/buyer/cart/clear-coupon/
        
        Clears the currently applied coupon from the buyer's cart.
        Validates the input using BuyerApplyOrClearCouponRequestSerializer and clears the coupon.
        """
        user = request.user
        serializer = BuyerApplyOrClearCouponRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = get_cart(user)
        if not cart:
            return Response({"message": "Cart is empty."}, status=HTTP_200_OK)

        cart.clear_coupon_code(serializer.validated_data['coupon_code'])
        cart_serializer = self.serializer_class(cart)
        return Response({"message": "Coupon cleared.", "cart": cart_serializer.data}, status=HTTP_200_OK)

    @action(methods=['POST'], url_path='toggle-ownership', detail=False)
    @transaction.atomic
    def toggle_ownership(self, request):
        """
        POST /marketplace/buyer/cart/toggle-ownership/
        
        Toggles the ownership of the buyer's cart.
        If the cart is not currently associated with a company, it attaches the user's company.
        Otherwise, it detaches the company association.
        """
        user = request.user
        cart, created = get_or_create_cart(user)

        if cart.owned_on_behalf_of_company_id is None:
            try:
                company = get_company(request)
            except:
                return Response({"error": "Access denied."}, status=HTTP_403_FORBIDDEN)
            cart.owned_on_behalf_of_company_id = company.id
            cart.save()
        else:
            cart.owned_on_behalf_of_company_id = None
            cart.save()

        cart = get_cart_prefetched(user)
        serializer = self.serializer_class(cart)
        status_code = HTTP_201_CREATED if created else HTTP_200_OK
        return Response({"message": "Cart ownership toggled.", "cart": serializer.data}, status=status_code)

    @action(methods=['POST'], url_path='checkout-with-paystack', detail=False)
    @transaction.atomic
    def checkout_with_paystack(self, request):
        """
        POST /marketplace/buyer/cart/checkout-with-paystack/
        
        Initiates the checkout process via Paystack.
        Validates that the cart is in a valid state for payment, creates or updates the Paystack split group,
        then initializes a Paystack transaction, returning an authorization URL.
        """
        user = request.user
        cart = get_cart(user)
        if not cart:
            return Response({"error": "No active cart found."}, status=HTTP_400_BAD_REQUEST)

        try:
            cart.check_if_valid_to_proceed_to_payment()
        except Exception as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

        try:
            # Set the order as pending payment by configuring the split group
            set_the_order_as_pending_payment(cart)
            # Initialize the transaction and get the checkout authorization URL from Paystack.
            authorization_url = get_checkout_url_for_order(cart)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

        return Response({
            "order_id": cart.id,
            "authorization_url": authorization_url,
        }, status=HTTP_200_OK)

class BuyerCartItemsViewSet(ViewSet):
    """
    API viewset for managing buyer cart items (adding and removing produce).
    
    Endpoints:
      - POST   /marketplace/buyer/cart/items/ : Add produce to the buyer's cart.
      - DELETE /marketplace/buyer/cart/items/:crate_id/ : Remove produce from the buyer's cart.
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'crate_id'
    serializer_class = BuyerCartSerializer

    @transaction.atomic
    def create(self, request):
        """
        POST /marketplace/buyer/cart/items/
        
        Adds produce to the authenticated buyer's cart. The endpoint:
         - Validates the input data using BuyerAddItemToCartRequestSerializer.
         - Retrieves the corresponding Crate and active cart.
         - Fetches the associated MarketListedCrate record.
         - Calculates a new ordered produce weight based on the update strategy (replace/increase/decrease),
           ensuring that the ordered weight does not exceed the available weight and is non-negative.
         - Creates or updates the corresponding OrderCrateItem.
         - Recomputes the entire cart and returns the updated cart data.
        """
        user = request.user
        # Validate incoming data
        input_serializer = BuyerAddItemToCartRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        
        # Extract validated values
        crate_id = input_serializer.validated_data['crate_id']
        update_strategy = input_serializer.validated_data['update_strategy']
        req_ordered_produce_weight = input_serializer.validated_data['ordered_produce_weight']

        # Retrieve the relevant crate and market listing
        crate = get_object_or_404(Crate, id=crate_id)
        cart, created = get_or_create_cart(user)
        market_listed_crate = get_object_or_404(MarketListedCrate, crate=crate, delisted_at__isnull=True)

        # Get existing order item if available
        existing_item = OrderCrateItem.objects.filter(order=cart, market_listed_crate=market_listed_crate).first()

        # Update the market listing computation (available weight, etc.)
        market_listed_crate.compute(save=True)

        # Calculate new ordered weight based on the update strategy
        if existing_item:
            if update_strategy == 'increase':
                new_weight = existing_item.ordered_produce_weight + req_ordered_produce_weight
            elif update_strategy == 'decrease':
                new_weight = existing_item.ordered_produce_weight - req_ordered_produce_weight
            else:  # 'replace'
                new_weight = req_ordered_produce_weight
        else:
            new_weight = req_ordered_produce_weight

        # Ensure the new weight is within bounds: at most the available weight and no less than 0
        ordered_produce_weight = max(0, min(market_listed_crate.cmp_available_weight_in_kg, new_weight))

        # Create or update the order item in the cart
        item, created_item = OrderCrateItem.objects.update_or_create(
            order=cart,
            market_listed_crate=market_listed_crate,
            defaults={'ordered_produce_weight': ordered_produce_weight}
        )

        # Re-fetch and compute the entire cart
        cart = get_cart_prefetched(user)
        cart.compute(save=True, compute_dependencies=True)

        # Serialize the updated cart data and determine appropriate status code
        cart_serializer = self.serializer_class(cart)
        status_code = HTTP_201_CREATED if created_item else HTTP_200_OK
        return Response({"cart": cart_serializer.data}, status=status_code)

    @transaction.atomic
    def destroy(self, request, crate_id=None):
        """
        DELETE /marketplace/buyer/cart/items/:crate_id/
        
        Removes produce (i.e., an order item) from the authenticated buyer's cart.
        After deletion, recomputes the cart and returns the updated cart data.
        """
        user = request.user
        cart = get_cart(user)
        if not cart:
            return Response({"error": "No active cart found"}, status=HTTP_400_BAD_REQUEST)

        # Retrieve the specific order item based on the crate ID
        item = get_object_or_404(OrderCrateItem, market_listed_crate__crate_id=crate_id, order=cart)
        item.delete()  # Remove the order item

        # Re-fetch and compute the updated cart
        cart = get_cart_prefetched(user)
        cart.compute(save=True, compute_dependencies=True)

        cart_serializer = self.serializer_class(cart)
        return Response({"cart": cart_serializer.data}, status=HTTP_200_OK)


# -----------------------------------------------------------------------------
# Orders related views
# -----------------------------------------------------------------------------

class BuyerOrdersViewSet(ViewSet):
    """
    API viewset for buyers to manage and view their orders.

    Endpoints:
      - GET /marketplace/buyer/orders/ : List all orders for the authenticated buyer.
      - GET /marketplace/buyer/orders/<order_id>/ : Retrieve a specific order.
      - GET /marketplace/buyer/orders/<order_id>/delivery-contacts/ : Get delivery contacts for the order.
      - POST /marketplace/buyer/orders/<order_id>/pay-with-paystack/ : Initiate payment with Paystack.
      - POST /marketplace/buyer/orders/<order_id>/cancel/ : Cancel a pending order.
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_id'
    serializer_class = BuyerOrderSerializer

    # Orders that can be listed or retrieved
    listable_statuses = [
        Order.Status.PAYMENT_PENDING,
        Order.Status.PAID,
        Order.Status.PAYMENT_EXPIRED,
        Order.Status.CANCELLED,
    ]

    def list(self, request):
        """
        GET /marketplace/buyer/orders/
        
        Lists all orders for the authenticated buyer with statuses in listable_statuses.
        """
        user = request.user
        orders = Order.objects.filter(created_by_user=user, status__in=self.listable_statuses)
        serializer = self.serializer_class(orders, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    def retrieve(self, request, order_id=None):
        """
        GET /marketplace/buyer/orders/<order_id>/
        
        Retrieves a specific order for the authenticated buyer.
        """
        user = request.user
        order = get_object_or_404(Order, id=order_id, created_by_user=user, status__in=self.listable_statuses)
        serializer = self.serializer_class(order)
        return Response(serializer.data, status=HTTP_200_OK)

    @action(methods=['GET'], url_path='delivery-contacts', detail=True)
    def delivery_contacts(self, request, order_id=None):
        """
        GET /marketplace/buyer/orders/<order_id>/delivery-contacts/
        
        Retrieves the delivery contacts for an order.
        Uses a subquery to extract company IDs from the order's related items and
        returns the corresponding CompanyDeliveryContact records.
        """
        user = request.user
        order = get_object_or_404(Order, id=order_id, created_by_user=user, status__in=self.listable_statuses)

        # Build a subquery to obtain distinct company IDs (and cooling unit IDs) from order items.
        company_ids_subquery = OrderCrateItem.objects.filter(order_id=order.id).values(
            'market_listed_crate__crate__cooling_unit__location__company_id',
            'market_listed_crate__crate__cooling_unit_id'
        ).distinct()

        company_delivery_contacts = CompanyDeliveryContact.objects.filter(
            company_id__in=Subquery(company_ids_subquery.values('market_listed_crate__crate__cooling_unit__location__company_id'))
        ).annotate(
            cooling_unit_id=company_ids_subquery.values('market_listed_crate__crate__cooling_unit_id')
        )

        serializer = CompanyDeliveryContactSerializer(company_delivery_contacts, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    @action(methods=['POST'], url_path='pay-with-paystack', detail=True)
    @transaction.atomic
    def pay_with_paystack(self, request, order_id=None):
        """
        POST /marketplace/buyer/orders/<order_id>/pay-with-paystack/
        
        Initiates the payment process using Paystack for an order in the PAYMENT_PENDING state.
        Generates a checkout authorization URL to complete the transaction.
        """
        user = request.user
        order = get_object_or_404(Order, id=order_id, created_by_user=user, status=Order.Status.PAYMENT_PENDING)
        try:
            authorization_url = get_checkout_url_for_order(order)
        except Exception as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Payment process initiated.",
            "authorization_url": authorization_url
        }, status=HTTP_200_OK)

    @action(methods=['POST'], url_path='cancel', detail=True)
    @transaction.atomic
    def cancel(self, request, order_id=None):
        """
        POST /marketplace/buyer/orders/<order_id>/cancel/
        
        Cancels an order that is currently in the PAYMENT_PENDING state.
        After cancellation, returns the updated order data.
        """
        order = get_object_or_404(Order, id=order_id, status=Order.Status.PAYMENT_PENDING)
        order.cancel_payment_pending_order()
        serializer = self.serializer_class(order)
        return Response({"message": "Order cancelled.", "order": serializer.data}, status=HTTP_200_OK)