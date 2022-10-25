from flask import Flask, request
from confluent_kafka import Producer, Consumer
import socket

import pandas as pd
from sqlalchemy import create_engine

app = Flask('click_api')

# TODO: additional request format error handling?
def kafka_req_res(key, request, type='GET'):
    def process_err(err):
        # unsubscribe from response topic
        consumer.close()
        # deliver exception
        return 'error: {}'.format(err)

    # init config
    prod_conf = {"bootstrap.servers": "kafka-service:9092", "client.id": socket.gethostname(), 'session.timeout.ms': 30000}
    cons_conf = {"bootstrap.servers": "kafka-service:9092", "client.id": socket.gethostname(), 'session.timeout.ms': 30000,
                 'group.id': 'responses-group-1', 'auto.offset.reset': 'latest'}

    # establish producer and consumer objects
    producer = Producer(prod_conf)
    consumer = Consumer(cons_conf)
    # subscribe to response topic
    consumer.subscribe(["responses"])

    # package request based on declared type
    if type == 'GET':
        producer.produce("requests", key=key, value=key)
    elif type == 'POST':
        producer.produce("requests", key=key, value=request)
    else:
        return process_err('unsupported request type!')

    # send request
    producer.flush()

    timeout = 0
    # process response
    try:
        # wait
        while True:
            # check for response every second
            msg = consumer.poll(1.0)
            # wait until received
            if msg is None:
                # keep track of the seconds that pass
                timeout += 1
                # if the response has taken more than 30 seconds
                if timeout > 30:
                    return process_err('request timed out!')

                continue
            # if dequeue error occurs
            elif msg.error():
                return process_err(msg.error())
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

# base route test function to confirm API status
@app.route("/")
def test_status():
    return "{status: 200 OK}"

# submit prediction requests to kafka for spark stream processing
@app.route("/predictions", methods=['POST'])
def predictions():
    return kafka_req_res(key='prediction-req', type='POST', request=str(request.json))

# assign model version
@app.route("/assignment", methods=['POST'])
def assignment():
    # create set to store valid versions
    valid_versions = {'0.1_1.0', '0.5_0.0'}
    # extract version from request json
    version = request.get_json()['version']
    # if version is valid
    if version in valid_versions:
        # TODO: reassign uri to unique kubernetes virtual network IP for retrain deployments
        # create engine to link to version table
        engine = create_engine('postgresql://postgres:password@10.110.230.221:5432/postgres')
        # assemble table structure
        table = pd.DataFrame([version], columns=['ver'])
        # commit assigned version
        table.to_sql('version', engine, schema='features', if_exists='replace')
        # send confirmation response
        return '{\"version\": {\"0\": ' + version + ', \"set\": \"True\"}'
    else:
        # send invalid response
        return '{\"version\": {\"0\": \"invalid\", \"set\": \"False\"}'

# fetch current model version
@app.route("/current_model")
def current_model():
    # TODO: reassign uri to unique kubernetes virtual network IP for retrain deployments
    # create engine to link to version table
    engine = create_engine('postgresql://postgres:password@10.110.230.221:5432/postgres')
    # get version
    version = pd.read_sql('SELECT ver AS version FROM features.version', engine)
    # convert to JSON and return
    return version.to_json()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)