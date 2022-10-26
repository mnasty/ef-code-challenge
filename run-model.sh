# spark submit script to deploy streaming application on k8 cluster
spark-submit \
--deploy-mode cluster \
--master k8s://https://127.0.0.1:60461 \
--conf spark.kubernetes.namespace=default \
--conf spark.driver.memory=2g \
--conf spark.executor.instances=1 \
--conf spark.executor.cores=1 \
--conf spark.executor.memory=2g \
--conf spark.kubernetes.authenticate.driver.serviceAccountName=spark \
--conf spark.kubernetes.authenticate.serviceAccountName=spark \
--conf spark.executor.instances=1 \
--conf spark.kubernetes.driver.container.image=click-model-env:latest \
--conf spark.kubernetes.executor.container.image=click-model-env:latest \
--conf spark.pyspark.python=python3 \
--conf spark.pyspark.driver.python=python3 \
--conf spark.sql.execution.arrow.pyspark.enabled=true \
--conf spark.sql.streaming.checkpointLocation=/tmp/checkpoints/ \
--packages \
org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,\
org.apache.spark:spark-token-provider-kafka-0-10_2.12:3.3.0,\
org.apache.kafka:kafka-clients:2.8.1,\
com.google.code.findbugs:jsr305:3.0.0,\
org.apache.commons:commons-pool2:2.11.1,\
org.apache.spark:spark-tags_2.12:3.3.0 \
--name lr-model \
local:///app/Main.py


