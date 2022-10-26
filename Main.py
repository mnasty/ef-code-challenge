from pyspark.sql import SparkSession
from pyspark.sql.types import StructField, StructType, StringType
import pyspark.sql.functions as f
from Model import OfferLR

# # init spark (local only) ->
# spark = SparkSession.builder \
#     .master('local[*]') \
#     .config('spark.driver.memory', '8g') \
#     .config('spark.sql.execution.arrow.pyspark.enabled', 'true') \
#     .appName('lr-model') \
#     .getOrCreate()

# init spark (k8s only) ->
spark = SparkSession.builder \
    .appName('lr-model') \
    .getOrCreate()

# # for a full retrain
# retrain_lr = OfferLR(spark=spark)
# retrain_res = retrain_lr.pull_data().prep_data() #.fit_or_load(reg_param=0.5, elastic_net_param=0.0).transform()
# retrain_res.get_current_data().show(truncate=False)

# init model objects for each version
# TODO: reassign db_uri to unique kubernetes virtual network IP for retrain deployments
lr_model = OfferLR(spark=spark, db_uri='postgresql://postgres:password@10.101.216.188:5432/postgres', saved=True)

# prevent overflowing kafka logs
spark.sparkContext.setLogLevel('WARN')
# constant for kafka server
KAFKA_SERVER = "kafka-service:9092"

# subscribe to requests topic
request_stream = spark \
  .readStream \
  .format("kafka") \
  .option("kafka.bootstrap.servers", KAFKA_SERVER) \
  .option("subscribe", "requests") \
  .option("startingOffsets", "latest") \
  .load().selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")

# open data stream, preserve object for loopback
stream_writer = request_stream.writeStream.format('console').option("truncate", "false")
stream_writer.start()

# --------- /predictions -------
# define incoming request schema
test_schema = StructType([
    StructField("lender_id", StringType(), True),
    StructField("loan_purpose", StringType(), True),
    StructField("credit", StringType(), True),
    StructField("annual_income", StringType(), True),
    StructField("apr", StringType(), True)
])

# extract JSON
request_stream = request_stream.select(f.from_json(f.col("value"), test_schema).alias("raw"))
request_stream.writeStream.format('console').option("truncate", "false").start()

# inflate prediction dataframe from JSON
test_stream = request_stream.select("raw.*")
test_stream.writeStream.format('console').option("truncate", "false").start()

# for up to n predictions in a batch from a saved model
lr_model.set_current_data(test_stream)
# execute model predictions
res_stream = lr_model.prep_data().fit_or_load().transform()

# if result stream is non-empty
if res_stream is not None:
    # extract prediction results and deflate to json
    res_stream = res_stream.select(f.col('rawPrediction'), f.col('probability'), f.col('prediction')) \
        .withColumn("value", f.to_json(f.struct("*")).cast("string"))
    res_stream.writeStream.format('console').option("truncate", "false").start()

    # subscribe to responses topic and push
    res_stream.select("value") \
        .writeStream \
        .outputMode("append") \
        .format("kafka") \
        .option("topic", "responses") \
        .option("kafka.bootstrap.servers", KAFKA_SERVER) \
        .start().awaitTermination()
else:
    # loopback to beginning of data stream
    stream_writer.start().awaitTermination()

