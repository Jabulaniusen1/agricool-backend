from decimal import ROUND_CEILING, ROUND_HALF_UP
from math import ceil
from typing import Tuple

from base.utils.currencies import flat_int_to_float, float_to_flat_int, quantitize_float

# Constants based on Paystack's fee structure
PAYSTACK_LOCAL_TRANSACTION_FEE = 0.015  # Local transaction fee (1.5%)
PAYSTACK_INTERNATIONAL_TRANSACTION_FEE = 0.039  # International transaction fee (3.9%)

# Paystack fee thresholds and caps (in NGN/kobo)
DEFAULT_THRESHOLD_FLAT = float_to_flat_int(2500, "NGN")  # Amount threshold after which additional fee is applied (in NGN)
DEFAULT_ADDITIONAL_CHARGE_FLAT = float_to_flat_int(100, "NGN")  # Additional fee after the threshold (in NGN)
DEFAULT_CAP_FLAT = float_to_flat_int(2000, "NGN")  # Maximum fee cap (in NGN)

def parse_options(international_transaction: bool = False, currency: str = "NGN") -> dict:
    """
    Parses options for fee calculation.

    Args:
        international_transaction (bool): Whether the transaction is international.
        currency (str): The currency code.

    Returns:
        dict: Dictionary containing the transaction fee and currency.
    """
    transaction_fee = PAYSTACK_INTERNATIONAL_TRANSACTION_FEE if international_transaction else PAYSTACK_LOCAL_TRANSACTION_FEE

    return {
        "transaction_fee": transaction_fee,
        "currency": currency
    }

def calculate_paystack_fees_from_final_amount(final_amount: float = 0.0, **kwargs) -> float:
    """
    Calculates the Paystack fee from the final amount.

    Args:
        final_amount (float): The final amount (including fees) as a float.
        **kwargs: Additional options (e.g., international_transaction, currency).

    Returns:
        float: The fee amount (in NGN, rounded appropriately).
    """
    options = parse_options(**kwargs)
    TRANSACTION_FEE = options.get('transaction_fee', 0)
    CURRENCY = options.get('currency')

    final_amount_flat = float_to_flat_int(final_amount, CURRENCY)

    # Calculate base transaction fee
    fee_flat = int(ceil(final_amount_flat * TRANSACTION_FEE))

    # Add additional charge if final amount exceeds the threshold
    if final_amount_flat >= DEFAULT_THRESHOLD_FLAT:
        fee_flat += DEFAULT_ADDITIONAL_CHARGE_FLAT

    # Apply the cap to the fee if it exceeds the maximum allowed value
    if fee_flat > DEFAULT_CAP_FLAT:
        fee_flat = DEFAULT_CAP_FLAT

    # Return the fee as a float (converted from flat integer value)
    return flat_int_to_float(fee_flat, CURRENCY, rounding=ROUND_CEILING)

def calculate_final_amount_and_paystack_fees_from_subtotal_amount(
    subtotal_amount: float = 0.0, 
    tolerance: float = 0.01, 
    max_iterations: int = 100, 
    **kwargs
) -> Tuple[float, float]:
    """
    Calculates the final amount (including fees) and the Paystack fee based on a given subtotal.

    This function iteratively adjusts an initial guess for the final amount until the computed
    subtotal (final amount minus fee) converges to the desired subtotal within the specified tolerance.

    Args:
        subtotal_amount (float): The desired subtotal amount (excluding fees).
        tolerance (float): The convergence tolerance.
        max_iterations (int): Maximum number of iterations to attempt.
        **kwargs: Additional options (e.g., international_transaction, currency).

    Returns:
        Tuple[float, float]: A tuple containing the final amount (with fees) and the fee.
    
    Raises:
        RuntimeError: If the iterative process does not converge within the maximum iterations.
    """
    options = parse_options(**kwargs)
    TRANSACTION_FEE = options.get('transaction_fee', 0)
    CURRENCY = options.get('currency')

    # Initial guess for the final amount based on a simple markup
    total_guess = quantitize_float(subtotal_amount * (1 + TRANSACTION_FEE), CURRENCY, rounding=ROUND_HALF_UP)
    fees = 0.0

    for _ in range(max_iterations):
        fees = calculate_paystack_fees_from_final_amount(total_guess, **kwargs)
        calculated_subtotal = total_guess - fees
        difference = subtotal_amount - calculated_subtotal

        if abs(difference) < tolerance:
            break

        # Adjust the guess based on the difference between the desired and calculated subtotal
        total_guess += quantitize_float(difference, CURRENCY, rounding=ROUND_HALF_UP)
    else:
        raise RuntimeError("Failed to converge on final amount within maximum iterations")

    return quantitize_float(total_guess, CURRENCY, rounding=ROUND_HALF_UP), fees
