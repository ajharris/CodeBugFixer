from flask import Flask, request, render_template, jsonify, url_for
import openai
import config
import hashlib
import sqlite3
import stripe

app = Flask(__name__)

client = openai.OpenAI(api_key=config.API_KEY)
stripe.api_key = config.STRIPE_TEST_KEY

def initialize_database():
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute(
        '''CREATE TABLE IF NOT EXISTS users (fingerprint text primary key, usage_counter int)'''
    )
    conn.commit()
    conn.close()

def get_fingerprint():
    browser = request.user_agent.browser
    version = request.user_agent.version and float(
        request.user_agent.version.split(".")[0])
    platform = request.user_agent.platform
    string = f"{browser}:{version}:{platform}"
    fingerprint = hashlib.sha256(string.encode("utf-8")).hexdigest()
    return fingerprint

def get_usage_counter(fingerprint):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    result = c.execute('SELECT usage_counter FROM users WHERE fingerprint=?', [fingerprint]).fetchone()
    conn.close()
    if result is None:
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (fingerprint, usage_counter) VALUES (?, 0)', [fingerprint])
        conn.commit()
        conn.close()
        return 0
    else:
        return result[0]
    
def update_usage_counter(fingerprint, usage_counter):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute('UPDATE users SET usage_counter=? WHERE fingerprint=?', [usage_counter, fingerprint])
    conn.commit()
    conn.close()

@app.route('/', methods=["GET", "POST"])
def index():
    initialize_database()
    fingerprint = get_fingerprint()
    usage_counter = get_usage_counter(fingerprint)
    explanation = None
    fixed_code = None

    if request.method == "POST":
        if usage_counter > 3:
            return render_template("payments.html")
        code = request.form["code"]
        error = request.form["error"]

        model_engine = "gpt-3.5-turbo"

        # Get explanation of the error
        explanation_completions = client.chat.completions.create(
            model=model_engine,
            messages=[
                {"role": "system", "content": "You are an expert programmer."},
                {"role": "user", "content": f"Explain the error in this code without fixing it:\n\n{code}\n\nError:\n\n{error}"}
            ],
            max_tokens=1024,
            temperature=0.2,
        )

        explanation = explanation_completions.choices[0].message.content.strip()

        # Get fixed version of the code
        fixed_code_completions = client.chat.completions.create(
            model=model_engine,
            messages=[
                {"role": "system", "content": "You are an expert programmer."},
                {"role": "user", "content": f"Fix this code:\n\n{code}\n\nError:\n\n{error}\n\nRespond only with the fixed code."}
            ],
            max_tokens=1024,
            temperature=0.2,
        )

        fixed_code = fixed_code_completions.choices[0].message.content.strip()

        usage_counter += 1
        update_usage_counter(fingerprint, usage_counter)

    return render_template('index.html', explanation=explanation, fixed_code=fixed_code)

@app.route("/charge", methods=["POST"])
def charge():
    amount = int(request.form["amount"]) 
    plan = str(request.form["plan"])
    customer = stripe.Customer.create(
        email=request.form["stripeEmail"],
        source=request.form["stripeToken"]
    )
    charge = stripe.PaymentIntent.create(
        customer=customer.id,
        amount=amount,
        currency="usd",
        description="App Charge"
    )
    return render_template("charge.html", amount=amount, plan=plan)

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.get_json()
        plan = data['plan']
        amount = data['amount']

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'{plan.capitalize()} Plan Subscription',
                    },
                    'unit_amount': amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payment_success', _external=True),
            cancel_url=url_for('payment_cancel', _external=True),
        )

        return jsonify(id=session.id)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/payment-success')
def payment_success():
    return render_template('payment_success.html')

@app.route('/payment-cancel')
def payment_cancel():
    return render_template('payment_cancel.html')

if __name__ == "__main__":
    app.run(debug=True)
