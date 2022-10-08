from flask import Flask
app = Flask('test_api')

"""test function"""
@app.route("/")
def index():
    return "Hello, world!"

