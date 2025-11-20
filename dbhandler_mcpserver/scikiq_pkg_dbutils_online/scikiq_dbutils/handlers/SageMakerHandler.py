import boto3
import pandas as pd
import io
import json
from datetime import datetime

from scikiq_dbutils.handlers.DBConnection import clsDBConnection

class clsSageMaker(clsDBConnection):
    
    def __init__(self, config):
        self.resource_key = config.get("resource_key")
        self.access_key = config.get('aws_access_key', config.get('access_key'))
        self.secret_access_key = config.get('aws_secret_key', config.get('secret_access_key'))
        self.bucket_name = config['bucket_name']
        self.region = config['region']
        self.connection_type = config.get("connection_type")
        self.role_arn = config.get("role_name")

    def getConnectionType(self):
        if self.connection_type is None:
            return "SR"
        else:
            return self.connection_type

    def connect(self):
        try:
            resp = {}
            resp['resource_call'] = 'connect'
            
            # Example: listing SageMaker notebooks (modify according to your needs)
            self.sagemaker_client = boto3.client(
                'sagemaker',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region
            )            

            # callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected to SageMaker.'
            resp['error'] = 0
            super(clsSageMaker, self).callConnectionAudit(resp)

        except Exception as e:
            # callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsSageMaker, self).callConnectionAudit(resp)
            raise

    def close(self):
        if hasattr(self, 'sagemaker_client'):
            del self.sagemaker_client
        # If there are any additional cleanup steps, add them here

    def update_column_comment(self, tbl_name, col_name, comment, **others):
        return False            

    def testConnection(self):
        try:
            resp = {}
            resp['resource_call'] = 'connect'
            
            # Example: listing SageMaker notebooks (modify according to your needs)
            self.sagemaker_client = boto3.client(
                'sagemaker',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region
            )            
            notebooks = self.sagemaker_client.list_notebook_instances()

            # callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected to SageMaker.'
            resp['error'] = 0
            super(clsSageMaker, self).callConnectionAudit(resp)

        except Exception as e:
            # callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsSageMaker, self).callConnectionAudit(resp)
            raise

    def createView(self, view_name, sql_query):
        pass

    def executeQuery(self, query, limit=None, manage_connection=True, use_polars=False, batch_size=10000, profile=False):
        results = None
        return results

    def executeSql(self, query, value=None, manage_connection=True):
        pass

    def executeInsertUpdate(self, tablename, df, if_exists='replace', chunksize=1000):
        pass

    def get_all_tables(self, search=None, type=None, limit=None, include_view=None):
        self.connect()
        
        try:
            response = self.sagemaker_client.list_feature_groups()
            feature_groups = response.get('FeatureGroupSummaries', [])
            
            results = []
            for fg in feature_groups:
                table_name = fg.get('FeatureGroupName')
                table_type = 'TABLE'  # SageMaker Feature Groups are tables by default
                schema_name = ''  # SageMaker does not provide schema name
                if search and search.lower() not in table_name.lower():
                    continue
                results.append([table_name, table_type, schema_name])
            
            results.sort()
        except Exception as e:
            raise Exception(f"Failed to retrieve feature groups: {str(e)}")
        finally:
            self.close()
        
        return results

    def getAllTablesWithColumns(self, search):
        tables = []
        self.connect()
        
        try:
            feature_groups = self.get_all_tables()
            
            for _, row in feature_groups.iterrows():
                tbl_name = row['FeatureGroupName']
                cols = {
                    "tablename": tbl_name,
                    "columnname": self.getTableColumns(tbl_name)
                }
                tables.append(cols)
        except Exception as e:
            raise Exception(f"Failed to retrieve feature groups with columns: {str(e)}")
        
        self.close()

        return tables

    def getTableColumns(self, tablename):
        df = None        
        col_name = ['COLUMN_NAME', 'DATA_TYPE']        
        self.connect()
        
        try:
            response = self.sagemaker_client.describe_feature_group(FeatureGroupName=tablename)
            feature_definitions = response.get("FeatureDefinitions", [])
            
            data = [{
                'COLUMN_NAME': feature['FeatureName'],
                'DATA_TYPE': feature['FeatureType']
            } for feature in feature_definitions]
            
            df = pd.DataFrame(data, columns=col_name)
        except Exception as e:
            raise Exception(f"Failed to get feature list for {tablename}: {str(e)}")
        
        self.close()   
        
        return df.to_dict(orient="records")  

    def getTableColumnsDetails(self, tbl_name, **others):
        df = None
        col_name = [
            'TABLE_SCHEMA',
            'TABLE_NAME', 
            'COLUMN_NAME', 
            'DATA_TYPE', 
            'DATA_TYPE_LENGTH', 
            'NUMERIC_PRECISION', 
            'IS_NULLABLE', 
            'CHARACTER_MAX_LENGTH', 
            'CHARACTER_MAXIMUM_LENGTH', 
            'NUMERIC_SCALE', 
            'ORDINAL_POSITION',
            'CONVEXIT',
            'COMMENT'
        ]
        
        self.connect()
        
        try:
            response = self.sagemaker_client.describe_feature_group(FeatureGroupName=tbl_name)
            feature_definitions = response.get("FeatureDefinitions", [])
            
            data = [{
                'TABLE_SCHEMA': None, 
                'TABLE_NAME': tbl_name,
                'COLUMN_NAME': feature['FeatureName'],
                'DATA_TYPE': feature['FeatureType'],
                'DATA_TYPE_LENGTH': None,
                'NUMERIC_PRECISION': None,
                'IS_NULLABLE': None,
                'CHARACTER_MAX_LENGTH': None,
                'CHARACTER_MAXIMUM_LENGTH': None,
                'NUMERIC_SCALE': None,
                'ORDINAL_POSITION': index + 1,
                'CONVEXIT': None,
                'COMMENT': None
            } for index, feature in enumerate(feature_definitions)]
            
            df = pd.DataFrame(data, columns=col_name)
        except Exception as e:
            raise Exception(f"Failed to get column details for {tbl_name}: {str(e)}")
        
        self.close()
        
        return df.to_dict(orient="records")  

    def generateQuery(
        self,
        tablename=None,
        columnnames=None,
        limit=None,
        orderby=None,
        filters=None,
        groupby=None,
        joins=None,
        joinCondition=None,
        distinct=0
    ):
        pass

    def create_engine(self):
       pass

    def readTable(self, tbl_name, limit = None, **others):
        results = None
        results_text = None

        res = {}
        res["df"] = results
        res["df_text"] = results_text 
        return res        

    def truncateTable(self, table_name):
        pass

    def generateCreateTableScriptETL(self, tableDetails):
        pass

    def createTable(self, tableDetails, etl=False):
        pass

    def getColumnLOV(self, table_name, col_name):
        pass

    def getColumnsProfile(self, table_name, with_min_max=False, filter=None):
        df_col_dtls = self.getTableColumnsDetails(table_name, sort_on_position=True, type=type)

        '''
            COLUMN_NAME
            DATA_TYPE
            MAX_VAL
            MIN_VAL
            UNQ_VAL
            TOTAL_COUNT
            NULL_CNT
        '''


        columns = ['COLUMN_NAME', 'DATA_TYPE', 'MAX_VAL', 'MIN_VAL', 'UNQ_VAL', 'TOTAL_COUNT', 'NULL_CNT']
        df = None
        
        return df   
    
    def getTableRowCount(self, table_name, filter, params = ''):
        return 0

    def getTableDetails(self, table_name=None, type={}):
        col_name = ['TABLE_SCHEMA', 'TABLE_NAME', 'NO_OF_COLS', 'SIZE_IN_MB', 'NO_OF_ROWS', 'LAST_UPDATED', 'TABLE_TYPE', 'COMMENT']
        df = None
        
        if not table_name:
            return pd.DataFrame(columns=col_name)
        
        try:
            response = self.sagemaker_client.describe_feature_group(FeatureGroupName=table_name)
            
            table_schema = None  # SageMaker does not provide schema name
            no_of_cols = len(response.get('FeatureDefinitions', []))
            table_size = None  # Size is not directly available from SageMaker
            no_of_rows = None  # Number of rows is not directly available
            last_updated = response.get('LastUpdateTime', None)
            table_type = 'FILE'  # Fixed value as per requirement
            comment = response.get('Description', '')
            
            data = [{
                'TABLE_SCHEMA': table_schema,
                'TABLE_NAME': table_name,
                'NO_OF_COLS': no_of_cols,
                'SIZE_IN_MB': table_size,
                'NO_OF_ROWS': no_of_rows,
                'LAST_UPDATED': last_updated,
                'TABLE_TYPE': table_type,
                'COMMENT': comment
            }]
            
            df = pd.DataFrame(data, columns=col_name)
        except Exception as e:
            raise Exception(f"Failed to retrieve table details for {table_name}: {str(e)}")
        
        return df

    def getTableRelationships(self, table_name, bi_directional = False):
        df = df[['table_name', 'col_name', 'ref_table_name', 'ref_type']]        
        return df

    def getDropTableQuery(self, table_name):
        pass

    def dropTable(self, table_name):
        pass

    def getTableIndexDetails(self, tablename):
        pass

    def get_incremental_columns(self, tablename, **others):
        return pd.DataFrame()

    def fetch_delta_columns(self, table_name, **others):
        df = None
        return df
    
    def find_row(self, tbl_name, row, on_condition, manage_connection):
        return False    

    def update_row(self, tbl_name, row, on_condition, matched_mapping, col_details, manage_connection):
        return False

    def insert_row(self, tbl_name, row, non_matched_mapping, col_details, manage_connection):

        '''
            INSERT INTO SCIKIQ_DEV.ORDERS
            (ID, CUSTOMER_ID, PRODUCT_ID, QUANTITY, PRICE, TOTAL_AMOUNT, STORE_ID, CREATED_DATE, CREATED_BY)
            VALUES(0, 0, 0, 0, 0, 0, 0, '', '');        
        '''
        
        return False

    def create_feature_group(self, feature_group_name, record_identifier_feature_name, event_time_feature_name, 
                            features_definition, description=None, offline_store_config=None, 
                            online_store_config=None, role_arn=None):
        """
        Create a SageMaker Feature Group with specified features.
        
        Parameters:
        -----------
        feature_group_name : str
            Name of the feature group to create
        record_identifier_feature_name : str
            Name of the feature that uniquely identifies records in the feature group
        event_time_feature_name : str
            Name of the feature that records the event time for all feature values in the feature group
        features_definition : list
            List of dictionaries defining features, each with 'FeatureName' and 'FeatureType'
        description : str, optional
            Description of the feature group
        offline_store_config : dict, optional
            Configuration for the offline store
        online_store_config : dict, optional
            Configuration for the online store
        role_arn : str, optional
            ARN of the IAM role to use for creating the feature group
            
        Returns:
        --------
        dict
            Response from SageMaker API
        """
        self.connect()
        
        try:
            # Set default offline store config if not provided
            if offline_store_config is None:
                offline_store_config = {
                    'S3StorageConfig': {
                        'S3Uri': f's3://{self.bucket_name}/feature-store/{feature_group_name}/'
                    }
                }
                
            
            # Set default online store config if not provided
            if online_store_config is None:
                online_store_config = {
                    'EnableOnlineStore': True
                }
                
            # Prepare the create feature group request
            feature_group_config = {
                'FeatureGroupName': feature_group_name,
                'RecordIdentifierFeatureName': record_identifier_feature_name,
                'EventTimeFeatureName': event_time_feature_name,
                'FeatureDefinitions': features_definition,
                'OnlineStoreConfig': online_store_config,
                'OfflineStoreConfig': offline_store_config,
                'RoleArn': self.role_arn
            }
            
            # Add optional parameters if provided
            if description:
                feature_group_config['Description'] = description
            
            if role_arn:
                feature_group_config['RoleArn'] = role_arn
                
            # Create the feature group
            response = self.sagemaker_client.create_feature_group(**feature_group_config)
            
            # Wait for feature group creation to complete
            self.sagemaker_client.get_waiter('feature_group_created').wait(
                FeatureGroupName=feature_group_name
            )
            
            return {
                'status': 'success',
                'message': f'Feature group {feature_group_name} created successfully',
                'response': response
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to create feature group: {str(e)}'
            }
        finally:
            self.close()
    
    def write_data_to_feature_group(self, feature_group_name, dataframe, record_identifier_col, 
                                   event_time_col, format='csv', s3_prefix=None):
        """
        Write data to a SageMaker Feature Group by first uploading to S3 and then
        ingesting into the feature store.
        
        Parameters:
        -----------
        feature_group_name : str
            Name of the feature group to write data to
        dataframe : pandas.DataFrame
            DataFrame containing the data to be written
        record_identifier_col : str
            Column name in dataframe that corresponds to the record identifier feature
        event_time_col : str
            Column name in dataframe that corresponds to the event time feature
        format : str, optional (default='csv')
            Format to use for data in S3 ('csv' or 'parquet')
        s3_prefix : str, optional
            Custom S3 prefix to use for the data. If None, uses a default prefix
            
        Returns:
        --------
        dict
            Status of the operation and details
        """
        self.connect()
        
        try:
            # Verify the feature group exists
            try:
                self.sagemaker_client.describe_feature_group(FeatureGroupName=feature_group_name)
            except Exception as e:
                return {
                    'status': 'error',
                    'message': f'Feature group {feature_group_name} does not exist: {str(e)}'
                }
            
            # Format event time column to ISO format if it's not already
            if pd.api.types.is_datetime64_any_dtype(dataframe[event_time_col]):
                dataframe[event_time_col] = dataframe[event_time_col].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Generate a timestamp for the upload
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Determine S3 key
            if s3_prefix is None:
                s3_key = f'feature-store/{feature_group_name}/input/{timestamp}-data'
            else:
                s3_key = f'{s3_prefix.rstrip("/")}/{timestamp}-data'
            
            # Convert DataFrame to the specified format and upload to S3
            if format.lower() == 'csv':
                buffer = io.StringIO()
                dataframe.to_csv(buffer, index=False)
                s3_key += '.csv'
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=buffer.getvalue()
                )
            elif format.lower() == 'parquet':
                buffer = io.BytesIO()
                dataframe.to_parquet(buffer)
                s3_key += '.parquet'
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=buffer.getvalue()
                )
            else:
                return {
                    'status': 'error',
                    'message': f'Unsupported format: {format}. Use "csv" or "parquet".'
                }
            
            # For smaller datasets, directly put records into the feature store
            # For larger datasets, you might want to use a batch ingestion job
            if len(dataframe) <= 100:  # Direct ingestion for small datasets
                success_count = 0
                errors = []
                
                # Process each row and put record
                for _, row in dataframe.iterrows():
                    record = {
                        feature_name: {'StringValue': str(value)} if isinstance(value, (str, datetime)) 
                                     else {'IntegerValue': int(value)} if isinstance(value, int)
                                     else {'FractionalValue': float(value)} if isinstance(value, float)
                                     else {'StringValue': str(value)}
                        for feature_name, value in row.items() if pd.notna(value)
                    }
                    
                    try:
                        self.sagemaker_featurestore_runtime.put_record(
                            FeatureGroupName=feature_group_name,
                            Record=[{'FeatureName': k, 'ValueAsString': str(v)} for k, v in row.items() if pd.notna(v)]
                        )
                        success_count += 1
                    except Exception as e:
                        errors.append(str(e))
                
                return {
                    'status': 'success' if not errors else 'partial',
                    'message': (f'Successfully wrote {success_count} out of {len(dataframe)} records to '
                                f'feature group {feature_group_name}'),
                    'errors': errors if errors else None,
                    's3_location': f's3://{self.bucket_name}/{s3_key}'
                }
            else:
                # Create a metadata file for the feature mapping
                feature_mapping = {col: col for col in dataframe.columns}
                feature_mapping_json = json.dumps(feature_mapping)
                
                mapping_key = f'{s3_key[:-len(format)-1]}-mapping.json'
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=mapping_key,
                    Body=feature_mapping_json
                )
                
                # Start a Sagemaker feature store batch job
                # Note: This requires appropriate role with permissions
                import_job_response = self.sagemaker_client.create_batch_import_job(
                    JobName=f'{feature_group_name}-import-{timestamp}',
                    FeatureGroupName=feature_group_name,
                    RoleArn=self.get_role_arn(),  # You would need to implement this method
                    InputConfig={
                        'S3InputConfig': {
                            'S3Uri': f's3://{self.bucket_name}/{s3_key}',
                            'ResolvedOutputS3Uri': f's3://{self.bucket_name}/feature-store/{feature_group_name}/resolved/'
                        },
                        'DataFormat': format.upper()
                    }
                )
                
                return {
                    'status': 'initiated',
                    'message': f'Batch import job initiated for feature group {feature_group_name}',
                    'job_name': import_job_response.get('JobName'),
                    's3_location': f's3://{self.bucket_name}/{s3_key}'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to write data to feature group: {str(e)}'
            }
        finally:
            self.close()
            
    def get_role_arn(self):
        """
        Helper method to retrieve the role ARN for SageMaker operations.
        This method should be implemented based on your organization's approach to role management.
        """
        # This is a placeholder - you should implement this based on your specific needs
        # For example, you might:
        # 1. Use a role ARN stored in the config
        # 2. Retrieve it from an environment variable
        # 3. Use AWS STS to get the ARN of the current role
        
        # Example implementation:
        iam_client = boto3.client(
            'iam',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region
        )
        
        # Get the caller identity
        sts_client = boto3.client(
            'sts',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region
        )
        caller_identity = sts_client.get_caller_identity()
        
        # If using an IAM role, return its ARN
        if 'assumed-role' in caller_identity['Arn']:
            role_name = caller_identity['Arn'].split('/')[1]
            role_response = iam_client.get_role(RoleName=role_name)
            return role_response['Role']['Arn']
        
        # Fallback to a default role
        return f"arn:aws:iam::{caller_identity['Account']}:role/service-role/AmazonSageMaker-ExecutionRole"