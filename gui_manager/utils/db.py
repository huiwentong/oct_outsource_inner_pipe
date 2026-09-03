import psycopg2
from psycopg2.extras import RealDictCursor, RealDictRow
from typing import Optional
from utils.config import get_config

cfg = get_config()

class Database:
    def __init__(
        self,
        host: str = cfg['server_ip'],
        port: int = cfg['db_port'],
        database: str = cfg['db_name'],
        user: str = cfg['admin'],
        password: str = cfg['db_password'],
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password



    def get_connection(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
        )

    def get_all_user(self):
        sql = """
            SELECT * FROM ftpuser;
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql,)
                return cursor.fetchall()