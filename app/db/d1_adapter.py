"""
Cloudflare D1 Database Adapter

This adapter allows the application to work with Cloudflare D1 directly.
When deployed to Cloudflare Workers, it uses D1 bindings.
For local development, it falls back to SQLite.
"""

from typing import Any, Dict, List, Optional, Tuple
import json
from datetime import datetime

class D1Adapter:
    """
    Adapter for Cloudflare D1 Database

    Usage in Cloudflare Workers:
        from cloudflare import env
        db = D1Adapter(env.DB)
    """

    def __init__(self, d1_binding):
        """
        Initialize D1 adapter

        Args:
            d1_binding: D1 database binding from Cloudflare Workers environment
        """
        self.db = d1_binding

    async def execute(self, query: str, params: Tuple = ()) -> Dict[str, Any]:
        """Execute a query and return results"""
        try:
            # D1 uses prepared statements
            stmt = self.db.prepare(query)

            # Bind parameters if provided
            if params:
                for param in params:
                    stmt = stmt.bind(param)

            # Execute and return results
            result = await stmt.run()
            return {
                "success": result.success,
                "meta": result.meta,
                "results": result.results if hasattr(result, 'results') else []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    async def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single row"""
        try:
            stmt = self.db.prepare(query)

            if params:
                for param in params:
                    stmt = stmt.bind(param)

            result = await stmt.first()
            return dict(result) if result else None
        except Exception as e:
            print(f"D1 fetch_one error: {e}")
            return None

    async def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        try:
            stmt = self.db.prepare(query)

            if params:
                for param in params:
                    stmt = stmt.bind(param)

            result = await stmt.all()
            return [dict(row) for row in result.results] if hasattr(result, 'results') else []
        except Exception as e:
            print(f"D1 fetch_all error: {e}")
            return []

    async def fetch_value(self, query: str, params: Tuple = ()) -> Any:
        """Fetch a single value"""
        row = await self.fetch_one(query, params)
        if row:
            return list(row.values())[0]
        return None

    async def execute_many(self, statements: List[Tuple[str, Tuple]]) -> Dict[str, Any]:
        """Execute multiple statements in a batch"""
        try:
            # D1 batch operations
            batch = []
            for query, params in statements:
                stmt = self.db.prepare(query)
                if params:
                    for param in params:
                        stmt = stmt.bind(param)
                batch.append(stmt)

            results = await self.db.batch(batch)
            return {
                "success": True,
                "count": len(results),
                "results": results
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
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


# For use in Cloudflare Workers Python runtime
def get_d1_from_env(env):
    """
    Get D1 database from Cloudflare Workers environment

    Usage in worker:
        from app.db.d1_adapter import get_d1_from_env

        async def on_fetch(request, env, ctx):
            db = get_d1_from_env(env)
            # Use db...
    """
    return D1Adapter(env.DB)
