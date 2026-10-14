import requests
from config import API_BASE, FP_API_KEY

class FPClient:
    def __init__(self):
        if not FP_API_KEY:
            raise RuntimeError("FP_API_KEY is missing")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {FP_API_KEY}", "Accept": "application/json"})

    def _request(self, method, path, params=None):
        r = self.session.request(method, API_BASE + path, params=params, timeout=25)
        if not r.ok:
            raise RuntimeError(f"MFP {method} {path} -> {r.status_code}: {r.text[:500]}")
        return r.json() if r.content else {}

    def list_accounts(self):
        return self._request("GET", "/v1/accounts")

    def list_markets(self):
        # Kept identical to the proven old bot behaviour: public market discovery.
        r = requests.get(API_BASE + "/v1/markets", timeout=20)
        r.raise_for_status()
        return r.json()
