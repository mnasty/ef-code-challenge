from pyspark.sql import SparkSession
from pyspark.sql.types import StructField, StructType, LongType, StringType, DoubleType
import pyspark.sql.functions as f
from Model import OfferLR
import time, datetime

# # init spark (local only) ->
# spark = SparkSession.builder \
#     .master('local[*]') \
#     .config('spark.driver.memory', '8g') \
#     .config('spark.sql.execution.arrow.pyspark.enabled', 'true') \
#     .appName('lr-model') \
#     .getOrCreate()
#
# # for a full retrain
# retrain_lr = OfferLR(spark=spark)
# retrain_res = retrain_lr.pull_data().prep_data() #.fit_or_load(reg_param=0.5, elastic_net_param=0.0).transform()
# retrain_res.get_current_data().show(truncate=False)

# init spark (k8s only) ->
spark = SparkSession.builder \
    .appName('lr-model') \
    .getOrCreate()

# prevent overflowing kafka logs
spark.sparkContext.setLogLevel('WARN')

KAFKA_SERVER = "kafka-service:9092"

# test_schema = StructType([
#     StructField("lender_id", LongType(), True),
#     StructField("loan_purpose", StringType(), True),
#     StructField("credit", StringType(), True),
#     StructField("annual_income", DoubleType(), True),
#     StructField("apr", DoubleType(), True)
# ])

test_schema = StructType([
    StructField("lender_id", StringType(), True),
    StructField("loan_purpose", StringType(), True),
    StructField("credit", StringType(), True),
    StructField("annual_income", StringType(), True),
    StructField("apr", StringType(), True)
])

# subscribe to requests topic, open data stream
print('Request Stream:')
request_stream = spark \
  .readStream \
  .format("kafka") \
  .option("kafka.bootstrap.servers", KAFKA_SERVER) \
  .option("subscribe", "requests") \
  .option("startingOffsets", "latest") \
  .load().selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")

print('Stream Writer:')
stream_writer = request_stream.writeStream.format('console').option("truncate", "false")
stream_writer.start()

# for prediction endpoint requests only
print('Prediction Stream 1:')
prediction_stream = request_stream.filter(f.col('key') == 'prediction-req')
prediction_stream.writeStream.format('console').option("truncate", "false").start()
# current_mdl_stream = request_stream.filter(f.col('key') == 'current-mdl-req')
# assignment_stream = request_stream.filter(f.col('key') == 'assignment-req')

# extract JSON
print('Prediction Stream 2:')
prediction_stream = prediction_stream.select(f.from_json(f.col("value"), test_schema).alias("raw"))
prediction_stream.writeStream.format('console').option("truncate", "false").start()

# construct test df
print('Test Stream:')
test_stream = prediction_stream.select("raw.*")
test_stream.writeStream.format('console').option("truncate", "false").start()

print('Model:')
# init model object
lr_model = OfferLR(spark=spark, saved=True)
# for up to n predictions from a saved model
lr_model.set_current_data(test_stream)
test_stream.writeStream.format('console').option("truncate", "false").start()
# execute model
res_stream = lr_model.prep_data().fit_or_load().transform()

if res_stream is not None:
    print('Result Stream:')
    res_stream.writeStream.format('console').option("truncate", "false").start()
    stream_writer.start().awaitTermination()
else:
    print('Empty DataFrame:')
    stream_writer.start().awaitTermination()

#  |-- rawPrediction: vector (nullable = true)
#  |-- probability: vector (nullable = true)
#  |-- prediction: double (nullable = false)

# pred_res.select("prediction") \
#         .writeStream.trigger(processingTime="10 seconds") \
#         .outputMode("complete") \
#         .format("kafka") \
#         .option("topic", "prediction-res") \
#         .option("kafka.bootstrap.servers", KAFKA_SERVER) \
#         .start().awaitTermination()

# start = time.time()
# print("--- Completed in %s ---" % datetime.timedelta(seconds=time.time() - start)) if start is not None else print('Start was None!')