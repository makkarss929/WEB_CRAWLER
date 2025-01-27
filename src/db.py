import logging
import os
import time
import traceback

import ibis
import pandas as pd
from dotenv import load_dotenv, find_dotenv
from pandas.errors import DatabaseError
from psycopg2 import OperationalError, InterfaceError
from psycopg2 import sql

# Load environment variables
load_dotenv(find_dotenv())

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)


class PostgresConnection:
    max_retry_count: int = 10
    retry_delay: int = 2

    def __init__(self):
        self.conn = self._initialize_db_connection()

    def _initialize_db_connection(self):
        try:
            return ibis.postgres.connect(
                user=os.getenv("DATABASE_USER"),  # Default to "admin" if not set
                password=os.getenv("DATABASE_PASSWORD"),  # Default to "admin" if not set
                host=os.getenv("DATABASE_HOST"),  # Default to "postgres" if not set
                port=int(os.getenv("DATABASE_PORT")),  # Default to 5432 if not set
                database=os.getenv("DATABASE_NAME"),  # Default to "ecommerce" if not set
            )
        except Exception as e:
            logging.error("Failed to initialize database connection", exc_info=True)
            return None

    def _execute_sql(self, cursor, query: str, params: str = None):
        retry_count = 0

        while retry_count < self.max_retry_count:
            retry_count += 1
            try:
                cursor.execute(query, params)
                logging.info("Successfully executed query.")
                return
            except (OperationalError, InterfaceError) as e:
                cursor.close()

                logging.error(e)
                logging.error(traceback.format_exc())
                logging.info(f"Retrying connection after {retry_count} attempt/s")

                time.sleep(self.retry_delay ** retry_count)

                self.conn.disconnect()
                self.conn = self._initialize_db_connection()
                cursor = self.conn.con.cursor()
            except Exception as e:
                logging.error("Unhandled exception occurred", exc_info=True)
                raise

        raise Exception(f"Connection Error after {retry_count} attempts")

    def read_sql_query(self, query: str, params: dict = {}) -> pd.DataFrame:
        """Execute a query using pandas read_sql_query and do a retry in case of connection error"""
        retry_count = 0

        logging.info("Executing pandas query")
        while retry_count < self.max_retry_count:
            retry_count += 1

            try:
                df = pd.read_sql_query(query, self.conn.con, params=params)
                logging.info("Successfully executed query")
                return df
            except (InterfaceError, OperationalError, DatabaseError) as e:
                logging.error(e)
                logging.error(traceback.format_exc())
                logging.info(f"Retrying connection after {retry_count} attempt/s")

                time.sleep(self.retry_delay ** retry_count)
                self.conn.disconnect()
                self.conn = self._initialize_db_connection()
            except Exception as e:
                logging.error("Unhandled exception occurred", exc_info=True)
                raise

        raise Exception(f"Connection Error after {retry_count} attempts")

    def get_table(self, table_name: str, database: str = "public"):
        return self.conn.table(table_name, database=database)

    def list_tables(self, database: str = "public"):
        return self.conn.list_tables(database=database)

    def execute_insert(self, row: dict, schema_name: str, table_name: str):
        with self.conn.con.cursor() as cursor:
            try:
                values = list(row.values())
                table_col_names = list(row.keys())
                col_names = sql.SQL(', ').join(sql.Identifier(n) for n in table_col_names)

                place_holders = sql.SQL(', ').join(sql.Placeholder() * len(table_col_names))
                values = list(row.values())

                query_base = sql.SQL("insert into {schema_name}.{table_name} ({col_names}) values ({values})").format(
                    schema_name=sql.Identifier(schema_name),
                    table_name=sql.Identifier(table_name),
                    col_names=col_names,
                    values=place_holders
                )
                self._execute_sql(cursor, query_base, values)
                self.conn.con.commit()
            except Exception as e:
                logging.error(f"Error inserting row: {e}")
                self.conn.con.rollback()

    def execute_update(self, query: str, params: tuple = None):
        with self.conn.con.cursor() as cursor:
            try:
                self._execute_sql(cursor, query, params)
                self.conn.con.commit()
            except Exception as e:
                logging.error(f"Error executing update: {e}")
                self.conn.con.rollback()

    def execute_query(self, query: str, params: tuple = None):
        with self.conn.con.cursor() as cursor:
            try:
                self._execute_sql(cursor, query, params)
                self.conn.con.commit()
            except Exception as e:
                logging.error(f"Error executing query: {e}")
                self.conn.con.rollback()

    def fetch_all(self, query: str, params: tuple = None, return_as_pandas: bool = True):
        try:
            with self.conn.con.cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchall()

                if return_as_pandas:
                    # Fetch column names from the cursor description
                    columns = [desc[0] for desc in cursor.description]
                    # Return as a pandas DataFrame
                    return pd.DataFrame(result, columns=columns)
                else:
                    # Return as list of tuples (default fetchall output)
                    return result
        except Exception as e:
            logging.error(f"Error fetching all rows: {e}")
            self.conn.con.rollback()
            return None

    def fetch(self, query: str, params: tuple = None):
        try:
            cursor = self.conn.con.cursor()  # Create a named cursor for efficient iteration
            cursor.execute(query, params)
            return cursor  # Return the cursor object to the user
        except Exception as e:
            logging.error(f"Error fetching rows: {e}")
            return None
