from django.db import transaction
from django.db.models import F, Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED,
                                   HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST,
                                   HTTP_403_FORBIDDEN, HTTP_409_CONFLICT)
from rest_framework.viewsets import ViewSet

from base.apps.marketplace.models import (Coupon, MarketListedCrate,
                                          MarketListedCratePrice, Order,
                                          OrderCrateItem, PaystackAccount)
from base.apps.marketplace.serializers.common import (
    CouponSerializer, MarketListedCrateSerializer, PaystackAccountSerializer)
from base.apps.marketplace.serializers.seller_requests import (
    SellerAttachPaystackAccountRequestSerializer,
    SellerListingUpdateRequestSerializer,
    SellerRegisterNewCouponRequestSerializer)
from base.apps.marketplace.serializers.seller_responses import \
    SellerOrderSerializer
from base.apps.storage.models import Crate
from base.apps.user.models import (Company, Notification, Operator,
                                   ServiceProvider, User)
from base.celery import app
from base.utils.secure_errors import handle_internal_error


# -----------------------------------------------------------------------------
# Marketplace listings related views
# -----------------------------------------------------------------------------

class SellerListedCratesViewSet(ViewSet):
    """
    ViewSet for managing seller-listed crate listings.

    Provides endpoints to list all current market listings, retrieve a specific listing,
    upsert (create or update) listings, and delete a listing. The filtering of listings
    is based on the seller—either on behalf of a user or a company.
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'crate_id'

    def get_seller(self):
        """
        Retrieve the seller based on query parameters.

        Checks if the request contains 'operator_on_behalf_of_seller_user_id', 
        'operator_on_behalf_of_seller_company_id', or 'operator_on_behalf_of_seller_farmer_id'
        and returns the respective seller or company. If none are provided, returns the
        current authenticated user.
        """
        user = self.request.user

        operator_on_behalf_of_seller_user_id = self.request.query_params.get('operator_on_behalf_of_seller_user_id')
        if operator_on_behalf_of_seller_user_id:
            # TODO: validate if the current user belongs to a company that owns a cooling unit and has the seller attached
            seller = get_object_or_404(User, id=operator_on_behalf_of_seller_user_id)
            return seller, None

        operator_on_behalf_of_seller_company_id = self.request.query_params.get('operator_on_behalf_of_seller_company_id')
        if operator_on_behalf_of_seller_company_id:
            company = get_object_or_404(Company, id=operator_on_behalf_of_seller_company_id)
            return None, company

        operator_on_behalf_of_seller_farmer_id = self.request.query_params.get('operator_on_behalf_of_seller_farmer_id')
        if operator_on_behalf_of_seller_farmer_id:
            # TODO: validate if the current user belongs to a company that owns a cooling unit and has the seller attached
            seller = get_object_or_404(User, farmer__id=operator_on_behalf_of_seller_farmer_id)
            return seller, None

        return user, None

    def get_queryset_filter_kwargs(self):
        """
        Build filter keyword arguments for MarketListedCrate based on seller ownership.

        Returns:
            dict: Filter keyword arguments used in queryset filtering.
        """
        seller_user, seller_on_behalf_of_company = self.get_seller()
        if seller_on_behalf_of_company:
            return {
                'crate__produce__checkin__owned_on_behalf_of_company': seller_on_behalf_of_company,
            }
        return {
            'crate__produce__checkin__owned_by_user': seller_user,
            'crate__produce__checkin__owned_on_behalf_of_company__isnull': True,
        }

    def list(self, request):
        """
        GET /marketplace/seller/listed-crates/

        Retrieves all active market listings (i.e. not delisted) for the seller.
        """
        seller_user, seller_on_behalf_of_company = self.get_seller()
        queryset = MarketListedCrate.objects.filter(
            delisted_at__isnull=True,
            **self.get_queryset_filter_kwargs()
        )

        # Prepare response data (pagination might be added later)
        return Response({
            'nodes': MarketListedCrateSerializer(queryset, many=True).data
        }, status=HTTP_200_OK)

    def retrieve(self, request, crate_id=None):
        """
        GET /marketplace/seller/listed-crates/<crate_id>/

        Retrieves a specific market listing for a given crate ID.
        """
        listing = get_object_or_404(
            MarketListedCrate,
            crate_id=crate_id,
            delisted_at__isnull=True,
            **self.get_queryset_filter_kwargs()
        )
        serializer = MarketListedCrateSerializer(listing)
        return Response(serializer.data, status=HTTP_200_OK)

    @transaction.atomic
    def create(self, request):
        """
        POST /marketplace/seller/listed-crates/

        Upserts (creates or updates) a market listing for the seller.
        Validates the input, checks that the seller can receive payments, ensures the seller owns the produce,
        and creates/updates the listing along with creating a listing price entry.
        It also sends notifications if necessary.
        """
        user = request.user
        seller_user, seller_on_behalf_of_company = self.get_seller()

        # Validate input using the appropriate serializer
        input_serializer = SellerListingUpdateRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        # Verify that the seller is capable of receiving payments.
        if seller_on_behalf_of_company:
            if not PaystackAccount.company_has_default_account(seller_on_behalf_of_company.id):
                return Response({"error": "Company does not have a default paystack account"}, status=HTTP_403_FORBIDDEN)
        elif seller_user:
            if not PaystackAccount.user_has_default_account(seller_user.id):
                return Response({"error": "User does not have a default paystack account"}, status=HTTP_403_FORBIDDEN)
        else:
            return Response({"error": "Seller must be either a user or a company"}, status=HTTP_403_FORBIDDEN)

        # Ensure the seller owns the produce: get crates specified in the input.
        crates = Crate.objects.filter(
            id__in=input_serializer.validated_data['crate_ids'],
            **(
                {'produce__checkin__owned_on_behalf_of_company': seller_on_behalf_of_company}
                if seller_on_behalf_of_company else {
                    'produce__checkin__owned_by_user': seller_user,
                    'produce__checkin__owned_on_behalf_of_company__isnull': True,
                }
            ),
        ).annotate(
            company_id=F('cooling_unit__location__company_id')
        ).all()

        if crates.count() == 0 or crates.count() != len(input_serializer.validated_data['crate_ids']):
            return Response({"error": "Crates do not exist or do not belong to the user"}, status=HTTP_400_BAD_REQUEST)

        # Verify that each cooling company has a default Paystack account.
        for company_id in crates.values_list('company_id', flat=True).distinct():
            if not PaystackAccount.company_has_default_account(company_id):
                return Response({"error": f"Cooling company #{company_id} does not have a default paystack account"}, status=HTTP_403_FORBIDDEN)

        # Annotate related user and smartphone info for the crates.
        crates_rel_users = crates.annotate(
            user_id=F('produce__checkin__owned_by_user_id'),
            farmer_with_smartphone=F('produce__checkin__owned_by_user__farmer__smartphone'),
        ).values('user_id', 'farmer_with_smartphone').distinct()

        crates_rel_user_ids = [user['user_id'] for user in crates_rel_users]

        listings = []
        notify_on_price_change = []

        # Create or update a market listing for each crate.
        for crate in crates:
            listing = MarketListedCrate.objects.filter(
                crate=crate, delisted_at__isnull=True
            ).first()

            if listing is None:
                listing = MarketListedCrate.objects.create(
                    crate=crate,
                    currency=crate.currency,
                )

            # Create a new price entry for the listing.
            price = MarketListedCratePrice.objects.create(
                market_listed_crate=listing,
                produce_price_per_kg=input_serializer.validated_data['produce_price_per_kg'],
                created_by_user_id=user.id,
            )

            # If the current user is not among the related users of the crates, mark for SMS notification.
            if user.id not in crates_rel_user_ids:
                notify_on_price_change.append(price)

            listing.compute(save=True)
            listings.append(listing)

        # Send SMS notifications for the price change.
        if len(notify_on_price_change) > 0:
            ids = [price.id for price in notify_on_price_change]
            # Loop through each related user to decide on notification method.
            for user in crates_rel_users:
                if user['farmer_with_smartphone']:
                    # Create a notification for each price change
                    for price in notify_on_price_change:
                        Notification.objects.create(
                            user_id=user['user_id'],
                            event_type=Notification.NotificationType.LISTING_PRICE_UPDATED,
                            specific_id=price.id,
                        )
                else:
                    # Use a task to send SMS for combined price changes.
                    app.send_task(
                        "base.apps.marketplace.tasks.sms.send_sms_notification_to_owner_on_listing_price_changed",
                        args=[ids, user['user_id']]
                    )

        serializer = MarketListedCrateSerializer(listings, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, crate_id=None):
        """
        DELETE /marketplace/seller/listed-crates/<crate_id>/

        Deletes an existing market listing (i.e. delists it) provided that there is no weight
        locked in payment pending orders. It then recomputes affected orders.
        """
        listing = get_object_or_404(
            MarketListedCrate,
            crate_id=crate_id,
            delisted_at__isnull=True,
            **self.get_queryset_filter_kwargs()
        )

        # Prevent deletion if there is weight locked in payment pending orders.
        if listing.cmp_weight_locked_in_payment_pending_orders_in_kg > 0:
            return Response(
                {"error": "Cannot delete listing with weight locked in payment pending orders."},
                status=HTTP_400_BAD_REQUEST
            )

        # Mark the listing as delisted and recompute its values.
        listing.delisted_at = timezone.now()
        listing.compute(save=True)

        # Gather order IDs for orders (in CART status) that reference this listing.
        order_ids = listing.order_items.filter(order__status=Order.Status.CART).values_list('order_id', flat=True)

        # Remove all order items associated with this listing.
        OrderCrateItem.objects.filter(market_listed_crate=listing).delete()

        # Recompute each order that was affected.
        for order in Order.objects.filter(id__in=order_ids).iterator():
            order.compute(save=True, compute_dependencies=False)

        return Response(status=HTTP_204_NO_CONTENT)



# -----------------------------------------------------------------------------
# Coupons related views
# -----------------------------------------------------------------------------

class SellerCouponsViewSet(ViewSet):
    """
    A viewset for sellers to manage coupons.
    
    Endpoints:
      - GET /marketplace/seller/coupons/ : List all coupons for the seller.
      - POST /marketplace/seller/coupons/ : Create a new coupon.
      - GET /marketplace/seller/coupons/<coupon_id>/ : Retrieve a specific coupon.
      - DELETE /marketplace/seller/coupons/<coupon_id>/ : Revoke (delete) a coupon.
      
    Note: Coupons are immutable except for updating the `revoked_at` field when revoking.
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'coupon_id'

    def get_ownership(self):
        """
        Determines the ownership context for coupons based on query parameters.
        
        If 'owned_on_behalf_of_company_id' is provided, retrieves the respective company and
        verifies the user's association with that company. Otherwise, returns the current user.
        
        Returns:
            tuple: (user, company) where company is None if the coupon is personal.
            
        Raises:
            PermissionDenied: If the user does not have permission to manage the company's coupons.
        """
        user = self.request.user
        owned_on_behalf_of_company_id = self.request.query_params.get('owned_on_behalf_of_company_id', None)

        if owned_on_behalf_of_company_id:
            company = get_object_or_404(Company, id=owned_on_behalf_of_company_id)
            if not ServiceProvider.is_employee_of_company(user, company):
                raise PermissionDenied("You do not have permission to manage the coupons for this company.")
            return user, company

        return user, None

    def get_queryset_kwargs(self):
        """
        Builds filter keyword arguments for retrieving coupons based on ownership context.
        
        Returns:
            dict: Queryset filter arguments.
        """
        user, owned_on_behalf_of_company = self.get_ownership()
        if not owned_on_behalf_of_company:
            return {'owned_by_user': user, 'owned_on_behalf_of_company__isnull': True}
        return {'owned_on_behalf_of_company': owned_on_behalf_of_company}

    def get_queryset(self):
        """
        Returns the filtered queryset for coupons based on ownership context.
        """
        return Coupon.objects.filter(**self.get_queryset_kwargs())

    def list(self, request):
        """
        GET /marketplace/seller/coupons/
        
        Lists all coupons for the seller. The 'show_revoked' query parameter can be:
          - "only": Show only revoked coupons.
          - "included": Include revoked coupons.
          - Any other value (default "hide"): Hide revoked coupons.
        """
        show_revoked = request.query_params.get('show_revoked', "hide")
        queryset = self.get_queryset()

        if show_revoked == "only":
            queryset = queryset.filter(revoked_at__isnull=False)
        elif show_revoked != "included":
            queryset = queryset.filter(revoked_at__isnull=True)

        # TODO: Might be useful to add pagination here in the future
        return Response({
            'nodes': CouponSerializer(queryset, many=True).data
        }, status=HTTP_200_OK)

    @transaction.atomic
    def create(self, request):
        """
        POST /marketplace/seller/coupons/
        
        Creates a new coupon for the seller.
        Validates the coupon data and ensures the coupon code is unique among active coupons.
        """
        user, owned_on_behalf_of_company = self.get_ownership()

        input_serializer = SellerRegisterNewCouponRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        code = input_serializer.validated_data['code']
        discount_percentage = input_serializer.validated_data['discount_percentage']

        # Check for duplicate active coupon code
        if self.get_queryset().filter(code=code, revoked_at__isnull=True).exists():
            return Response(
                {'error': f'Coupon code "{code}" already exists.'},
                status=HTTP_409_CONFLICT
            )

        coupon = Coupon.objects.create(
            created_by_user=user,
            owned_by_user=user,
            owned_on_behalf_of_company=owned_on_behalf_of_company,
            code=code,
            discount_percentage=discount_percentage,
        )
        serializer = CouponSerializer(coupon)
        return Response(serializer.data, status=HTTP_201_CREATED)

    def retrieve(self, request, coupon_id=None):
        """
        GET /marketplace/seller/coupons/<coupon_id>/
        
        Retrieves details of a specific coupon for the seller.
        """
        coupon = get_object_or_404(Coupon, id=coupon_id, **self.get_queryset_kwargs())
        serializer = CouponSerializer(coupon)
        return Response(serializer.data, status=HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, coupon_id=None):
        """
        DELETE /marketplace/seller/coupons/<coupon_id>/
        
        Revokes a coupon (marks as deleted) for the seller.
        A coupon can only be revoked if it is currently active.
        """
        coupon = get_object_or_404(Coupon, id=coupon_id, **self.get_queryset_kwargs())

        if coupon.revoked_at is not None:
            return Response(status=HTTP_400_BAD_REQUEST)

        coupon.revoke()
        return Response(status=HTTP_204_NO_CONTENT)

# -----------------------------------------------------------------------------
#  Payouts related views
# -----------------------------------------------------------------------------

class SellerPaystackAccountViewSet(ViewSet):
    """
    ViewSet for managing Paystack accounts for sellers.

    Endpoints include:
      - GET /marketplace/seller/paystack-accounts/ : List seller's Paystack accounts.
      - POST /marketplace/seller/paystack-accounts/ : Create a new Paystack account.
      - GET /marketplace/seller/paystack-accounts/<pk>/ : Retrieve a specific Paystack account.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        GET /marketplace/seller/paystack-accounts/

        Lists all Paystack accounts for the current user. If a `company_id` query
        parameter is provided, it will filter and only return accounts belonging to that company.
        """
        user = request.user
        company_id = request.query_params.get('company_id', None)
        accounts = PaystackAccount.objects.all()

        if company_id:
            # Validate that the user belongs to the company.
            company = get_object_or_404(Company, id=company_id)
            if not ServiceProvider.is_employee_of_company(user, company):
                return Response({"error": "Access denied"}, status=HTTP_403_FORBIDDEN)
            accounts = accounts.filter(owned_on_behalf_of_company=company)
        else:
            # Otherwise, list personal accounts created by the user.
            accounts = accounts.filter(owned_by_user=user)

        serializer = PaystackAccountSerializer(accounts, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    @transaction.atomic
    def create(self, request):
        """
        POST /marketplace/seller/paystack-accounts/

        Creates a new Paystack account for a seller. If a `company_id` is provided in the request data,
        the user is validated against that company. The endpoint then creates the Paystack account using
        the provided bank details and returns the created account.
        """
        user = request.user
        input_serializer = SellerAttachPaystackAccountRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        # Check if a company_id is provided and validate ownership.
        company_id = input_serializer.validated_data.get('company_id', None)
        company = None
        if company_id:
            company = get_object_or_404(Company, id=company_id)
            if not ServiceProvider.is_employee_of_company(user, company):
                return Response({"error": "Access denied"}, status=HTTP_403_FORBIDDEN)

        try:
            paystack_account = PaystackAccount.create(
                owned_on_behalf_of_company=company,
                owned_by_user=user,
                account_type=input_serializer.validated_data['account_type'],
                bank_code=input_serializer.validated_data['bank_code'],
                country_code=input_serializer.validated_data['country_code'],
                account_number=input_serializer.validated_data['account_number'],
                account_name=input_serializer.validated_data['account_name'],
            )
        except Exception as e:
            return handle_internal_error(e, "paystack account creation")

        serializer = PaystackAccountSerializer(paystack_account)
        return Response(serializer.data, status=HTTP_201_CREATED)

    @transaction.atomic
    def retrieve(self, request, pk=None):
        """
        GET /marketplace/seller/paystack-accounts/<pk>/

        Retrieves a specific Paystack account. The endpoint checks if the current user
        has access to the account (either because they created it or because it is tied to
        their company).
        """
        user = request.user
        account = get_object_or_404(PaystackAccount, pk=pk)

        # Check if the user is allowed to access this account.
        if account.created_by_user != user and not account.company.users.filter(id=user.id).exists():
            return Response({"error": "Access denied"}, status=HTTP_403_FORBIDDEN)

        serializer = PaystackAccountSerializer(account)
        return Response(serializer.data)


# -----------------------------------------------------------------------------
# Orders
# -----------------------------------------------------------------------------

class SellerOrdersViewSet(ViewSet):
    """
    ViewSet for sellers to list orders.
    
    This endpoint retrieves all orders with a 'PAID' status for the authenticated seller.
    A query parameter 'owned_on_behalf_of_company_id' can be provided to filter orders
    owned by a company. The seller must be associated with the specified company via 
    ServiceProvider or Operator relationships.
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_id'
    serializer_class = SellerOrderSerializer

    def list(self, request):
        """
        GET /marketplace/seller/orders/
        
        Lists all orders for the authenticated seller that have a PAID status.
        Orders are filtered by the seller's ID (or by the company ID if the request includes
        'owned_on_behalf_of_company_id'). The results are prefetching related order items for better
        performance.
        """
        user = request.user
        # Retrieve the company filter if provided
        owned_on_behalf_of_company_id = request.query_params.get('owned_on_behalf_of_company_id') or None

        # If filtering by company, validate that the seller is associated with the company
        if owned_on_behalf_of_company_id:
            company = get_object_or_404(Company, id=owned_on_behalf_of_company_id)
            if not ServiceProvider.is_employee_of_company(user, company) and not Operator.is_operator_of_company(user, company):
                return Response({"error": "Access denied"}, status=HTTP_403_FORBIDDEN)

        # Filter orders that have been paid and belong to the seller, either by user or company ownership.
        orders = Order.objects.prefetch_related(
            Prefetch(
                'items',
                queryset=OrderCrateItem.objects.filter(
                    market_listed_crate__crate__produce__checkin__owned_by_user_id=user.id,
                    market_listed_crate__crate__produce__checkin__owned_on_behalf_of_company_id=owned_on_behalf_of_company_id,
                )
            )
        ).filter(
            status=Order.Status.PAID,
            items__market_listed_crate__crate__produce__checkin__owned_by_user_id=user.id,
            items__market_listed_crate__crate__produce__checkin__owned_on_behalf_of_company_id=owned_on_behalf_of_company_id,
        ).distinct()

        serializer = self.serializer_class(orders, many=True)
        return Response(serializer.data, status=HTTP_200_OK)