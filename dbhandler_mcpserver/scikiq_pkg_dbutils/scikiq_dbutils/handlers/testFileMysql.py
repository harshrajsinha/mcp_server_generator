from MySqlHandler import clsMySqlDB
import random
import string
import pandas as pd

config = {}

config["hostname"] = 'localhost'
config["dbname"] = ""
config["dbuser"] = ''
config["pwd"] = ''
config["dbType"] = "MYSQL"
config["port"] = 3306

handle = clsMySqlDB(config)

table_name = 'signup'
_filter = None


#df = handle.getColumnsProfile(table_name, with_min_max=False, filter=_filter) ## PASS
# Function to generate random string
def random_string(length):
    return ''.join(random.choices(string.ascii_letters, k=length))

# Number of dummy records to create
num_records = 100

# Generate dummy data
data = {
    'id1': range(1, num_records + 1),
    'name1': [random_string(8) for _ in range(num_records)],
    'email1': [f"{random_string(6)}@example.com" for _ in range(num_records)],
    'password1': [random_string(12) for _ in range(num_records)]
}

# Create DataFrame


df = pd.DataFrame(data)
#df = handle.getColumnsProfile(table_name, with_min_max=False, filter=_filter) ## PASS

# Insert data into the table
df = handle.executeInsertUpdate(table_name, df, if_exists='replace', chunksize=1000)
print(df)

