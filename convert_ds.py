from flask import Flask, request, jsonify

app = Flask(__name__)

def number_to_words(number):
    units = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    teens = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", 
             "seventeen", "eighteen", "nineteen"]
    tens = ["", "ten", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", 
            "eighty", "ninety"]
    
    if number == 0:
        return "zero"
    elif number < 10:
        return units[number]
    elif 10 <= number < 20:
        return teens[number - 10]
    elif 20 <= number < 100:
        return tens[number // 10] + (" " + number_to_words(number % 10) if number % 10 != 0 else "")
    elif 100 <= number < 1000:
        return units[number // 100] + " hundred" + (" " + number_to_words(number % 100) if number % 100 != 0 else "")
    elif 1000 <= number < 1000000:
        return number_to_words(number // 1000) + " thousand" + (" " + number_to_words(number % 1000) if number % 1000 != 0 else "")
    elif 1000000 <= number < 1000000000:
        return number_to_words(number // 1000000) + " million" + (" " + number_to_words(number % 1000000) if number % 1000000 != 0 else "")
    elif 1000000000 <= number < 1000000000000:
        return number_to_words(number // 1000000000) + " billion" + (" " + number_to_words(number % 1000000000) if number % 1000000000 != 0 else "")
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