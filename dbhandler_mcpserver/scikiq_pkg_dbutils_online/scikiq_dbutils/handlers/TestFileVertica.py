from VerticaHandler import clsVerticaDB
from DBFactory import clsDBHandler
from scikiq_utils.globalfunction import encodeData
#import pandas as pd

import timeit
import sys
import psutil
import os
import polars as pl
import pandas as pd

def cleanup_dataframe(df, framework='pandas'):
    """
    Clean up DataFrame and free memory.
    
    Args:
        df: DataFrame (either pandas or polars)
        framework: str, either 'pandas' or 'polars'
    """
    import gc
    
    def cleanup_pandas(df):
        # Delete all references to the dataframe
        for col in df.columns:
            df[col] = None
        df.drop(df.index, inplace=True)
        df.drop(df.columns, axis=1, inplace=True)
        
        # Clear all references
        del df
        
        # Force garbage collection
        gc.collect()
        
    def cleanup_polars():
        
        # Force garbage collection
        gc.collect()
    
    try:
        if framework.lower() == 'pandas':
            cleanup_pandas(df)
        elif framework.lower() == 'polars':
            cleanup_polars()
        else:
            raise ValueError(f"Unsupported framework: {framework}. Use 'pandas' or 'polars'.")
            
    except Exception as e:
        print(f"Error cleaning up DataFrame: {str(e)}")

def get_memory_usage(variable=None):
    """
    Get memory usage of a variable or current Python process.
    Specifically handles Polars DataFrame memory calculation.
    
    Args:
        variable: Optional variable to check memory usage
        
    Returns:
        dict: Memory usage information including:
            - process_memory: Total RAM used by the Python process
            - object_memory: Memory used by the specific variable
            - detailed_memory: Detailed memory breakdown for Polars DataFrames
    """
    
    def sizeof_fmt(num):
        """Format size in bytes to human readable."""
        try:
            num = float(num)  # Ensure we have a number
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if abs(num) < 1024:
                    return f"{num:3.2f} {unit}"
                num /= 1024.0
        except (TypeError, ValueError) as e:
            return f"Error formatting size: {str(e)}"
    
    try:
        process = psutil.Process(os.getpid())
        memory_info = {
            'process_memory': sizeof_fmt(process.memory_info().rss)
        }
        
        if variable is not None:
            if isinstance(variable, pl.DataFrame):
                try:
                    # Get total memory size of the DataFrame
                    total_bytes = variable.estimated_size()  # Call the method
                    memory_info['object_memory'] = sizeof_fmt(total_bytes)
                    
                    # Get detailed column-wise memory usage
                    column_sizes = {}
                    for col_name in variable.columns:
                        try:
                            col_size = variable.select(pl.col(col_name)).estimated_size()  # Call the method
                            column_sizes[col_name] = sizeof_fmt(col_size)
                        except Exception as e:
                            column_sizes[col_name] = f"Error: {str(e)}"
                    
                    memory_info['detailed_memory'] = {
                        'total_bytes': total_bytes,
                        'total_formatted': sizeof_fmt(total_bytes),
                        'columns': column_sizes,
                        'num_rows': variable.shape[0],
                        'num_columns': variable.shape[1]
                    }
                    
                except Exception as e:
                    memory_info['error'] = f"Error calculating Polars DataFrame size: {str(e)}"
                
            elif isinstance(variable, pd.DataFrame):
                try:
                    memory_usage = variable.memory_usage(deep=True)
                    total_bytes = memory_usage.sum()
                    memory_info['object_memory'] = sizeof_fmt(total_bytes)
                    
                    # Get detailed column-wise memory usage
                    column_sizes = {col: sizeof_fmt(size) for col, size in memory_usage.items()}
                    memory_info['detailed_memory'] = {
                        'total_bytes': total_bytes,
                        'total_formatted': sizeof_fmt(total_bytes),
                        'columns': column_sizes,
                        'num_rows': variable.shape[0],
                        'num_columns': variable.shape[1]
                    }
                except Exception as e:
                    memory_info['error'] = f"Error calculating Pandas DataFrame size: {str(e)}"
                
            else:
                # For other types, use sys.getsizeof
                try:
                    memory_info['object_memory'] = sizeof_fmt(sys.getsizeof(variable))
                except Exception as e:
                    memory_info['error'] = f"Error calculating object size: {str(e)}"
        
        return memory_info
    
    except Exception as e:
        return {'error': str(e)}

def get_polars_df_info(df):
    """
    Get comprehensive information about a Polars DataFrame.
    
    Args:
        df: polars.DataFrame - The DataFrame to analyze
        
    Returns:
        dict: Dictionary containing DataFrame statistics and information
    """
    import polars as pl
    from datetime import datetime
    import sys

    def sizeof_fmt(num_bytes):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(num_bytes) < 1024:
                return f"{num_bytes:3.2f} {unit}"
            num_bytes /= 1024
            
    def get_column_details(df):
        """Get detailed information about each column"""
        column_info = []
        for col in df.columns:
            try:
                col_series = df[col]
                col_dtype = col_series.dtype
                
                # Basic column stats
                col_stats = {
                    'name': col,
                    'dtype': str(col_dtype),
                    'null_count': col_series.null_count(),
                    'null_percentage': round((col_series.null_count() / len(df)) * 100, 2),
                    'memory_usage': sizeof_fmt(df.get_column(col).estimated_size())
                }
                
                # Calculate unique values based on data type
                try:
                    if isinstance(col_dtype, pl.Decimal):
                        # Convert decimal to float for n_unique
                        col_stats['n_unique'] = col_series.cast(pl.Float64).n_unique()
                    else:
                        col_stats['n_unique'] = col_series.n_unique()
                except Exception as e:
                    col_stats['n_unique'] = None
                    print(f"Warning: Could not calculate unique values for column {col}: {str(e)}")
                
                # Get min/max for numeric and temporal columns
                if isinstance(col_dtype, (pl.Int8, pl.Int16, pl.Int32, pl.Int64, 
                                       pl.Float32, pl.Float64, pl.Decimal,
                                       pl.Date, pl.Datetime)):
                    try:
                        col_stats['min'] = col_series.min()
                        col_stats['max'] = col_series.max()
                    except Exception as e:
                        col_stats['min'] = None
                        col_stats['max'] = None
                        print(f"Warning: Could not calculate min/max for column {col}: {str(e)}")
                    
                # Get additional string column statistics
                if isinstance(col_dtype, pl.String):
                    try:
                        # Remove null values
                        non_null_values = df.filter(df[col].is_not_null())
                        if len(non_null_values) > 0:
                            # Calculate string lengths
                            lengths = non_null_values.get_column(col).str.lengths()
                            col_stats['min_length'] = lengths.min()
                            col_stats['max_length'] = lengths.max()
                            col_stats['avg_length'] = round(float(lengths.mean()), 2)
                    except Exception as e:
                        print(f"Warning: Could not calculate string metrics for column {col}: {str(e)}")
                
                column_info.append(col_stats)
                
            except Exception as e:
                print(f"Warning: Error processing column {col}: {str(e)}")
                column_info.append({
                    'name': col,
                    'dtype': str(df[col].dtype),
                    'error': str(e)
                })
                
        return column_info

    try:
        # Calculate basic DataFrame metrics
        total_null_cells = sum(df[col].null_count() for col in df.columns)
        total_cells = len(df) * len(df.columns)
        completeness = round((1 - total_null_cells / total_cells) * 100, 2) if total_cells > 0 else 100
        total_size = df.estimated_size()

        # Create info dictionary
        info = {
            'general': {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'row_count': len(df),
                'column_count': len(df.columns),
                'total_elements': total_cells,
                'dtypes': {str(col): str(dtype) for col, dtype in zip(df.columns, df.dtypes)}
            },
            'memory': {
                'total_size': sizeof_fmt(total_size),
                'size_in_bytes': total_size,
                'size_in_mb': round(total_size / (1024 * 1024), 2),
                'size_in_gb': round(total_size / (1024 * 1024 * 1024), 4)
            },
            'columns': get_column_details(df),
            'data_quality': {
                'total_null_cells': total_null_cells,
                'completeness_percentage': completeness,
                'duplicate_rows': len(df) - df.unique().height if len(df) > 0 else 0,
                'columns_with_nulls': [col for col in df.columns if df[col].null_count() > 0]
            }
        }
        
        # Calculate percentage of memory used by each column
        for col_info in info['columns']:
            col_size = df.get_column(col_info['name']).estimated_size()
            col_info['memory_percentage'] = round((col_size / total_size) * 100, 2)
        
        return info

    except Exception as e:
        import traceback
        return {
            'error': f"Error analyzing DataFrame: {str(e)}",
            'traceback': traceback.format_exc()
        }

def print_df_info(df_info):
    """
    Print DataFrame information in a formatted way.
    
    Args:
        df_info: dict - The output from get_polars_df_info()
    """
    try:
        if 'error' in df_info:
            print("\n=== Error in DataFrame Analysis ===")
            print(f"Error: {df_info['error']}")
            print(f"Traceback:\n{df_info['traceback']}")
            return

        print("\n=== DataFrame Overview ===")
        print(f"Timestamp: {df_info['general']['timestamp']}")
        print(f"Rows: {df_info['general']['row_count']:,}")
        print(f"Columns: {df_info['general']['column_count']}")
        print(f"Total Elements: {df_info['general']['total_elements']:,}")
        
        print("\n=== Memory Usage ===")
        print(f"Total Size: {df_info['memory']['total_size']}")
        print(f"Size in MB: {df_info['memory']['size_in_mb']} MB")
        print(f"Size in GB: {df_info['memory']['size_in_gb']} GB")
        
        print("\n=== Data Quality ===")
        print(f"Data Completeness: {df_info['data_quality']['completeness_percentage']}%")
        print(f"Duplicate Rows: {df_info['data_quality']['duplicate_rows']:,}")
        print(f"Total Null Cells: {df_info['data_quality']['total_null_cells']:,}")
        
        print("\n=== Column Details ===")
        for col in df_info['columns']:
            print(f"\n{col['name']}:")
            print(f"  Type: {col['dtype']}")
            if 'n_unique' in col and col['n_unique'] is not None:
                print(f"  Unique Values: {col['n_unique']:,}")
            print(f"  Null Count: {col['null_count']:,} ({col['null_percentage']}%)")
            print(f"  Memory Usage: {col['memory_usage']} ({col['memory_percentage']}% of total)")
            
            if 'min' in col and col['min'] is not None:
                print(f"  Min: {col['min']}")
                print(f"  Max: {col['max']}")
                
            if 'min_length' in col:
                print(f"  String Length (min/avg/max): {col['min_length']}/{col['avg_length']}/{col['max_length']}")
            
            if 'error' in col:
                print(f"  Error: {col['error']}")
        
        print("\n=== Columns with Nulls ===")
        null_cols = df_info['data_quality']['columns_with_nulls']
        if null_cols:
            print(", ".join(null_cols))
        else:
            print("No columns with null values")

    except KeyError as e:
        print(f"Error: Missing key in DataFrame info: {str(e)}")
    except Exception as e:
        print(f"Error printing DataFrame info: {str(e)}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")

config = {}


## EFS Dev SCIKIQ
config["hostname"] = 'host'
config["dbuser"] = 'user'
config["dbpassword"] = encodeData('pwd')
config["port"] = 5433
config["dbType"] = "VERTICA"
config["dbname"] = "dbname"
config["schema"] = "schema"

handle = clsDBHandler().getInstanceByConfig(config)

print(handle.get_all_tables())


start_time = timeit.default_timer()
# df, timing = handle.executeQuery("SELECT * FROM prd_stg.F0911", 200000, True, True, 20000, True)
## WITH PROFILE
# df, timing = handle.executeQuery("SELECT * FROM EFS_DEV.tb_Fin_Txn_All_Currency_YTD_Actual", 200000, True, True, 20000, True)
## WITHOUT PROFILE

# polars dataframe
# df= handle.executeQuery("SELECT * FROM EFS_DEV.tb_Fin_Txn_All_Currency_YTD_Actual", 1000000, True, False, 5000)
# Time taken to fetch data:  110.49765589996241
# Time taken to fetch data:  95.37089459999697 2nd optimization
# Dataframe shape:  (1000000, 51)
# 'process_memory': '2.09 GB', 'object_memory': '711.69 MB'

## OLD FUNCTION pandas dataframe
# df = handle.executeQueryOld("SELECT * FROM EFS_DEV.tb_Fin_Txn_All_Currency_YTD_Actual", 1000000, True)
# Time taken to fetch data:  74.16365329996916
# Dataframe shape:  (1000000, 51)
# 'process_memory': '3.23 GB', 'object_memory': '2.58 GB',

# print("Time taken to fetch data: ", timeit.default_timer() - start_time)
# print("Dataframe shape: ", df.shape)
# print("Dataframe columns: ", df.columns)
# # print("Timing: ", timing)
# print(get_memory_usage(df))

# print(type(df))

# print(cleanup_dataframe(df, "polars"))

# df_info = get_polars_df_info(df)

# Print the information in a formatted way
# print_df_info(df_info)

# print(df_info)

# Or access specific information
# print(f"Memory usage: {df_info['memory']['estimated_size']}")
# print(f"Total rows: {df_info['general']['row_count']:,}")

# qry = """select aws_set_config('aws_region', 'ap-south-1'); \
# select aws_set_config('aws_secret', 'secret_key'); \
# select aws_set_config('aws_id', 'access_id'); \
# qry = """SELECT S3EXPORT( * USING PARAMETERS url='s3://clientharsh/userdata_test.parquet') OVER(PARTITION BEST) from "client89"."userdata1.parquet" ; """

# print(handle.get_all_tables())

# print(handle.getColumnsProfile('BSAD'))

# ------------------------------------------------------------------------------------

# print(handle.getTableRelationships(table_name='OrderDetails_child2',bi_directional =True))

# Customers_parent

#     table_name        col_name         ref_table_name       ref_col_name
#   Orders_child1   CustomerID_child1  Customers_parent     CustomerID_parent


# Orders_child1

#        table_name              col_name              ref_table_name       ref_col_name
#      Orders_child1          CustomerID_child1       Customers_parent     CustomerID_parent
#   OrderDetails_child2       OrderID_OrderDetails     Orders_child1           OrderID


# OrderDetails_child2

#        table_name              col_name          ref_table_name   ref_col_name
#   OrderDetails_child2     OrderID_OrderDetails    Orders_child1      OrderID

# ------------------------------------------------------------------------------------


# ------------------------------------------------------------------------------------

# print(handle.getTableRelationships(table_name='OrderDetails_child2',bi_directional =False))

# Customers_parent


# Orders_child1

#    table_name        col_name         ref_table_name       ref_col_name
#   Orders_child1  CustomerID_child1  Customers_parent     CustomerID_parent



# OrderDetails_child2
#        table_name           col_name          ref_table_name    ref_col_name
#   OrderDetails_child2  OrderID_OrderDetails    Orders_child1      OrderID


# ------------------------------------------------------------------------------------
