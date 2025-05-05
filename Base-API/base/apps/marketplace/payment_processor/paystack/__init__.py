from paystackapi.paystack import Paystack
from base.settings import PAYSTACK_SECRET_KEY

paystack = Paystack(secret_key=PAYSTACK_SECRET_KEY)
