import hashlib

def string_sort(value):
    """Sort the characters in a string."""
    return ''.join(sorted(value))

def generate_signature(key_code, sign_date, order_no):
    """Generate a signature using keyCode, signDate, and ORDER_NO."""
    concatenated = f"{key_code}{sign_date}{order_no}"
    sorted_string = string_sort(concatenated)
    signature = hashlib.md5(sorted_string.encode()).hexdigest()
    return signature

# Input values
key_code = "VTI"
sign_date = "2025-10-31"
order_no = "12345678"

# Generate the signature
signature = generate_signature(key_code, sign_date, order_no)
print("Generated Signature:", signature)
