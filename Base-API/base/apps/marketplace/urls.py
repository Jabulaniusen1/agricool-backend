from rest_framework.routers import DefaultRouter

from base.apps.marketplace.payment_processor.paystack.views import \
    WebhooksPaystackViewSet
from base.apps.marketplace.views.buyer import (
    BuyerAvailableMarketListingViewSet, BuyerCartItemsViewSet, BuyerCartViewSet,
    BuyerOrdersViewSet)
from base.apps.marketplace.views.company import (CompanyDeliveryContactsViewSet,
                                                 CompanyOrdersViewSet,
                                                 CompanySetupViewSet)
from base.apps.marketplace.views.data import MarketplaceDataViewSet
from base.apps.marketplace.views.seller import (SellerCouponsViewSet,
                                                SellerListedCratesViewSet,
                                                SellerOrdersViewSet,
                                                SellerPaystackAccountViewSet)
from base.settings import ENVIRONMENT

# Environment constants
DEVELOPMENT_ENV = 'development'
E2E_ENV = 'e2e'

# Create a router and register the MarketListingViewSet
router = DefaultRouter()

router.register(r'seller/listed-crates', SellerListedCratesViewSet, basename='seller-listed-crates')
router.register(r'seller/coupons', SellerCouponsViewSet, basename='seller-coupons')
router.register(r'seller/paystack-accounts', SellerPaystackAccountViewSet, basename='seller-paystack-accounts')
router.register(r'seller/orders', SellerOrdersViewSet, basename='seller-orders')

router.register(r'buyer/available-listings', BuyerAvailableMarketListingViewSet, basename='buyer-available-listings')
router.register(r'buyer/cart', BuyerCartViewSet, basename='buyer-cart')
router.register(r'buyer/cart/items', BuyerCartItemsViewSet, basename='buyer-cart-items')
router.register(r'buyer/orders', BuyerOrdersViewSet, basename='buyer-orders')

router.register(r'company/orders', CompanyOrdersViewSet, basename='company-orders')
router.register(r'company/delivery-contacts', CompanyDeliveryContactsViewSet, basename='company-delivery-contacts')
router.register(r'company/setup', CompanySetupViewSet, basename='company-setup')

# Integrations
router.register(r'webhooks/paystack', WebhooksPaystackViewSet, basename='webhooks-paystack')

# Master data
router.register(r'data', MarketplaceDataViewSet, basename='data')

# Development test endpoints
if ENVIRONMENT == DEVELOPMENT_ENV or ENVIRONMENT == E2E_ENV:
    from base.apps.marketplace.views.development import DevelopmentViewSet

    router.register(r'development', DevelopmentViewSet, basename='development')

urlpatterns = router.urls
