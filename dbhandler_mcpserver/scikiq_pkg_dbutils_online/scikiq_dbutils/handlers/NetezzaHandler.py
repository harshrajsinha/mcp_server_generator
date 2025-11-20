# Required packages
import nzpy
import pandas as pd
from scikiq_dbutils.handlers.DBConnection import clsDBConnection  # abstract base class

class clsNetezzaDB(clsDBConnection):
    """
    Netezza handler using nzpy.
    """

    def __init__(self, config):
        # Expect keys: hostname, port, dbname, dbuser, pwd
        self.host = config.get("hostname")
        self.port = config.get("port", 5480)
        self.dbname = config.get("dbname")
        self.user = config.get("dbuser")
        self.password = config.get("pwd")
        self.connection = None
        self.cursor = None
        self.schema = config.get("schema")
        self.db_type = "NETEZZA"
        if "resource_key" in config:
            self.resource_key = config["resource_key"]
        else:
            self.resource_key = None

    def connect(self):
        self.connection = nzpy.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.dbname,
        )
        self.cursor = self.connection.cursor()

    def close(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.connection:
            self.connection.close()
            self.connection = None

    def testConnection(self):
        resp = {}
        try:
            self.connect()
            self.close()
            resp['error'] = 0
            resp['msg'] = 'Successfully connected to Netezza.'
        except Exception as e:
            resp['error'] = 1
            resp['msg'] = str(e)
        super(clsNetezzaDB, self).callConnectionAudit(resp)
        return resp

    def executeQuery(self, query, limit=None, manage_connection=True, use_polars=False, batch_size=100000, profile=False):
        # limit/connection/audit logic modeled after SqlServerHandler
        try:
            if manage_connection:
                self.connect()

            if limit is not None:
                # Netezza supports LIMIT at the end of the query
                query = query.rstrip(';')
                query = f"{query} LIMIT {limit}"

            self.cursor.execute(query)
            columns = [desc[0] for desc in self.cursor.description]
            results = self.cursor.fetchall()
            df = pd.DataFrame(results, columns=columns)

            if manage_connection:
                self.close()
            return df
        except Exception as e:
            if manage_connection:
                self.close()
            raise

    def executeSql(self, query, manage_connection=True):
        try:
            if manage_connection:
                self.connect()
            self.cursor.execute(query)
            if self.connection:
                self.connection.commit()
            if manage_connection:
                self.close()
            return {"status": 1, "msg": "Success"}
        except Exception as e:
            if manage_connection:
                self.close()
            return {"status": 0, "msg": str(e)}

    def get_all_tables(self, search=None, type=None, limit=None, include_view=False):
        # Netezza doesn't use INFORMATION_SCHEMA, but _V_TABLE
        query = "SELECT TABLENAME, TABLETYPE FROM _V_TABLE WHERE OWNER <> 'SYSTEM'"
        if search:
            query += f" AND TABLENAME LIKE '%{search}%'"
        if type:
            if type.upper() == "VIEW":
                query += " AND TABLETYPE = 'V'"
            else:
                query += " AND TABLETYPE = 'T'"
        if self.schema:
            query += f" AND SCHEMA = '{self.schema}'"
        query += " ORDER BY TABLENAME"
        return self.executeQuery(query, limit=limit, manage_connection=True)

    def getTableColumns(self, tablename, type=""):
        # Use _V_RELATION_COLUMN for column metadata
        query = f"""
        SELECT COLUMNNAME FROM _V_RELATION_COLUMN 
        WHERE TABLENAME = '{tablename}'
        """
        if self.schema:
            query += f" AND SCHEMA = '{self.schema}'"
        query += " ORDER BY ORDINALPOSITION"
        return self.executeQuery(query, manage_connection=True)

    def getTableColumnsDetails(self, tbl_name, **others):
        # Rich column metadata for a table
        query = f"""
        SELECT
            COLUMNNAME as "COLUMN_NAME",
            COLUMNTYPE as "DATA_TYPE",
            LENGTH as "CHARACTER_MAXIMUM_LENGTH",
            CASE WHEN NULLABLE = 'Y' THEN 'YES' ELSE 'NO' END as "IS_NULLABLE",
            ORDINALPOSITION as "ORDINAL_POSITION"
        FROM _V_RELATION_COLUMN
        WHERE TABLENAME = '{tbl_name}'
        """
        if self.schema:
            query += f" AND SCHEMA = '{self.schema}'"
        query += " ORDER BY ORDINALPOSITION"
        df = self.executeQuery(query, manage_connection=True)
        return df.to_dict(orient="records")

    # Example: read a table as DataFrame
    def readTable(self, tbl_name, limit=None, **others):
        full_table_name = f"{self.schema}.{tbl_name}" if self.schema else tbl_name
        query = f"SELECT * FROM {full_table_name}"
        df = self.executeQuery(query, limit=limit, manage_connection=True)
        return {"df": df, "df_text": None}
    
    def createTable(self, tbl_name, col_defs, schema=None, drop_if_exists=False):
        sch = schema or self.schema
        tbl = f"{sch}.{tbl_name}" if sch else tbl_name
        if drop_if_exists:
            self.dropTable(tbl)
        query = f"CREATE TABLE {tbl} ({col_defs})"
        return self.executeSql(query)

    def dropTable(self, tbl_name, schema=None):
        sch = schema or self.schema
        tbl = f"{sch}.{tbl_name}" if sch else tbl_name
        query = f"DROP TABLE IF EXISTS {tbl}"
        return self.executeSql(query)

    def insertDataFrame(self, tbl_name, df: pd.DataFrame, schema=None):
        sch = schema or self.schema
        tbl = f"{sch}.{tbl_name}" if sch else tbl_name
        columns = ','.join(df.columns)
        placeholders = ','.join(['%s'] * len(df.columns))
        insert_sql = f"INSERT INTO {tbl} ({columns}) VALUES ({placeholders})"
        self.connect()
        for row in df.itertuples(index=False, name=None):
            self.cursor.execute(insert_sql, row)
        self.connection.commit()
        self.close()
        return {"status": 1, "msg": "Data inserted"}

    def createView(self, view_name, select_sql, schema=None, replace=False):
        sch = schema or self.schema
        vname = f"{sch}.{view_name}" if sch else view_name
        if replace:
            self.dropView(vname)
        query = f"CREATE VIEW {vname} AS {select_sql}"
        return self.executeSql(query)

    def dropView(self, view_name, schema=None):
        sch = schema or self.schema
        vname = f"{sch}.{view_name}" if sch else view_name
        query = f"DROP VIEW IF EXISTS {vname}"
        return self.executeSql(query)

    def getMergeQuery(self, tbl_name, keys, data_cols):
        # Netezza supports MERGE, but with simpler syntax
        keys_str = ' AND '.join([f'target.{k}=source.{k}' for k in keys])
        set_str = ', '.join([f'target.{c}=source.{c}' for c in data_cols if c not in keys])
        insert_cols = ', '.join(keys + data_cols)
        values_cols = ', '.join([f'source.{c}' for c in keys + data_cols])
        query = f'''
MERGE INTO {tbl_name} AS target
USING (VALUES ({" ,".join(["%s"]*len(keys+data_cols))})) AS source ({insert_cols})
ON {keys_str}
WHEN MATCHED THEN UPDATE SET {set_str}
WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({values_cols})
'''
        return query

    def truncateTable(self, tbl_name, schema=None):
        sch = schema or self.schema
        tbl = f"{sch}.{tbl_name}" if sch else tbl_name
        query = f"TRUNCATE TABLE {tbl}"
        return self.executeSql(query)

    def getPrimaryKeys(self, tbl_name, schema=None):
        sch = schema or self.schema
        query = f'''SELECT COLUMNNAME 
FROM _V_PRIMARY_KEY 
WHERE TABLENAME = '{tbl_name}' '''
        if sch:
            query += f"AND SCHEMA = '{sch}'"
        result = self.executeQuery(query)
        return result['COLUMNNAME'].tolist() if not result.empty else []

    def getAllSchemas(self):
        query = "SELECT SCHEMA FROM _V_SCHEMA ORDER BY SCHEMA"
        df = self.executeQuery(query)
        return df['SCHEMA'].tolist() if not df.empty else []    