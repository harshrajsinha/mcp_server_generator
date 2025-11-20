from MongoDBHandler import clsMongoDB
import pandas as pd

config = {}

config["hostname"] = 'host:port/?authSource=Scikiqdb'
config["dbuser"] = 'username'
config["pwd"] = 'password'
# config["port"] = 60801
config["dbType"] = "MONGODB"
config["dbname"] = "myAppDatabase"


handle = clsMongoDB(config)

mylist = [
  { "emp_id": 1, "name": "John", "address": "Highway 37"},
  { "emp_id": 2, "name": "Peter", "address": "Lowstreet 27"},
  { "emp_id": 3, "name": "Amy", "address": "Apple st 652"},
  { "emp_id": 4, "name": "Hannah", "address": "Mountain 21"},
  { "emp_id": 5, "name": "Michael", "address": "Valley 345"},
  { "emp_id": 6, "name": "Sandy", "address": "Ocean blvd 2"},
  { "emp_id": 7, "name": "Betty", "address": "Green Grass 1"},
  { "emp_id": 8, "name": "Richard", "address": "Sky st 331"},
  { "emp_id": 9, "name": "Susan", "address": "One way 98"},
  { "emp_id": 10, "name": "Vicky", "address": "Yellow Garden 2"},
  { "emp_id": 11, "name": "Ben", "address": "Park Lane 38"},
  { "emp_id": 12, "name": "William", "address": "Central st 954"},
  { "emp_id": 13, "name": "Chuck", "address": "Main Road 989"},
  { "emp_id": 14, "name": "Viola", "address": "Sideway 1633"}
]

df = pd.DataFrame(mylist)

print(df)

# qry = """select aws_set_config('aws_region', 'ap-south-1'); \
# select aws_set_config('aws_secret', 'secret_key'); \
# select aws_set_config('awsemp_id', 'access_id'); \
# qry = """SELECT S3EXPORT( * USING PARAMETERS url='s3://clientharsh/userdata_test.parquet') OVER(PARTITION BEST) from "client89"."userdata1.parquet" ; """
print("--------------")
print(handle.testConnection())
print("--------------")
# print(handle.getTableDetails('Preauth'))
# print(handle.get_all_tables())
import pdb; pdb.set_trace()
# print(handle.executeInsertUpdate("testwriteDF1", df))
print("--------------")

filter = {'emp_id': 1}
print(handle.readTable("testwriteDF1", limit=None, filter=filter))
# print(handle.getColumnsProfile('BSAD'))

