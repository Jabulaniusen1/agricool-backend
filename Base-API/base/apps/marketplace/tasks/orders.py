from django.utils import timezone

from base.apps.marketplace.models import Order
from base.celery import app


@app.task
def expire_unpaid_orders():
    """
    Cancels unpaid orders to unlock available weight in market listings.
    
    This task targets orders that have been in the PAYMENT_PENDING status
    for over 1 hour. It updates their status to PAYMENT_EXPIRED and then
    recomputes the order to refresh its computed fields.
    
    It is scheduled to run every minute.
    """
    # Calculate cutoff time: orders that haven't been updated in the last hour
    cutoff_time = timezone.now() - timezone.timedelta(hours=1)
    
    # Filter orders that are still pending payment and not updated within the past hour
    orders = Order.objects.filter(
        status=Order.Status.PAYMENT_PENDING,
        status_changed_at__lt=cutoff_time,
    )
    
    # Bulk update orders to mark them as expired
    orders.update(
        status=Order.Status.PAYMENT_EXPIRED,
        status_changed_at=timezone.now(),
    )
    
    # Use cursors to get the most updated state before computing the order
    for order in orders.iterator():
        try:
            # Now call compute with the updated order
            order.compute(save=True, compute_dependencies=True)
        except Exception as e:
            print(f"Failed to compute order {order.id}: {e}")
            pass
