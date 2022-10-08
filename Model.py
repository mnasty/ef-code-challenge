import pyspark.sql.functions as f
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler, StandardScaler
from pyspark.ml.classification import LogisticRegression, LogisticRegressionModel
from pyspark.ml import Pipeline

import pandas as pd
from sqlalchemy import create_engine

# TODO: add log statements and ensure pythonic formatting
"""finish documenting this class"""
class OfferLR:

    def __init__(self, spark):
        self.spark = spark
        self.current_data = None
        self.train = None
        self.test = None
        self.lr_model = None

    # getters and setters for those params that could be modified directly
    def get_current_data(self):
        return self.current_data

    def get_train(self):
        return self.current_data

    def set_train(self, train):
        self.train = train

    def get_test(self):
        return self.test

    def set_test(self, test):
        self.test = test

    def pull_data(self):
        # TODO: reassign uri to kubernetes virtual network IP
        # create engine to direct pandas to the features database
        engine = create_engine('postgresql://postgres:password@localhost:5432/postgres')

        # define query and join conditions to generate train set
        q = "SELECT COALESCE(features.ds_clicks.offer_id, features.ds_offers.offer_id) AS offer_id, " \
            "COALESCE(features.ds_leads.lead_uuid, features.ds_offers.lead_uuid) AS lead_uuid, " \
            "features.ds_offers.lender_id, features.ds_leads.requested, features.ds_leads.loan_purpose, " \
            "features.ds_leads.credit, features.ds_leads.annual_income, features.ds_offers.apr, " \
            "features.ds_clicks.clicked_at FROM features.ds_offers " \
            "LEFT OUTER JOIN features.ds_clicks ON (features.ds_clicks.offer_id = features.ds_offers.offer_id) " \
            "LEFT OUTER JOIN features.ds_leads ON (features.ds_leads.lead_uuid = features.ds_offers.lead_uuid)"

        # execute query from local database
        join_data = pd.read_sql(q, engine)
        self.current_data = self.spark.createDataFrame(join_data)

        return self

    def prep_data(self):
        # generate a target column based on if a timestamp was present or not, clean up old column
        raw_data = self.current_data.withColumn('is_clicked',
                f.when(f.col('clicked_at').isNull(), f.lit(0.0)).otherwise(f.lit(1.0))).drop(f.col("clicked_at"))

        # features with expected high correlation: lender_id, loan_purpose, credit, annual_income, apr | target: clicked_at
        # one hot encodings only for non-ordinals: lender_id, loan_purpose, credit
        # categorical encodings for ordinals after sort: annual_income, apr

        # define string indexer to get categorical values
        si_cat = StringIndexer(stringOrderType="frequencyDesc").setInputCols(["lender_id", "loan_purpose", "credit"]) \
            .setOutputCols(["lender_id_si", "loan_purpose_si", "credit_si"]).setHandleInvalid('keep')

        # define string indexer to get categorical values for items with linear relationship
        si_lin = StringIndexer(stringOrderType="alphabetAsc").setInputCols(['annual_income', 'apr']) \
            .setOutputCols(['annual_income_si', 'apr_si']).setHandleInvalid('keep')

        # define one hot encoder to package non-linear categorical values into vectors for model consumption
        oh_encoder = OneHotEncoder().setInputCols(si_cat.getOutputCols()) \
            .setOutputCols(["lender_id_enc", "loan_purpose_enc", "credit_enc"])

        # define vector assembler to combine all features into a single dense vector for model consumption
        vec_assembler = VectorAssembler(outputCol="features") \
            .setInputCols(
            ["lender_id_enc", "annual_income_si", "apr_si", "loan_purpose_enc", "credit_enc"]).setHandleInvalid("keep")

        # define standard scaler to avoid modeling inaccuracies from continuous features with large deviations
        std_scaler = StandardScaler(inputCol=vec_assembler.getOutputCol(), outputCol="scaled_feat")

        # wrap all defined stages in pipeline object
        preprocess_pipeline = Pipeline(stages=[si_cat, si_lin, oh_encoder, vec_assembler, std_scaler])
        # apply to data
        self.current_data = preprocess_pipeline.fit(raw_data).transform(raw_data)

        return self

    def fit_or_load(self, saved=False, reg_param=0.1, elastic_net_param=1.0):
        mdl_path = 'models/lr_model_' + str(reg_param) + '_' + str(elastic_net_param)
        if saved:
            print('Loading Saved Model..')
            self.lr_model = LogisticRegressionModel.load(mdl_path)
        else:
            # get train test split
            self.train, self.test = self.current_data.randomSplit([0.9, 0.1], seed=999)
            # instantiate instance of logistic regression
            multi_lr = LogisticRegression(regParam=reg_param, elasticNetParam=elastic_net_param, family="multinomial",
                                          featuresCol="scaled_feat", labelCol="is_clicked")

            self.lr_model = multi_lr.fit(self.train)
            print('Exporting Model..')
            self.lr_model.write().overwrite().save(mdl_path)

        return self

    def transform(self):
        # fetch predictions in batch
        results = self.lr_model.transform(self.test)
        # TODO; for API stream ?
        # fetch predictions per request
        # lr_model.predict(test0.head().features)

        # drop unneeded cols from processing
        results = results.drop(*["lender_id_si", "loan_purpose_si", "credit_si", "annual_income_si", "apr_si",
                                 "lender_id_enc", "loan_purpose_enc", "credit_enc", "features", "scaled_feat"])

        # TODO: screw around with class imbalance if you have extra time
        # results = results.filter('is_clicked > 0.0')
        return results

