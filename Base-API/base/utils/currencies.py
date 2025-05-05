from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import iso4217
from decimal import Decimal, ROUND_CEILING

def get_currency_fraction_digits(currency_code):
    currency = iso4217.Currency(currency_code)
    return currency.exponent

# Function to round the float according to the currency's fractional unit using iso4217 library
def quantitize_float(float_amount, currency_code, rounding=ROUND_CEILING):
    fraction_digits = get_currency_fraction_digits(currency_code)
    return float(Decimal(float_amount).quantize(Decimal(f'1.{"0" * fraction_digits}'), rounding=rounding))

def flat_int_to_float(flat_int_amount, currency_code, rounding=ROUND_CEILING):
    fraction_digits = get_currency_fraction_digits(currency_code)
    return float(int(flat_int_amount) / (10 ** fraction_digits))

def float_to_flat_int(float_amount, currency_code, rounding=ROUND_CEILING):
    fraction_digits = get_currency_fraction_digits(currency_code)
    return int(Decimal(float_amount * (10 ** fraction_digits)).quantize(Decimal('1.0'), rounding=rounding))

def is_valid_currency(currency_code):
    try:
        iso4217.Currency(currency_code)
        return True
    except:
        return False

# Custom model field validator function
def validate_currency(value):
    if not is_valid_currency(value):
        raise ValidationError(
            _('%(value)s is not a valid ISO 4217 currency code.'),
            params={'value': value},
        )
