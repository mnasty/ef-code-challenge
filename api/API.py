from flask import Flask
app = Flask('click_api')

# TODO: setup .dockerignore, json

"""test function"""
@app.route("/")
def test_status():
    return "200 OK"

@app.route("/current_model")
def get_current_model():
    return "200 OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)