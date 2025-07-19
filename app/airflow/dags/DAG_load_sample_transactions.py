from __future__ import annotations

import pendulum
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
import polars as pl
import logging
import psycopg2
from typing import Optional
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_csv(file_path: str = "/app/data/local/sample_transactions.csv",min_size_kb: int = 1) -> str:
    """Load CSV file using Polars and validate it"""
    try:
        # Check file exists and size
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        file_size_bytes = os.path.getsize(file_path)
        file_size_kb = file_size_bytes / 1024
        
        if file_size_kb < min_size_kb:
            raise ValueError(f"File too small: {file_size_kb:.2f}KB < {min_size_kb}KB minimum")
        
        # Return a simple status instead of the DataFrame
        logger.info(f"Lightweight CSV validation successful")
        return "CSV loaded successfully"
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        raise

def get_connection() -> Optional[psycopg2.extensions.connection]:
    """Establish connection to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            dbname='airflow',
            user='airflow',
            password='airflow',
            host='postgres',
            port='5432'
        )
        logger.info("Successfully connected to database")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Error connecting to database: {e}")
        raise

def test_connection() -> None:
    """Test database connection"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        logger.info(f"Database version: {version[0]}")
        cursor.close()
        conn.close()
        logger.info("Database connection test successful")
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        raise

def check_table_status() -> None:
    """Check the status of the transactions table"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'transactions'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            logger.info("Table 'transactions' does not exist yet")

            # Create table query with proper data types
            create_table_query = """
            CREATE TABLE IF NOT EXISTS transactions (
                order_id INT PRIMARY KEY,
                user_id INT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                ts TIMESTAMP,
                status VARCHAR(20)
            );
            """
            # Create table
            cursor.execute(create_table_query)
            conn.commit()
            logger.info("Table 'transactions' created successfully")
        else:
            cursor.execute("SELECT COUNT(*) FROM transactions;")
            count = cursor.fetchone()[0]
            if count == 0:
                logger.warning("Table 'transactions' exists but is empty")
            else:
                logger.info(f"Table 'transactions' contains {count} records")
        
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error checking table status: {e}")
        raise

def load_to_postgresql() -> str:
    """Load CSV data to PostgreSQL database"""
    # Load the CSV data
    df = pl.read_csv("/app/data/local/sample_transactions.csv")
    if df is None or df.is_empty():
        raise ValueError("DataFrame is empty or None. Cannot load to database.")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert data
        insert_query = """
        INSERT INTO transactions (order_id, user_id, amount, ts, status)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (order_id) DO NOTHING;
        """
        
        rows_inserted = 0
        for row in df.iter_rows(named=True):
            cursor.execute(insert_query, (
                row['order_id'], 
                row['user_id'], 
                row['amount'], 
                row['ts'], 
                row['status']
            ))
            if cursor.rowcount > 0:
                rows_inserted += 1
        
        conn.commit()
        logger.info(f"Successfully inserted {rows_inserted} new rows")
        
        cursor.close()
        conn.close()
        
        return f"Data loaded successfully: {rows_inserted} new rows inserted"
        
    except Exception as e:
        logger.error(f"Error loading data to PostgreSQL: {e}")
        raise

# Default DAG arguments
default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': pendulum.duration(minutes=5),
}

# Define the DAG
with DAG(
    dag_id="load_sample_transactions",  # Fixed typo: "transation" -> "transactions"
    default_args=default_args,
    description="Load sample transaction data from CSV to PostgreSQL",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    schedule=None,  # Manual trigger only
    tags=["transactions", "etl", "sample_data"],
    max_active_runs=1,  # Ensure only one run at a time
) as dag:
    
    # Task to load and validate CSV
    load_csv_task = PythonOperator(
        task_id="validate_csv",
        python_callable=test_csv,
        doc_md="""
        ## Load CSV Task
        This task test the sample transactions CSV file and validates its size.
        """,
    )

    # Task to test database connection
    test_connection_task = PythonOperator(
        task_id="test_database_connection",
        python_callable=test_connection,  
        doc_md="""
        ## Test Connection Task
        This task verifies that we can connect to the PostgreSQL database.
        """,
    )

    # Task to check table status
    table_status_task = PythonOperator(
        task_id="check_table_status",
        python_callable=check_table_status,  
        doc_md="""
        ## Table Status Task
        This task checks if the transactions table exists and creates 
        the transactions table (if it doesn't exist) .
        """,
    )

    # Task to load data to PostgreSQL
    load_to_postgresql_task = PythonOperator(
        task_id="load_data_to_postgresql",
        python_callable=load_to_postgresql,
        doc_md="""
        ## Load to PostgreSQL Task
        This task loads the CSV data to PostgreSQL.
        """,
    )

    # Define task dependencies
    load_csv_task >> test_connection_task >> table_status_task >> load_to_postgresql_task