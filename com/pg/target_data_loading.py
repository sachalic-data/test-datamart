from pyspark.sql import SparkSession
from pyspark.sql.types import StringType
from pyspark.sql.functions import current_date
import yaml
import os.path

import utils.aws_utils as ut


def fn_uuid():
    uid = uuid.uuid1()
    return uid

if __name__ == '__main__':

    current_dir = os.path.abspath(os.path.dirname(__file__))
    app_config_path = os.path.abspath(current_dir + "/../../" + "application.yml")
    app_secrets_path = os.path.abspath(current_dir + "/../../" + ".secrets")

    conf = open(app_config_path)
    app_conf = yaml.load(conf, Loader=yaml.FullLoader)
    secret = open(app_secrets_path)
    app_secret = yaml.load(secret, Loader=yaml.FullLoader)

    # Create the SparkSession
    spark = SparkSession \
        .builder \
        .appName("Read ingestion enterprise applications") \
        .config("spark.mongodb.input.uri", app_secret["mongodb_config"]["uri"])\
        .getOrCreate()
    spark.sparkContext.setLogLevel('ERROR')
    fn_uuid = spark.udf \
        .register("fn_uuid", fn_uuid, StringType())
    tgt_list = app_conf['target_list']

    for tgt in tgt_list:
        tgt_conf = app_conf[tgt]
        stg_loc = "s3a://" + app_conf["s3_conf"]["s3_bucket"] + "/" + app_conf["s3_conf"]["staging_dir"]
        if tgt == 'REGIS_DIM':
            cp_df = spark.read.parquet(stg_loc + "/" + tgt_conf["source_data"] + "/" + "ins_date=2021-01-27")
            cp_df.createOrReplaceTempView(tgt_conf["source_data"])
            cp_df.show(5, False)

            regis_dim_df = spark.sql("""
                SELECT
                    fn_uuid() AS REGIS_KEY, REGIS_CNSM_ID AS CNSM_ID,REGIS_CTY_CODE AS CTY_CODE,
                    REGIS_ID, REGIS_DATE, REGIS_LTY_ID AS LTY_ID, REGIS_CHANNEL, REGIS_GENDER, REGIS_CITY, INS_TS
                FROM
                    (SELECT
                        DISTINCT REGIS_CNSM_ID, CAST(REGIS_CTY_CODE AS SMALLINT), CAST(REGIS_ID AS INTEGER),
                        REGIS_LTY_ID, REGIS_DATE, REGIS_CHANNEL, REGIS_GENDER, REGIS_CITY, INS_TS
                    FROM
                        CP
                    WHERE
                        CAST(INS_TS AS DATE) = CURRENT_DATE
                    )
                CP""")
            regis_dim_df.show(5, False)


# spark-submit --master yarn --packages "org.apache.hadoop:hadoop-aws:2.7.4" com/pg/target_data_loading.py
