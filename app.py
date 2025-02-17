from flask import Flask, request, render_template
import openai
import config

app = Flask(__name__)

client = openai.OpenAI(api_key=config.API_KEY)

@app.route('/', methods=["GET", "POST"])
def index():
    explanation = None
    fixed_code = None

    if request.method == "POST":
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

    return render_template('index.html', explanation=explanation, fixed_code=fixed_code)

if __name__ == "__main__":
    app.run(debug=True)
