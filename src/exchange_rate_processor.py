from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import requests
from datetime import datetime
import time

def create_spark_session():
    return SparkSession.builder \
        .appName("ExchangeRateETL") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
        .getOrCreate()

def fetch_exchange_rates():
    """Fetch data from Exchange Rate API"""
    url = "https://v6.exchangerate-api.com/v6/d859a94bdc40c124d4842d22/latest/USD"
    response = requests.get(url)
    data = response.json()
    print(f"API Response: {data['result']}")
    print(f"Total currencies fetched: {len(data['conversion_rates'])}")
    return data

def process_and_save_data(spark, data):
    """Process and save exchange rate data"""
    try:
        # Create rows for DataFrame
        rows = []
        current_time = datetime.now()
        
        # Process each currency rate
        for currency, rate in data['conversion_rates'].items():
            row = {
                'currency': currency,
                'rate': float(rate),
                'timestamp': current_time,
                'date': current_time.date()
            }
            rows.append(row)
        
        # Create DataFrame
        schema = StructType([
            StructField("currency", StringType(), True),
            StructField("rate", DoubleType(), True),
            StructField("timestamp", TimestampType(), True),
            StructField("date", DateType(), True)
        ])
        
        df = spark.createDataFrame(rows, schema)
        
        # Show data yang akan disimpan
        print("\nData yang akan disimpan ke HDFS:")
        df.show(5)
        print(f"Total records: {df.count()}")
        
        # Simpan ke HDFS
        output_path = f"/exchange_rates/batch={current_time.strftime('%Y%m%d_%H%M%S')}"
        
        df.write \
            .mode("overwrite") \
            .format("parquet") \
            .save(output_path)
        
        print(f"\nData berhasil disimpan di: {output_path}")
        
        # Verifikasi data tersimpan
        saved_df = spark.read.parquet(output_path)
        saved_count = saved_df.count()
        print(f"Verifikasi: {saved_count} records tersimpan")
        
        return True
        
    except Exception as e:
        print(f"Error dalam proses dan penyimpanan data: {e}")
        return False

def verify_hdfs_storage():
    """Verifikasi storage HDFS"""
    try:
        from subprocess import check_output
        
        # Cek HDFS directory
        cmd = ["hdfs", "dfs", "-ls", "/exchange_rates"]
        result = check_output(cmd).decode()
        print("\nHDFS Directory Content:")
        print(result)
        
        return True
    except Exception as e:
        print(f"Error verifikasi HDFS: {e}")
        return False

def main():
    print(f"\nStarting Exchange Rate ETL at {datetime.now()}")
    
    try:
        # Create Spark Session
        spark = create_spark_session()
        print("Spark session created successfully")
        
        while True:
            try:
                # Step 1: Fetch Data
                print("\nFetching exchange rates...")
                data = fetch_exchange_rates()
                
                # Step 2: Process & Save Data
                print("\nProcessing and saving data...")
                success = process_and_save_data(spark, data)
                
                if success:
                    print("\nETL cycle completed successfully")
                    # Verify storage
                    verify_hdfs_storage()
                else:
                    print("\nETL cycle failed")
                
                # Wait before next cycle
                wait_time = 3600  # 1 hour
                print(f"\nWaiting {wait_time} seconds before next cycle...")
                time.sleep(wait_time)
                
            except Exception as e:
                print(f"Error in ETL cycle: {e}")
                print("Waiting 5 minutes before retry...")
                time.sleep(300)
                
    except Exception as e:
        print(f"Critical error: {e}")
    finally:
        if 'spark' in locals():
            spark.stop()
            print("Spark session stopped")

if __name__ == "__main__":
    main()