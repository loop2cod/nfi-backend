import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json

class Database:
    """
    Database wrapper for Cloudflare D1 / SQLite

    This class provides a clean interface for database operations.
    In production with Cloudflare Workers, this will use D1 bindings.
    For local development, it uses SQLite with the same schema.
    """

    def __init__(self, db_path: str = "nfi_platform.db"):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self):
        """Establish database connection"""
        if not self.connection:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Return rows as dictionaries
        return self.connection

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute(self, query: str, params: Tuple = ()) -> sqlite3.Cursor:
        """Execute a single query"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor

    def execute_many(self, query: str, params_list: List[Tuple]) -> None:
        """Execute multiple queries with different parameters"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()

    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single row"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def fetch_value(self, query: str, params: Tuple = ()) -> Any:
        """Fetch a single value"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return row[0] if row else None

    @staticmethod
    def now() -> int:
        """Get current timestamp in milliseconds"""
        return int(datetime.utcnow().timestamp() * 1000)

    @staticmethod
    def to_json(data: Any) -> str:
        """Convert Python object to JSON string"""
        return json.dumps(data) if data else None

    @staticmethod
    def from_json(data: str) -> Any:
        """Convert JSON string to Python object"""
        return json.loads(data) if data else None

    @staticmethod
    def dict_to_row(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert dictionary values for database insertion"""
        result = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                result[key] = json.dumps(value)
            elif isinstance(value, datetime):
                result[key] = int(value.timestamp() * 1000)
            elif isinstance(value, bool):
                result[key] = 1 if value else 0
            else:
                result[key] = value
        return result

    @staticmethod
    def row_to_dict(row: Dict[str, Any], json_fields: List[str] = None) -> Dict[str, Any]:
        """Convert database row to dictionary with proper types"""
        if json_fields is None:
            json_fields = []

        result = dict(row)

        # Convert JSON fields
        for field in json_fields:
            if field in result and result[field]:
                try:
                    result[field] = json.loads(result[field])
                except (json.JSONDecodeError, TypeError):
                    pass

        # Convert boolean fields (stored as 0/1 in SQLite)
        for key, value in result.items():
            if key.startswith('is_') or key.endswith('_verified') or key == 'revoked' or key == 'flagged':
                result[key] = bool(value)

        return result

    def init_schema(self, schema_path: str = "database/schema.sql"):
        """Initialize database schema from SQL file"""
        try:
            with open(schema_path, 'r') as f:
                schema = f.read()

            conn = self.connect()
            cursor = conn.cursor()
            cursor.executescript(schema)
            conn.commit()
            print(f"✓ Database schema initialized from {schema_path}")
        except FileNotFoundError:
            print(f"✗ Schema file not found: {schema_path}")
        except Exception as e:
            print(f"✗ Error initializing schema: {e}")
