import unittest

from .fees import (
    calculate_final_amount_and_paystack_fees_from_subtotal_amount,
    calculate_paystack_fees_from_final_amount)


class PaystackFeesTest(unittest.TestCase):

    def test_case_for_transaction_4252978540(self):
        AMOUNT = 3264.18
        CURRENCY = "NGN"
        FEES_AMOUNT = 148.97
        # ACCOUNT_AMOUNT = 103.21
        # SPLITS = [2412.00, 600.00]

        subtotal = AMOUNT - FEES_AMOUNT
        self.assertEqual(FEES_AMOUNT, calculate_paystack_fees_from_final_amount(AMOUNT, currency=CURRENCY))
        self.assertEqual((AMOUNT, FEES_AMOUNT), calculate_final_amount_and_paystack_fees_from_subtotal_amount(subtotal, currency=CURRENCY))
