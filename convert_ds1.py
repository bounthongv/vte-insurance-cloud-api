from flask import Flask, request, jsonify
import re

app = Flask(__name__)


units = ["", "ໜຶ່ງ", "ສອງ", "ສາມ", "ສີ່", "ຫ້າ", "ຫົກ", "ເຈັດ", "ແປດ", "ເກົ້າ"]
teens = ["ສິບ", "ສິບເອັດ", "ສິບສອງ", "ສິບສາມ", "ສິບສີ່", "ສິບຫ້າ", "ສິບຫົກ",
       "ສິບເຈັດ", "ສິບແປດ", "ສິບເກົ້າ"]
tens = ["", "ສິບ", "ຊາວ", "ສາມສິບ", "ສີ່ສິບ", "ຫ້າສິບ", "ຫົກສິບ", "ເຈັດສິບ",
             "ແປດສິບ", "ເກົ້າສິບ"]

def number_to_words(number):

  

    if number == 0:
        return "ສູນ"
    elif number < 10:
        return units[number]
    elif 10 <= number < 20:
        return teens[number - 10]
    elif 20 <= number < 100:
        if number % 10 == 1:
            return tens[number // 10] + "ເອັດ"
        else:
            return tens[number // 10] + (number_to_words(number % 10) if number % 10 != 0 else "")
    elif 100 <= number < 1000:
        hundreds_digit = number // 100
        remainder = number % 100
        if remainder == 0:
            return units[hundreds_digit] + "ຮ້ອຍ"
        else:
            return units[hundreds_digit] + "ຮ້ອຍ" + number_to_words(remainder)
    elif 1000 <= number < 1000000:
        thousands_part = number // 1000
        remainder = number % 1000
        thousands_word = number_to_words(thousands_part) + "ພັນ"
        if remainder == 0:
            return thousands_word
        else:
            return thousands_word + number_to_words(remainder)
    elif 1000000 <= number < 1000000000:
        millions_part = number // 1000000
        remainder = number % 1000000
        millions_word = number_to_words(millions_part) + "ລ້ານ"
        if remainder == 0:
            return millions_word
        else:
            return millions_word + number_to_words(remainder)
    elif 1000000000 <= number < 1000000000000:
        billions_part = number // 1000000000
        remainder = number % 1000000000
        billions_word = number_to_words(billions_part) + "ຕື້"
        if remainder == 0:
            return billions_word
        else:
            return billions_word + number_to_words(remainder)
    else:
        return "Number out of range"

@app.route('/number-to-words', methods=['POST'])
def convert_number_to_words():
    data = request.get_json()
    number_input = data.get('number')

    if number_input is None:
        return jsonify({"error": "Please provide a number"}), 400

    # Convert to string first (handles both int/float/string inputs)
    number_str = str(number_input).strip()

    # Validate the number format
    if not re.fullmatch(r'^(\d+(\.\d{1,2})?|\.\d{1,2})$', number_str):
        return jsonify({"error": "Invalid format. Use: 123, 123.45, or .45"}), 400

    # Split into integer and decimal parts
    if '.' in number_str:
        integer_part_str, decimal_part_str = number_str.split('.')
        decimal_part_str = decimal_part_str.ljust(2, '0')[:2]  # Ensure two digits
    else:
        integer_part_str = number_str
        decimal_part_str = ''

    # Handle cases like ".45" which should be treated as 0.45
    if integer_part_str == '':
        integer_part = 0
    else:
        try:
            integer_part = int(integer_part_str)
        except ValueError:
            return jsonify({"error": "Invalid integer part"}), 400

    # Validate integer part range
    if integer_part < 0 or integer_part >= 1000000000000:
        return jsonify({"error": "Integer part out of range (0-999,999,999,999)"}), 400

    # Process integer part
    integer_words = number_to_words(integer_part)

    # Process decimal part
    decimal_words = ""
    if decimal_part_str:
        decimal_digits = []
        for d in decimal_part_str:
            digit = int(d)
            decimal_digits.append("ສູນ" if digit == 0 else units[digit])
        decimal_words = "ຈຸດ" + "".join(decimal_digits)

    # Combine words (omit "ສູນ" for pure decimals like 0.45)
    if integer_part == 0 and decimal_part_str:
        full_words = decimal_words
    else:
        full_words = integer_words + decimal_words

    return jsonify({"number": number_str, "words": full_words})

if __name__ == "__main__":
    app.run(debug=False)