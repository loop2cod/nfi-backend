"""
Cloudflare D1 HTTP API Client

This allows Python applications to connect directly to Cloudflare D1
via the REST API without needing to be deployed to Workers.
"""

import requests
from typing import Any, Dict, List, Optional, Tuple
import json
from datetime import datetime

class D1HTTPClient:
    """
    HTTP client for Cloudflare D1 REST API

    Usage:
        from app.core.config import settings
        client = D1HTTPClient(
            account_id=settings.D1_ACCOUNT_ID,
            database_id=settings.D1_DATABASE_ID,
            api_token=settings.D1_API_TOKEN
        )

        # Execute query
        result = client.execute("SELECT * FROM users WHERE email = ?", ("test@example.com",))
    """

    def __init__(self, account_id: str, database_id: str, api_token: str):
        """
        Initialize D1 HTTP client

        Args:
            account_id: Cloudflare account ID
            database_id: D1 database ID
            api_token: Cloudflare API token with D1 permissions
        """
        self.account_id = account_id
        self.database_id = database_id
        self.api_token = api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        })

    def execute(self, query: str, params: Tuple = ()) -> Dict[str, Any]:
        """Execute a SQL query"""
        payload = {
            "sql": query
        }

        if params:
            payload["params"] = list(params)

        try:
            response = self.session.post(self.base_url, json=payload)
            response.raise_for_status()

            data = response.json()

            if data.get("success"):
                results = data.get("result", [])
                if results and len(results) > 0:
                    return {
                        "success": True,
                        "results": results[0].get("results", []),
                        "meta": results[0].get("meta", {})
                    }
                return {"success": True, "results": [], "meta": {}}
            else:
                return {
                    "success": False,
                    "error": data.get("errors", ["Unknown error"])[0],
                    "results": []
                }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single row"""
        result = self.execute(query, params)

        if result.get("success") and result.get("results"):
            rows = result["results"]
            return rows[0] if rows else None

        return None

    def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        result = self.execute(query, params)

        if result.get("success"):
            return result.get("results", [])

        return []

    def fetch_value(self, query: str, params: Tuple = ()) -> Any:
        """Fetch a single value"""
        row = self.fetch_one(query, params)

        if row:
            return list(row.values())[0]

        return None

    def execute_many(self, statements: List[Tuple[str, Tuple]]) -> Dict[str, Any]:
        """Execute multiple statements"""
        # D1 HTTP API doesn't support batch in the same way
        # Execute sequentially for now
        results = []
        for query, params in statements:
            result = self.execute(query, params)
            results.append(result)

        success = all(r.get("success", False) for r in results)
        return {
            "success": success,
            "count": len(results),
            "results": results
        }

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

        # Convert boolean fields
        for key, value in result.items():
            if key.startswith('is_') or key.endswith('_verified') or key == 'revoked' or key == 'flagged':
                result[key] = bool(value)

        return result

    def close(self):
        """Close the HTTP session"""
        self.session.close()
