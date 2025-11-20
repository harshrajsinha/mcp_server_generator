import abc
import logging
from datetime import datetime, date, time
from typing import Any, Dict, List, Optional
from bson.decimal128 import Decimal128


import pymongo
from pymongo import MongoClient

LOGGER = logging.getLogger(__name__)


class Extractor(abc.ABC):
    """
    An extractor extracts record
    """

    @abc.abstractmethod
    def init(self, conf: Dict[str, Any]) -> None:
        pass

    @abc.abstractmethod
    def extract(self) -> Any:
        """
        :return: Provides a record or None if no more to extract
        """
        return None

    def get_scope(self) -> str:
        return 'extractor'


class ColumnMetadata:
    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        data_type: str = '',
        is_nullable: bool = True,
        is_primary_key: bool = False,
        references: Optional[List['ColumnReference']] = None
    ) -> None:
        self.name = name
        self.description = description
        self.data_type = data_type
        self.is_nullable = is_nullable
        self.is_primary_key = is_primary_key
        self.references = references



class ColumnReference:
    def __init__(
        self,
        table_name: str,
        column_name: str,
        on_update: Optional[str] = None,
        on_delete: Optional[str] = None
    ) -> None:
        self.table_name = table_name
        self.column_name = column_name
        self.on_update = on_update
        self.on_delete = on_delete


class IndexMetadata:
    def __init__(self, name: str, key: Dict[str, Any], unique: bool, sparse: bool) -> None:
        self.name = name
        self.key = key
        self.unique = unique
        self.sparse = sparse


class TableMetadata:
    def __init__(
        self,
        database: str,
        cluster: Optional[str],
        schema: Optional[str],
        name: str,
        description: Optional[str],
        columns: List[ColumnMetadata],
        table_type: str = 'Table',
        total_usage: Optional[Any] = None,
        unique_usage: Optional[Any] = None,
        indexes: Optional[List[IndexMetadata]] = None,
        tags: Optional[List[str]] = None,
        last_updated_timestamp: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
        partitions: Optional[List[Dict[str, Any]]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        extras: Optional[Dict[str, Any]] = None,
        is_view: bool = False,
        cdc_enabled: bool = False
    ) -> None:
        self.database = database
        self.cluster = cluster
        self.schema = schema
        self.name = name
        self.description = description
        self.columns = columns
        self.table_type = table_type
        self.total_usage = total_usage
        self.unique_usage = unique_usage
        self.indexes = indexes
        self.tags = tags
        self.last_updated_timestamp = last_updated_timestamp
        self.options = options
        self.partitions = partitions
        self.parameters = parameters
        self.extras = extras
        self.is_view = is_view
        self.cdc_enabled = cdc_enabled


class MongoDBMetadataExtractor(Extractor):
    """
    Extracts MongoDB table and column metadata using the PyMongo library
    """

    def __init__(self, connection_string: str, database: str):
        self._connection_string = connection_string
        self._database = database
        self._client = None
        self._collection_names = []

    def init(self, conf: Dict[str, Any]) -> None:
        self._client = MongoClient(self._connection_string)

        import pdb; pdb.set_trace()
        self._collection_names = self._client[self._database].list_collection_names()

    def extract(self) -> Any:
        if not self._collection_names:
            return None

        import pdb; pdb.set_trace()
        collection_name = self._collection_names.pop(0)
        collection = self._client[self._database][collection_name]

        columns = []

        # Get column names, types, and metadata
        sample_document = collection.find_one()
        for field, field_value in sample_document.items():
            # Additional metadata information (nullable, primary key, references) can be derived as per your requirements
            # Here, placeholders are used
            column_metadata = ColumnMetadata(
                name=field,
                description=None,
                data_type=self.get_data_type(field_value),
                is_nullable=True,
                is_primary_key=False,
                references=None
            )
            columns.append(column_metadata)

        # Get total document count
        doc_count = collection.count_documents({})

        # Get index information
        indexes = []
        for index in collection.list_indexes():
            index_info = IndexMetadata(
                name=index['name'],
                key=index['key'],
                unique=index.get('unique', False),  # Set default value as False if 'unique' key is missing
                sparse=index.get('sparse', False)
            )
            indexes.append(index_info)

        # Get collection statistics
        stats = self._client[self._database].command('collstats', collection_name)

        # Placeholder for partition information
        partitions = None

        # Placeholder for table parameters
        parameters = None

        # Placeholder for extras
        extras = None

        # Create TableMetadata object with enriched metadata
        table_metadata = TableMetadata(
            database=self._database,
            cluster=None,
            schema=None,
            name=collection_name,
            description=stats.get('source', ''),
            columns=columns,
            table_type='Collection',
            total_usage=None,
            unique_usage=None,
            indexes=indexes,
            tags=None,
            last_updated_timestamp=None,
            options=stats,
            partitions=partitions,
            parameters=parameters,
            extras=extras,
            is_view=False,
            cdc_enabled=False  # Placeholder for CDC status, update as per your needs
        )

        # Set the document count as the estimated row count
        table_metadata.total_usage = doc_count

        return table_metadata

    @staticmethod
    def get_data_type(value: Any) -> str:
        if isinstance(value, dict):
            return "Dictionary"
        elif isinstance(value, list):
            return "List"
        elif isinstance(value, int):
            return "Integer"
        elif isinstance(value, float):
            return "Decimal"
        elif isinstance(value, bool):
            return "Boolean"
        elif isinstance(value, str):
            return "String"
        elif isinstance(value, datetime):
            return "DateTime"
        elif isinstance(value, date):
            return "Date"
        elif isinstance(value, time):
            return "Time"
        elif isinstance(value, Decimal128):
            return "Decimal"
        else:
            return "Unknown"

    def get_scope(self) -> str:
            return 'extractor.mongodb_metadata'


# Example usage
connection_string = "mongodb://root:Data9999@103.178.248.128:27017/"
database_name = "local"

extractor = MongoDBMetadataExtractor(connection_string, database_name)
extractor.init({})
table_metadata = extractor.extract()

# Print the metadata
print("Table Metadata:")
print("----------------")
print(f"Database: {table_metadata.database}")
print(f"Cluster: {table_metadata.cluster}")
print(f"Schema: {table_metadata.schema}")
print(f"Name: {table_metadata.name}")
print(f"Description: {table_metadata.description}")

# Print columns
print("Columns:")
for column in table_metadata.columns:
    print("----------------")
    print(f"Name: {column.name}")
    print(f"Description: {column.description}")
    print(f"Data Type: {column.data_type}")
    print(f"Is Nullable: {column.is_nullable}")
    print(f"Is Primary Key: {column.is_primary_key}")
    print(f"References: {column.references}")

print(f"Table Type: {table_metadata.table_type}")
print(f"Total Usage: {table_metadata.total_usage}")
print(f"Unique Usage: {table_metadata.unique_usage}")
# Print indexes
print("Indexes:")
for index in table_metadata.indexes:
    print("----------------")
    print(f"Name: {index.name}")
    print(f"Key: {index.key}")
    print(f"Unique: {index.unique}")
    print(f"Sparse: {index.sparse}")

print(f"Tags: {table_metadata.tags}")
print(f"Last Updated Timestamp: {table_metadata.last_updated_timestamp}")
print(f"Options: {table_metadata.options}")
print(f"Partitions: {table_metadata.partitions}")
print(f"Parameters: {table_metadata.parameters}")
print(f"Extras: {table_metadata.extras}")
print(f"Is View: {table_metadata.is_view}")
print(f"CDC Enabled: {table_metadata.cdc_enabled}")

import random
from pymongo import MongoClient
from ydata_profiling import ProfileReport as YDataProfileReport
import pandas as pd


def run_mongodb_profiling(connection_string: str, database_name: str,
                          output_folder: str, config, sample_size: int = 20000):
    # Connect to MongoDB
    client = MongoClient(connection_string)

    # Get list of collection names in the database
    collection_names = client[database_name].list_collection_names()

    for collection_name in collection_names:
        # Get the document count in the collection
        collection = client[database_name][collection_name]
        document_count = collection.count_documents({})

        # Determine the sample size
        sample_size = min(sample_size, document_count)

        # Generate a random list of indices for sampling
        sample_indices = random.sample(range(document_count), sample_size)

        # Retrieve the sample of data from MongoDB collection
        data = []
        for index in sample_indices:
            document = collection.find().limit(1).skip(index).next()
            data.append(document)

        # Convert data to a pandas DataFrame
        df = pd.DataFrame(data)

        profile = YDataProfileReport(df, config=config)
        # Save profiling report to file
        output_file = f"{output_folder}/{collection_name}.html"
        profile.to_file(output_file)


# Example usage
connection_string = "localhost:27017"
database_name = "testdb"
output_folder = "./profile123"
sample_size = 500
use_ydata = True

config = {
    "title": "MongoDB Collection Profiling",
    "correlations": {
        "compute": False
    },
    "missing_diagrams": {
        "bar": True,
        "matrix": True,
        "heatmap": False,
        "dendrogram": False,
        "regression": False
    },
    "text": {
        "wordcloud": False  # Disable word cloud for text fieldsd
    },
    "interactions": {
        "compute": False

    }
}



from ydata_profiling.config import Settings

# Create the config object
config = Settings(config)


run_mongodb_profiling(connection_string, database_name,
                      output_folder, config, sample_size)
