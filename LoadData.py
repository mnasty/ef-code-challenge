import re
import pandas as pd
from sqlalchemy import create_engine, DDL

# class not appropriate for single method process

# define extensible list of parquet files
parquets = ['res/ds_clicks.parquet.gzip', 'res/ds_leads.parquet.gzip', 'res/ds_offers.parquet.gzip']
# create stack to hold table data tuples
tables = []
# regex pattern to extract table names
name_pattern = '(\/{1})(.*)(\.p)'

# read in parquets
for parquet in parquets:
    # fetch table names
    name = re.search(name_pattern, parquet, re.IGNORECASE).group(2)
    # add data and name as tuple to stack
    tables.append((pd.read_parquet(parquet), name))

# create engine to direct pandas to the features database
engine = create_engine('postgresql://postgres:password@localhost:5432/postgres')

# load sql file
with open('res/init_db.sql', 'r') as file:
    sql = file.read()

# execute ddl
with engine.connect() as con:
    con.execute(DDL(sql))

# execute data insertion for each table
for table_tup in tables:
    print("Loading", table_tup[1])
                                                                # can be 'append'
    table_tup[0].to_sql(table_tup[1], engine, schema='features', if_exists='replace')

print("Done!")
