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
        # Handle the case where the last digit is 1
        if number % 10 == 1:
            # Check if the last two digits are "01"
            if number % 100 == 1:
                return tens[number // 10] + "ແລະໜຶ່ງ"
            elif (number // 10) % 10 != 0:
                return tens[number // 10] + "ເອັດ"
            else:
                return tens[number // 10] + "ແລະໜຶ່ງ"
        else:
            return tens[number // 10] + ("" + number_to_words(number % 10) if number % 10 != 0 else "")
    elif 100 <= number < 1000:
        # Handle the case where the last digit is 1
        if number % 10 == 1:
            # Check if the last two digits are "01"
            if number % 100 == 1:
                return units[number // 100] + "ຮ້ອຍ" + "ແລະໜຶ່ງ"
            elif (number % 100) // 10 != 0:
                return units[number // 100] + "ຮ້ອຍ" + ("" + number_to_words(number % 100) if number % 100 != 0 else "")
            else:
                return units[number // 100] + "ຮ້ອຍ" + "ແລະໜຶ່ງ"
        else:
            return units[number // 100] + "ຮ້ອຍ" + ("" + number_to_words(number % 100) if number % 100 != 0 else "")
    elif 1000 <= number < 1000000:
        # Handle the case where the last digit is 1
        if number % 10 == 1:
            # Check if the last two digits are "01"
            if number % 100 == 1:
                return number_to_words(number // 1000) + "ພັນ" + ("" + number_to_words(number % 1000) if number % 1000 != 1 else "ແລະໜຶ່ງ")
            elif (number % 100) // 10 != 0:
                return number_to_words(number // 1000) + "ພັນ" + ("" + number_to_words(number % 1000) if number % 1000 != 0 else "")
            else:
                return number_to_words(number // 1000) + "ພັນ" + "ແລະໜຶ່ງ"
        else:
            return number_to_words(number // 1000) + "ພັນ" + ("" + number_to_words(number % 1000) if number % 1000 != 0 else "")
    elif 1000000 <= number < 1000000000:
        # Handle the case where the last digit is 1
        if number % 10 == 1:
            # Check if the last two digits are "01"
            if number % 100 == 1:
                return number_to_words(number // 1000000) + "ລ້ານ" + ("" + number_to_words(number % 1000000) if number % 1000000 != 1 else "ແລະໜຶ່ງ")
            elif (number % 100) // 10 != 0:
                return number_to_words(number // 1000000) + "ລ້ານ" + ("" + number_to_words(number % 1000000) if number % 1000000 != 0 else "")
            else:
                return number_to_words(number // 1000000) + "ລ້ານ" + "ແລະໜຶ່ງ"
        else:
            return number_to_words(number // 1000000) + "ລ້ານ" + ("" + number_to_words(number % 1000000) if number % 1000000 != 0 else "")
    elif 1000000000 <= number < 1000000000000:
        # Handle the case where the last digit is 1
        if number % 10 == 1:
            # Check if the last two digits are "01"
            if number % 100 == 1:
                return number_to_words(number // 1000000000) + "ຕື້" + ("" + number_to_words(number % 1000000000) if number % 1000000000 != 1 else "ແລະໜຶ່ງ")
            elif (number % 100) // 10 != 0:
                return number_to_words(number // 1000000000) + "ຕື້" + ("" + number_to_words(number % 1000000000) if number % 1000000000 != 0 else "")
            else:
                return number_to_words(number // 1000000000) + "ຕື້" + "ແລະໜຶ່ງ"
        else:
            return number_to_words(number // 1000000000) + "ຕື້" + ("" + number_to_words(number % 1000000000) if number % 1000000000 != 0 else "")
    else:
        return "Number out of range"

@app.route('/number-to-words', methods=['POST'])
def convert_number_to_words():
    data = request.get_json()
    number = data.get('number')
    
    if number is None:
        return jsonify({"error": "Please provide a number"}), 400
    
    try:
        number = int(number)
    except ValueError:
        return jsonify({"error": "Invalid number provided"}), 400
    
    if number < 0 or number >= 1000000000000:
        return jsonify({"error": "Number out of range. Please provide a number between 0 and 999,999,999,999"}), 400
    
    words = number_to_words(number)
    return jsonify({"number": number, "words": words})

if __name__ == '__main__':
    app.run(debug=True)