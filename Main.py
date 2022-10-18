from pyspark.sql import SparkSession
from Model import OfferLR
import time, datetime

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

# TODO: configure subscription to kafka
# init custom model objects for below demo
retrain_lr = OfferLR(spark=spark)
batch_lr = OfferLR(spark=spark)

# for a full retrain
retrain_res = retrain_lr.pull_data().prep_data().fit_or_load(reg_param=0.5, elastic_net_param=0.0).transform()
test = retrain_lr.get_test()
retrain_res.show(truncate=False)

start = time.time()

# for batch predictions from a saved model
batch_lr.set_test(test)
batch_res = batch_lr.fit_or_load(saved=True).transform()
batch_res.show(truncate=False)

print("--- Completed in %s ---" % datetime.timedelta(seconds=time.time() - start)) if start is not None else print('Start was None!')