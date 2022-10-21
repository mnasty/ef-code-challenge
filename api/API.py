from flask import Flask
from confluent_kafka import Producer, Consumer
import socket

app = Flask('click_api')

# TODO: setup .dockerignore, json

test_json = "{\"lender_id\": \"1103\",\"loan_purpose\": \"debt_consolidation\",\"credit\":" \
            " \"poor\",\"annual_income\": \"24000.0\",\"apr\":\"199.0\"}"

"""test function"""
@app.route("/")
def test_status():
    return "{status: 200 OK}"

@app.route("/prediction")
def get_current_model():
    # init config
    prod_conf = {"bootstrap.servers": "kafka-service:9092", "client.id": socket.gethostname(), 'session.timeout.ms': 30000}
    cons_conf = {"bootstrap.servers": "kafka-service:9092", "client.id": socket.gethostname(), 'session.timeout.ms': 30000,
                 'group.id': 'responses-group-1', 'auto.offset.reset': 'latest'}

    # establish producer and consumer objects
    producer = Producer(prod_conf)
    consumer = Consumer(cons_conf)
    # subscribe to response topic
    consumer.subscribe(["responses"])
    # package request
    producer.produce("requests", key="prediction-req", value=test_json)
    # send request
    producer.flush()

    timeout = 0
    # process response
    try:
        # wait
        while True:
            # check for response every second
            msg = consumer.poll(1.0)
            if msg is None:
                # wait until received
                print("Waiting for response..")
                # keep track of the seconds that pass
                timeout += 1
                # if the response has taken more than 30 seconds
                if timeout > 30:
                    # unsubscribe from response topic
                    consumer.close()
                    # deliver timeout exception
                    return 'error: {}'.format('request timed out!')
                continue
            # if dequeue error occurs
            elif msg.error():
                # log error
                err = 'error: {}'.format(msg.error())
                print(err)
                # unsubscribe from response topic
                consumer.close()
                # deliver response
                return err
            else:
                # when message received
                value = msg.value()
                # unsubscribe from response topic
                consumer.close()
                # deliver response
                return value
    # prevent any exception from causing container failure
    except Exception as e:
        print('error: {}'.format(e))
        pass
    finally:
        # unsubscribe from response topic
        consumer.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)