from pyspark.sql import SparkSession
from pyspark.sql.types import StructField, StructType, LongType, StringType, DoubleType, BooleanType
import pyspark.sql.functions as f
from Model import OfferLR

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

# init model object
lr_model = OfferLR(spark=spark, saved=True)

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

# filter by request type
prediction_stream = request_stream.filter(f.col('key') == 'prediction-req')
prediction_stream.writeStream.format('console').option("truncate", "false").start()

current_mdl_stream = request_stream.filter(f.col('key') == 'current-mdl-req')
current_mdl_stream.writeStream.format('console').option("truncate", "false").start()

assignment_stream = request_stream.filter(f.col('key') == 'assignment-req')
assignment_stream.writeStream.format('console').option("truncate", "false").start()

# --------- /assignment -------
# define incoming request schema
assign_schema = StructType([StructField("version", StringType(), True)])

# extract JSON
assignment_stream = assignment_stream.select(f.from_json(f.col("value"), assign_schema).alias("raw"))
assignment_stream.writeStream.format('console').option("truncate", "false").start()

# inflate prediction dataframe from JSON
assignment_stream = assignment_stream.select("raw.*")
assignment_stream.writeStream.format('console').option("truncate", "false").start()

@f.udf(returnType=BooleanType())
def assign_mdl_path(version_col):
    if version_col == '0.1_1.0' or version_col == '0.5_0.0':
        open('version.txt', 'w').write(version_col)
        return True
    else:
        return False

assignment_stream = assignment_stream.withColumn('set', assign_mdl_path(f.col('version')))
assignment_stream.writeStream.format('console').option("truncate", "false").start()

# extract prediction results and deflate to json
assignment_stream = assignment_stream.withColumn("value", f.to_json(f.struct("*")).cast("string"))
assignment_stream.writeStream.format('console').option("truncate", "false").start()

# subscribe to responses topic and push
assignment_stream.select("value") \
    .writeStream \
    .outputMode("append") \
    .format("kafka") \
    .option("topic", "responses") \
    .option("kafka.bootstrap.servers", KAFKA_SERVER) \
    .start()

# --------- /current_model -------
version = lr_model.fetch_local_version() if lr_model.fetch_local_version() is not None else 'version.txt missing'
current_mdl_stream = current_mdl_stream.withColumn('version', f.lit(version)).select(f.col('version'))

# extract prediction results and deflate to json
current_mdl_stream = current_mdl_stream.withColumn("value", f.to_json(f.struct("*")).cast("string"))
current_mdl_stream.writeStream.format('console').option("truncate", "false").start()

# subscribe to responses topic and push
current_mdl_stream.select("value") \
    .writeStream \
    .outputMode("append") \
    .format("kafka") \
    .option("topic", "responses") \
    .option("kafka.bootstrap.servers", KAFKA_SERVER) \
    .start()

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
prediction_stream = prediction_stream.select(f.from_json(f.col("value"), test_schema).alias("raw"))
prediction_stream.writeStream.format('console').option("truncate", "false").start()

# inflate prediction dataframe from JSON
test_stream = prediction_stream.select("raw.*")
test_stream.writeStream.format('console').option("truncate", "false").start()

# for up to n predictions in a batch from a saved model
lr_model.set_current_data(test_stream)
# execute model predictions
res_stream = lr_model.prep_data().fit_or_load().transform()

if res_stream is not None:
    # extract prediction results and deflate to json
    res_stream = res_stream.select(f.col('rawPrediction'), f.col('probability'), f.col('prediction'))\
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
