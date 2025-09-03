import unittest

from .fees import (
    calculate_final_amount_and_paystack_fees_from_subtotal_amount,
    calculate_paystack_fees_from_final_amount)

# Test constants for transaction 4252978540
TEST_TRANSACTION_AMOUNT = 3264.18
TEST_TRANSACTION_CURRENCY = "NGN"
TEST_TRANSACTION_FEES_AMOUNT = 148.97


class PaystackFeesTest(unittest.TestCase):

    def test_case_for_transaction_4252978540(self):
        # ACCOUNT_AMOUNT = 103.21
        # SPLITS = [2412.00, 600.00]

        subtotal = TEST_TRANSACTION_AMOUNT - TEST_TRANSACTION_FEES_AMOUNT
        self.assertEqual(TEST_TRANSACTION_FEES_AMOUNT, calculate_paystack_fees_from_final_amount(TEST_TRANSACTION_AMOUNT, currency=TEST_TRANSACTION_CURRENCY))
        self.assertEqual((TEST_TRANSACTION_AMOUNT, TEST_TRANSACTION_FEES_AMOUNT), calculate_final_amount_and_paystack_fees_from_subtotal_amount(subtotal, currency=TEST_TRANSACTION_CURRENCY))
