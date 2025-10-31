import hashlib

def string_sort(value):
    """Sort the characters in a string."""
    return ''.join(sorted(value))

def generate_signature(key_code, sign_date):
    """Generate a signature using keyCode, signDate, and ORDER_NO."""
    concatenated = f"{key_code}{sign_date}"
    sorted_string = string_sort(concatenated)
    signature = hashlib.md5(sorted_string.encode()).hexdigest()
    return signature

# Input values
key_code = "APIS"
sign_date = "2024 Dec 17"


# Generate the signature
signature = generate_signature(key_code, sign_date)
print("Generated Signature:", signature)
