from flask import Flask, jsonify, request

app = Flask(__name__)

# 🔹 Calculator UI at root
@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Calculator</title>
    </head>
    <body>
        <h2>Simple Calculator Test</h2>

        <input type="number" id="a" placeholder="Enter first number">
        <input type="number" id="b" placeholder="Enter second number">
        <br><br>

        <button onclick="calculate('add')">Add</button>
        <button onclick="calculate('sub')">Subtract</button>
        <button onclick="calculate('mul')">Multiply</button>
        <button onclick="calculate('div')">Divide</button>

        <h3 id="result"></h3>

        <script>
            function calculate(op) {
                let a = document.getElementById('a').value;
                let b = document.getElementById('b').value;

                fetch(`/calc?op=${op}&a=${a}&b=${b}`)
                .then(res => res.json())
                .then(data => {
                    if (data.result !== undefined) {
                        document.getElementById('result').innerText = "Result: " + data.result;
                    } else {
                        document.getElementById('result').innerText = "Error: " + data.error;
                    }
                });
            }
        </script>
    </body>
    </html>
    '''

# Health check
@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200


# 🔹 Calculator API (same as before)
@app.route('/calc')
def calculate():
    try:
        op = request.args.get('op')
        a = float(request.args.get('a'))
        b = float(request.args.get('b'))

        if op == 'add':
            result = a + b
        elif op == 'sub':
            result = a - b
        elif op == 'mul':
            result = a * b
        elif op == 'div':
            if b == 0:
                return jsonify({"error": "Division by zero"}), 400
            result = a / b
        else:
            return jsonify({"error": "Invalid operation"}), 400

        return jsonify({
            "operation": op,
            "a": a,
            "b": b,
            "result": result
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
