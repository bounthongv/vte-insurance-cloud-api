import hashlib
from datetime import datetime

def string_sort(value):
    """Sort the characters in a string."""
    return ''.join(sorted(value))

def standardize_date_format(sign_date):
    """
    Standardize the date to the format dd/MM/yyyy HH:mm:ss.
    Input date can be in any recognizable format.
    """
    try:
        # Parse the input date
        parsed_date = datetime.strptime(sign_date, "%Y %b %d")
        # Reformat to the desired format
        standardized_date = parsed_date.strftime("%d/%m/%Y %H:%M:%S")
        return standardized_date
    except ValueError:
        raise ValueError(f"Invalid date format: {sign_date}")

def generate_signature(key_code, sign_date, order_no):
    """Generate a signature using keyCode, signDate, and ORDER_NO."""
    standardized_date = standardize_date_format(sign_date)
    concatenated = f"{key_code}{standardized_date}{order_no}"
    sorted_string = string_sort(concatenated)
    signature = hashlib.md5(sorted_string.encode()).hexdigest()
    return signature

# Input values
key_code = "VTI"
sign_date = "2024 Dec 18"  # Input date in original format
order_no = "11"

# Generate the signature
try:
    signature = generate_signature(key_code, sign_date, order_no)
    print("Generated Signature:", signature)
except ValueError as e:
    print("Error:", e)
