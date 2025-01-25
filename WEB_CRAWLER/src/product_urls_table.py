from psycopg2 import sql

from src.db import PostgresConnection


class ProductURLsManagementSystem:
    def __init__(self, table_name, db_connection=None, schema_name="public"):
        self.schema_name = schema_name
        self.table_name = table_name
        self.db_connection = db_connection or PostgresConnection()
        if self.table_name not in self.db_connection.list_tables():
            self.create_table()

    def create_table(self):
        query = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} (
                id BIGSERIAL PRIMARY KEY,
                url TEXT UNIQUE,
                domain_name TEXT
            );
        """).format(
            schema_name=sql.Identifier(self.schema_name),
            table_name=sql.Identifier(self.table_name)
        )
        self.db_connection.execute_query(query=query)

    def insert_one(self, url: str, domain_name: str):
        row = {"url": url, "domain_name": domain_name}
        self.db_connection.execute_insert(row, self.schema_name, self.table_name)
