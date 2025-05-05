from django.db.models import Prefetch, Q
from base.apps.marketplace.models.order import Order
from base.apps.marketplace.models.order_crate_item import OrderCrateItem
from base.apps.user.models.company import Company


def get_cart_prefetched(user):
    """
    Retrieve the active cart for a user with order items prefetched.

    This returns the first Order instance for the specified user whose status is CART,
    and it prefetches the associated order items ordered by their ID.

    Args:
        user: User instance for whom the cart should be retrieved.

    Returns:
        An Order instance (active cart) or None if not found.
    """
    return (
        Order.objects
        .filter(created_by_user=user, status=Order.Status.CART)
        .prefetch_related(Prefetch('items', queryset=OrderCrateItem.objects.order_by('id')))
        .first()
    )


def get_cart(user):
    """
    Retrieve the active cart for a user.

    Args:
        user: User instance for whom the cart should be retrieved.

    Returns:
        An Order instance (active cart) or None if not found.
    """
    return Order.objects.filter(created_by_user=user, status=Order.Status.CART).first()


def get_or_create_cart(user):
    """
    Retrieve or create the active cart for a user.

    Args:
        user: User instance for whom the cart should be retrieved or created.

    Returns:
        A tuple of (Order instance, created (bool)) as returned by get_or_create.
    """
    return Order.objects.get_or_create(created_by_user=user, status=Order.Status.CART)


def get_company(request, company_id=None):
    """
    Retrieve a Company related to the current user based on the provided company_id.

    Searches for companies associated with the user as a service provider or operator.
    If a single company is found, it is returned immediately. If multiple companies
    exist, the function will look for a specific company using the company_id provided
    in the URL query parameters.

    Args:
        request: The HTTP request object, expected to contain the authenticated user.
        company_id: An optional company ID. If not provided, the function looks for it in the
                    request's query parameters under the key 'company_id'.

    Returns:
        A Company instance corresponding to the provided or derived company_id.

    Raises:
        ValueError: If no company_id is provided or if the company with the given ID is not found.
    """
    user = request.user

    # Filter companies that the user is related to either as a service provider or operator.
    companies = Company.objects.filter(
        Q(service_provider_company__user_id=user.id) | Q(operator_company__user_id=user.id)
    ).distinct()

    if companies.count() == 1:
        return companies.first()

    # If company_id is not passed as an argument, attempt to fetch it from query parameters.
    company_id = company_id or request.query_params.get('company_id', None)
    if not company_id:
        raise ValueError("Expecting company_id in query params.")

    # Find the matching company from the filtered list.
    for company in companies:
        if int(company.id) == int(company_id):
            return company

    raise ValueError(f"Company with id {company_id} not found.")
