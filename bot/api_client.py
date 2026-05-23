import httpx
from typing import Optional, Dict, Any

class XHTTPManagerClient:
    def __init__(self, base_url: str, admin_token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {"Authorization": f"Bearer {admin_token}"}
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def _get(self, path: str, params=None) -> Optional[Any]:
        try:
            resp = await self.client.get(f"{self.base_url}{path}", params=params, headers=self.headers)
            if resp.status_code == 200:
                if resp.headers.get('content-type', '').startswith('application/json'):
                    return resp.json()
                else:
                    return resp.text
            return None
        except Exception as e:
            print(f"API Error: {e}")
            return None

    async def _post(self, path: str, json=None) -> Optional[Dict]:
        try:
            resp = await self.client.post(f"{self.base_url}{path}", json=json, headers=self.headers)
            if resp.status_code in (200, 201):
                return resp.json()
            return {"error": resp.text}
        except Exception as e:
            return {"error": str(e)}

    async def _delete(self, path: str) -> Optional[Dict]:
        try:
            resp = await self.client.delete(f"{self.base_url}{path}", headers=self.headers)
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.text}
        except Exception as e:
            return {"error": str(e)}

    async def health(self) -> bool:
        try:
            resp = await self.client.get(f"{self.base_url}/api/v1/health", timeout=5.0)
            return resp.status_code == 200
        except:
            return False

    async def get_user_stats(self, username: str) -> Optional[Dict]:
        return await self._get(f"/api/v1/stats/users", params={"username": username})

    async def get_user_details(self, username: str) -> Optional[Dict]:
        return await self._get(f"/api/v1/users/{username}")

    async def get_user_config(self, username: str) -> Optional[str]:
        """Get VLESS config URI for a user."""
        result = await self._get(f"/api/v1/users/{username}/config", params={"format": "uri"})
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return result.get("config") or result.get("vless_uri")
        return None

    async def get_user_qr(self, username: str) -> Optional[bytes]:
        """Get QR code image bytes for a user."""
        try:
            resp = await self.client.get(
                f"{self.base_url}/api/v1/users/{username}/config",
                params={"format": "qr"},
                headers=self.headers
            )
            if resp.status_code == 200:
                return resp.content
            return None
        except:
            return None

    async def create_user(self, username: str, expiry_days: int = None, data_cap_gb: float = None, max_devices: int = None) -> Dict:
        payload = {"username": username}
        if expiry_days:
            payload["expiry_days"] = expiry_days
        if data_cap_gb:
            payload["data_cap_gb"] = data_cap_gb
        if max_devices:
            payload["max_devices"] = max_devices
        return await self._post("/api/v1/users", json=payload)

    async def revoke_user(self, username: str) -> Dict:
        return await self._delete(f"/api/v1/users/{username}")

    async def suspend_user(self, username: str) -> Dict:
        return await self._post(f"/api/v1/users/{username}/suspend")

    async def unsuspend_user(self, username: str) -> Dict:
        return await self._post(f"/api/v1/users/{username}/unsuspend")

    async def extend_user(self, username: str, days: int) -> Dict:
        return await self._post(f"/api/v1/users/{username}/extend", json={"days": days})

    async def list_users(self, status: str = "active", limit: int = 100) -> Optional[Dict]:
        return await self._get("/api/v1/users", params={"status": status, "limit": limit})
