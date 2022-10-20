from flask import Flask
from confluent_kafka import Producer
import socket

app = Flask('click_api')

# TODO: setup .dockerignore, json

test_json = "{\"lender_id\": \"1103\",\"loan_purpose\": \"debt_consolidation\",\"credit\":" \
            " \"poor\",\"annual_income\": \"24000.0\",\"apr\":\"199.0\"}"

"""test function"""
@app.route("/")
def test_status():
    return "200 OK"

@app.route("/current_model")
def get_current_model():
    kafka_conf = {"bootstrap.servers": "kafka-service:9092", "client.id": socket.gethostname(), 'session.timeout.ms': 30000}
    producer = Producer(kafka_conf)
    producer.produce("requests", key="prediction-req", value=test_json)
    producer.produce("requests", key="test-key", value="fuck kafka")
    # to serve delivery reports
    producer.poll()
    # to send request
    producer.flush()
    return 'test message sent'

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)