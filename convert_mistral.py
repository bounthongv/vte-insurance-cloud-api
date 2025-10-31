from flask import Flask, request, jsonify

app = Flask(__name__)

def number_to_words(number):
    units = ["", "ໜຶ່ງ", "ສອງ", "ສາມ", "ສີ່", "ຫ້າ", "ຫົກ", "ເຈັດ", "ແປດ", "ເກົ້າ"]
    teens = ["ສິບ", "ສິບເອັດ", "ສິບສອງ", "ສິບສາມ", "ສິບສີ່", "ສິບຫ້າ", "ສິບຫົກ",
             "ສິບເຈັດ", "ສິບແປດ", "ສິບເກົ້າ"]
    tens = ["", "ສິບ", "ຊາວ", "ສາມສິບ", "ສີ່ສິບ", "ຫ້າສິບ", "ຫົກສິບ", "ເຈັດສິບ",
            "ແປດສິບ", "ເກົ້າສິບ"]

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
            return tens[number // 10] + ("" + number_to_words(number % 10) if number % 10 != 0 else "")
    elif 100 <= number < 1000:
        hundreds_digit = number // 100
        remainder = number % 100
        if remainder == 0:
            return units[hundreds_digit] + "ຮ້ອຍ"
        else:
            return units[hundreds_digit] + "ຮ້ອຍ" + number_to_words(remainder)
    elif 1000 <= number < 100000:
        thousands_part = number // 1000
        remainder = number % 1000
        thousands_word = number_to_words(thousands_part) + "ພັນ"
        if remainder == 0:
            return thousands_word
        else:
            return thousands_word + number_to_words(remainder)
    elif 100000 <= number < 1000000:  # Fix for 100,000 to 999,999
        hundred_thousands_part = number // 100000
        remainder = number % 100000
        hundred_thousands_word = number_to_words(hundred_thousands_part) + "ແສນ"
        if remainder == 0:
            return hundred_thousands_word
        else:
            return hundred_thousands_word + number_to_words(remainder)
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

def number_with_decimals_to_words(number):
    """ Convert a number with up to two decimal places to words in Lao. """
    integer_part = int(number)
    decimal_part = round((number - integer_part) * 100)  # Extract two decimal places

    words = number_to_words(integer_part)  # Convert integer part correctly

    if decimal_part > 0:
        decimal_digits = str(decimal_part).zfill(2)  # Ensure two digits
        decimal_words = "ຈຸດ" + "".join([number_to_words(int(digit)) for digit in decimal_digits])
        return words + decimal_words
    else:
        return words

@app.route('/number-to-words', methods=['POST'])
def convert_number_to_words():
    data = request.get_json()
    number = data.get('number')

    if number is None:
        return jsonify({"error": "Please provide a number"}), 400

    try:
        number = float(number)
    except ValueError:
        return jsonify({"error": "Invalid number provided"}), 400

    if number < 0 or number >= 1000000000000:
        return jsonify({"error": "Number out of range. Please provide a number between 0 and 999,999,999,999"}), 400

    words = number_with_decimals_to_words(number)
    return jsonify({"number": number, "words": words})

if __name__ == "__main__":
    app.run(debug=False)
