"""
SentinelOps AI - Dashboard SaaS API Client.
Handles JWT authentication, organization scoping, and API requests to FastAPI backend.
"""

from typing import Optional, Dict, Any, List
import requests


class SaaSClient:
    """
    HTTP Client communicating with SentinelOps FastAPI Backend (http://127.0.0.1:8000).
    Manages user session, JWT auth headers, and organization scoping.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.user: Optional[Dict[str, Any]] = None
        self.active_org: Optional[Dict[str, Any]] = None

    def _headers(self, collector_token: Optional[str] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if collector_token:
            headers["X-Collector-Token"] = collector_token
        return headers

    def check_health(self) -> bool:
        """Verify if backend is reachable."""
        try:
            r = requests.get(f"{self.base_url}/", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------
    def register(self, email: str, password: str, full_name: str, org_name: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/auth/register"
        r = requests.post(url, json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "organization_name": org_name,
        }, timeout=4.0)
        if r.status_code == 201:
            data = r.json()
            self.token = data["access_token"]
            self.user = data["user"]
            self.active_org = {"id": data["active_organization_id"], "name": org_name}
            return {"success": True, "data": data}
        return {"success": False, "error": r.json().get("detail", "Registration failed")}

    def login(self, email: str, password: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/auth/login"
        r = requests.post(url, json={"email": email, "password": password}, timeout=4.0)
        if r.status_code == 200:
            data = r.json()
            self.token = data["access_token"]
            self.user = data["user"]
            org_id = data.get("active_organization_id")
            self.active_org = {"id": org_id, "name": "Active Workspace"}
            return {"success": True, "data": data}
        return {"success": False, "error": r.json().get("detail", "Invalid email or password")}

    def get_me(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/auth/me"
        r = requests.get(url, headers=self._headers(), timeout=3.0)
        if r.status_code == 200:
            return {"success": True, "data": r.json()}
        return {"success": False, "error": r.json().get("detail", "Failed to fetch user")}

    def logout(self) -> None:
        self.token = None
        self.user = None
        self.active_org = None

    # -------------------------------------------------------------------------
    # Organizations
    # -------------------------------------------------------------------------
    def list_orgs(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/orgs"
        r = requests.get(url, headers=self._headers(), timeout=3.0)
        if r.status_code == 200:
            return r.json()
        return []

    def create_org(self, name: str, slug: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/orgs"
        r = requests.post(url, headers=self._headers(), json={"name": name, "slug": slug}, timeout=3.0)
        if r.status_code == 201:
            return {"success": True, "data": r.json()}
        return {"success": False, "error": r.json().get("detail", "Failed to create organization")}

    def set_active_org(self, org: Dict[str, Any]) -> None:
        self.active_org = org

    def list_members(self, org_id: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/orgs/{org_id}/members"
        r = requests.get(url, headers=self._headers(), timeout=3.0)
        if r.status_code == 200:
            return r.json()
        return []

    def list_audit_logs(self, org_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/orgs/{org_id}/audit-logs"
        r = requests.get(url, headers=self._headers(), params={"limit": limit}, timeout=3.0)
        if r.status_code == 200:
            return r.json()
        return []

    # -------------------------------------------------------------------------
    # Collectors
    # -------------------------------------------------------------------------
    def list_collectors(self, org_id: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/orgs/{org_id}/collectors"
        r = requests.get(url, headers=self._headers(), timeout=3.0)
        if r.status_code == 200:
            return r.json()
        return []

    def register_collector(self, org_id: str, name: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/orgs/{org_id}/collectors"
        r = requests.post(url, headers=self._headers(), json={"name": name}, timeout=3.0)
        if r.status_code == 201:
            return {"success": True, "data": r.json()}
        return {"success": False, "error": r.json().get("detail", "Failed to register collector")}

    def revoke_collector(self, org_id: str, collector_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/orgs/{org_id}/collectors/{collector_id}"
        r = requests.delete(url, headers=self._headers(), timeout=3.0)
        if r.status_code == 200:
            return {"success": True, "message": "Collector revoked"}
        return {"success": False, "error": r.json().get("detail", "Failed to revoke collector")}

    # -------------------------------------------------------------------------
    # Telemetry & Metrics
    # -------------------------------------------------------------------------
    def send_telemetry(self, payload: Dict[str, Any], collector_token: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/telemetry"
        r = requests.post(url, headers=self._headers(collector_token=collector_token), json=payload, timeout=3.0)
        if r.status_code in [200, 201]:
            return {"success": True, "data": r.json()}
        return {"success": False, "error": r.json().get("detail", "Telemetry send failed")}

    def get_tenant_metrics(self, org_id: str, source_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/orgs/{org_id}/metrics"
        params = {"limit": limit}
        if source_id:
            params["source_id"] = source_id
        r = requests.get(url, headers=self._headers(), params=params, timeout=3.0)
        if r.status_code == 200:
            return r.json().get("data", [])
        return []

    def get_tenant_summary(self, org_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/orgs/{org_id}/metrics/summary"
        r = requests.get(url, headers=self._headers(), timeout=3.0)
        if r.status_code == 200:
            return r.json().get("data", {})
        return {}

    # -------------------------------------------------------------------------
    # Incidents
    # -------------------------------------------------------------------------
    def list_incidents(
        self,
        org_id: str,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/orgs/{org_id}/incidents"
        params = {}
        if status and status != "all":
            params["status"] = status
        if severity and severity != "all":
            params["severity"] = severity
        if source_id and source_id != "all":
            params["source_id"] = source_id

        r = requests.get(url, headers=self._headers(), params=params, timeout=3.0)
        if r.status_code == 200:
            return r.json()
        return []

    def update_incident_status(self, org_id: str, incident_id: str, status: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/orgs/{org_id}/incidents/{incident_id}/status"
        r = requests.patch(url, headers=self._headers(), json={"status": status}, timeout=3.0)
        if r.status_code == 200:
            return {"success": True, "data": r.json()}
        return {"success": False, "error": r.json().get("detail", "Failed to update incident")}

    # -------------------------------------------------------------------------
    # Privacy Lab
    # -------------------------------------------------------------------------
    def inspect_privacy(self, sample_data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/privacy/inspect"
        r = requests.post(url, headers=self._headers(), json={"sample_data": sample_data}, timeout=3.0)
        if r.status_code == 200:
            return {"success": True, "data": r.json()}
        return {"success": False, "error": r.json().get("detail", "Privacy inspection failed")}
