
# Function to determine the appropriate dtype for a column
import os
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import dask.dataframe as dd

def determine_dtype(column):
    dtype = column.dtype

    if np.issubdtype(dtype, np.integer):

        min_value = column.min()

        max_value = column.max()

        if min_value >= 0:

            if max_value <= np.iinfo(np.uint8).max:

                return 'uint8'

            elif max_value <= np.iinfo(np.uint16).max:

                return 'uint16'

            elif max_value <= np.iinfo(np.uint32).max:

                return 'uint32'

            elif max_value <= np.iinfo(np.uint64).max:

                return 'uint64'

        return dtype

    elif np.issubdtype(dtype, np.floating):

        min_value = column.min()

        max_value = column.max()

        if min_value >= 0:

            if max_value <= np.finfo(np.float16).max:

                return 'float16'

            elif max_value <= np.finfo(np.float32).max:

                return 'float32'

            elif max_value <= np.finfo(np.float64).max:

                return 'float64'

            elif max_value <= np.finfo(np.float128).max:

                return 'float128'

        return dtype

    elif dtype == 'object' or dtype == 'string':

        return 'object'

    elif dtype == 'bool':

        return 'bool'

    else:

        return dtype


# Function to convert a Dask DataFrame to Pandas DataFrame and set data types

def dask_convert_and_set_dtype(df, max_workers):
    # Convert Dask DataFrame to Pandas DataFrame

    df_pandas = df.compute()

    # Iterate through columns and set the desired data type

    for col in df_pandas.columns:
        df_pandas[col] = df_pandas[col].astype(determine_dtype(df_pandas[col]))

    return df_pandas


# Function to print DataFrame size in MB

def print_dataframe_size(df, label):
    memory_usage_mb = df.memory_usage(deep=True).sum() / (1024 ** 2)

    print(f"{label} DataFrame Size: {memory_usage_mb:.2f} MB")


# Function to perform data type conversion with Dask

def perform_dask_data_conversion(df):
    ddf = dd.from_pandas(df, npartitions=os.cpu_count())

    max_workers_with_dask = os.cpu_count()

    df_with_dask = dask_convert_and_set_dtype(ddf.copy(), max_workers_with_dask)

    print_dataframe_size(df_with_dask, "Initial (With Dask)")

    return df_with_dask

# You can now use the 'result_df' Pandas DataFrame in your code.

def df_reduce_size(df):
    try:
        print_dataframe_size(df,"pandas")
        result_df = perform_dask_data_conversion(df)
        return result_df
    except Exception as e:
        return df
