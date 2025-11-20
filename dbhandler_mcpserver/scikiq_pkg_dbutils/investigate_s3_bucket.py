#!/usr/bin/env python3
"""
S3 Bucket Investigation Script for DuckDB

This script will check what files are actually in your S3 bucket
to help diagnose the DuckDB table scanning issue.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import sys

def investigate_s3_bucket():
    """Investigate the contents of your S3 bucket"""
    
    # S3 configuration from your config.ini
    bucket_name = "allcargo"
    region_name = "ap-south-1"
    access_key = ""
    secret_key = ""
    
    print("🔍 Investigating S3 bucket contents for DuckDB compatibility...")
    print(f"📦 Bucket: {bucket_name}")
    print(f"🌍 Region: {region_name}")
    print(f"🔑 Access Key: {access_key[:10]}...")
    
    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            region_name=region_name,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        print("\n✅ S3 client created successfully")
        
        # Test bucket access
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print("✅ Bucket access confirmed")
        except ClientError as e:
            print(f"❌ Bucket access failed: {e}")
            return False
        
        # List top-level contents
        print(f"\n📂 Top-level contents in bucket '{bucket_name}':")
        
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Delimiter='/'
            )
            
            # Show folders (CommonPrefixes)
            if 'CommonPrefixes' in response:
                print("\n📁 Folders (potential DuckDB tables):")
                for folder in response['CommonPrefixes']:
                    folder_name = folder['Prefix'].rstrip('/')
                    print(f"   - {folder_name}/")
                    
                    # Investigate the Book.orc folder specifically
                    if folder_name == 'Book.orc':
                        investigate_book_orc_folder(s3_client, bucket_name)
            
            # Show files at root level
            if 'Contents' in response:
                print("\n📄 Files at root level:")
                for obj in response['Contents']:
                    if not obj['Key'].endswith('/'):  # Skip folder markers
                        print(f"   - {obj['Key']} ({obj['Size']} bytes)")
                        
        except ClientError as e:
            print(f"❌ Failed to list bucket contents: {e}")
            return False
            
        return True
        
    except NoCredentialsError:
        print("❌ AWS credentials not found or invalid")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def investigate_book_orc_folder(s3_client, bucket_name):
    """Investigate the contents of the Book.orc folder"""
    print(f"\n🔍 Investigating Book.orc/ folder contents:")
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix='Book.orc/',
            MaxKeys=10  # Limit to first 10 files for investigation
        )
        
        if 'Contents' not in response:
            print("   ⚠️  Folder appears to be empty or contains no files")
            return
            
        files_found = []
        total_size = 0
        
        for obj in response['Contents']:
            # Skip the folder itself
            if obj['Key'] != 'Book.orc/':
                file_name = obj['Key']
                file_size = obj['Size']
                total_size += file_size
                
                # Detect file format
                extension = file_name.lower().split('.')[-1] if '.' in file_name else 'no-extension'
                
                files_found.append({
                    'name': file_name,
                    'size': file_size,
                    'extension': extension
                })
                
        if not files_found:
            print("   ⚠️  No actual files found in Book.orc/ folder")
            return
            
        print(f"   📊 Found {len(files_found)} files (Total size: {total_size:,} bytes)")
        
        # Analyze file types
        extensions = {}
        for file_info in files_found:
            ext = file_info['extension']
            if ext not in extensions:
                extensions[ext] = {'count': 0, 'total_size': 0}
            extensions[ext]['count'] += 1
            extensions[ext]['total_size'] += file_info['size']
        
        print("\n   📋 File type analysis:")
        for ext, info in extensions.items():
            print(f"      - .{ext}: {info['count']} files, {info['total_size']:,} bytes")
            
        # DuckDB compatibility check
        print("\n   🎯 DuckDB compatibility analysis:")
        duckdb_supported = {'parquet', 'csv', 'json', 'jsonl', 'ndjson'}
        duckdb_unsupported = {'orc', 'avro'}
        
        for ext in extensions.keys():
            if ext in duckdb_supported:
                print(f"      ✅ .{ext} files: Natively supported by DuckDB")
            elif ext in duckdb_unsupported:
                print(f"      ❌ .{ext} files: NOT supported by DuckDB")
            else:
                print(f"      ❓ .{ext} files: Unknown compatibility")
        
        # Show first few files as examples
        print("\n   📄 Sample files:")
        for i, file_info in enumerate(files_found[:5]):
            print(f"      {i+1}. {file_info['name']} ({file_info['size']:,} bytes)")
        
        if len(files_found) > 5:
            print(f"      ... and {len(files_found) - 5} more files")
            
    except Exception as e:
        print(f"   ❌ Failed to investigate folder: {e}")

def provide_recommendations():
    """Provide recommendations based on findings"""
    print("\n" + "="*60)
    print("📝 RECOMMENDATIONS FOR DUCKDB INTEGRATION")
    print("="*60)
    
    print("""
🎯 Based on the investigation, here are the next steps:

1. **If files are ORC format:**
   - DuckDB doesn't natively support ORC files
   - Consider converting ORC to Parquet using tools like:
     * Apache Spark: spark.read.orc().write.parquet()
     * pandas: pd.read_orc().to_parquet()
     * AWS Glue: Create ETL job to convert formats

2. **If files are Parquet/CSV/JSON:**
   - Files should work with DuckDB
   - Update the folder query to use correct file extension
   - Example: s3://allcargo/Book.orc/*.parquet

3. **DuckDB Query Fixes:**
   - Use read_parquet('s3://bucket/folder/*.parquet') for Parquet
   - Use read_csv_auto('s3://bucket/folder/*.csv') for CSV  
   - Use read_json_auto('s3://bucket/folder/*.json') for JSON

4. **Test Query Examples:**
   ```sql
   -- For Parquet files:
   SELECT * FROM read_parquet('s3://allcargo/Book.orc/*.parquet') LIMIT 5;
   
   -- For CSV files:
   SELECT * FROM read_csv_auto('s3://allcargo/Book.orc/*.csv') LIMIT 5;
   ```

5. **Alternative Solutions:**
   - Rename folder to match content: Book.orc/ → Book/ 
   - Create views for easier access
   - Use DuckDB's auto-detection: SELECT * FROM 's3://allcargo/Book.orc/*'
""")

if __name__ == "__main__":
    print("S3 Bucket Investigation for DuckDB Integration")
    print("=" * 50)
    
    success = investigate_s3_bucket()
    
    if success:
        provide_recommendations()
        print("\\n🎉 Investigation complete! Check the recommendations above.")
    else:
        print("\\n❌ Investigation failed. Please check your AWS credentials and permissions.")
    
    sys.exit(0 if success else 1)