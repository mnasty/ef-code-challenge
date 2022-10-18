spark-submit \
--deploy-mode cluster \
--master k8s://https://127.0.0.1:52306 \
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
--name lr-model \
local:///app/Main.py
