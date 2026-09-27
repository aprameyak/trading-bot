from __future__ import annotations

import base64
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def _d(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    return Decimal(str(value))


def money(value: Decimal | float | str, places: str = "0.0001") -> str:
    q = Decimal(places)
    return str(Decimal(str(value)).quantize(q, rounding=ROUND_DOWN))


@dataclass
class Market:
    ticker: str
    event_ticker: str
    title: str
    yes_bid: Decimal
    yes_ask: Decimal
    volume_24h: Decimal
    liquidity: Decimal
    close_time: str
    rules_primary: str
    category: str
    subtitle: str

    @property
    def mid(self) -> Decimal:
        if self.yes_bid > 0 and self.yes_ask > 0 and self.yes_ask < 1:
            return (self.yes_bid + self.yes_ask) / 2
        if self.yes_ask > 0 and self.yes_ask < 1:
            return self.yes_ask
        if self.yes_bid > 0:
            return self.yes_bid
        return Decimal("0.5")

    @property
    def spread(self) -> Decimal:
        if self.yes_bid > 0 and self.yes_ask > 0:
            return self.yes_ask - self.yes_bid
        if self.yes_ask > 0:
            return self.yes_ask
        return Decimal("1")


class KalshiClient:
    def __init__(self, base_url: str, api_key_id: str, private_key_path: Path):
        self.base_url = base_url.rstrip("/")
        self.api_key_id = api_key_id
        self._private_key = self._load_key(private_key_path)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    @staticmethod
    def _load_key(path: Path):
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    def _sign(self, method: str, full_path: str) -> dict[str, str]:
        path_no_query = full_path.split("?", 1)[0]
        timestamp = str(int(time.time() * 1000))
        message = f"{timestamp}{method.upper()}{path_no_query}".encode("utf-8")
        signature = self._private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        auth: bool = True,
        timeout: float = 30,
        retries: int = 3,
    ) -> Any:
        if not path.startswith("/"):
            path = "/" + path
        url = self.base_url + path

        last_err: Exception | None = None
        for attempt in range(retries):
            headers: dict[str, str] = {}
            if auth:
                headers.update(self._sign(method, urlparse(url).path))
            if json_body is not None:
                headers["Content-Type"] = "application/json"
            try:
                resp = self.session.request(
                    method.upper(),
                    url,
                    params=params,
                    json=json_body,
                    headers=headers,
                    timeout=timeout,
                )
            except requests.RequestException as exc:
                last_err = exc
                time.sleep(min(2**attempt, 8))
                continue

            if resp.status_code == 429:
                time.sleep(min(2**attempt, 8))
                last_err = RuntimeError("Kalshi rate limit hit")
                continue
            if resp.status_code >= 400:
                raise RuntimeError(f"Kalshi {resp.status_code}: {resp.text}")
            if resp.status_code == 204 or not resp.content:
                return {}
            return resp.json()

        raise RuntimeError(f"Kalshi request failed after retries: {last_err}")

    def get_balance(self) -> dict:
        return self.request("GET", "/portfolio/balance")

    def list_events(self, *, limit: int = 50, cursor: str | None = None) -> dict:
        params: dict[str, Any] = {
            "limit": limit,
            "status": "open",
            "with_nested_markets": "true",
        }
        if cursor:
            params["cursor"] = cursor
        return self.request("GET", "/events", params=params, auth=False)

    def get_market(self, ticker: str) -> dict:
        return self.request("GET", f"/markets/{ticker}", auth=False).get("market", {})

    def create_order(
        self,
        *,
        ticker: str,
        side: str,
        count: Decimal | str | int,
        price: Decimal | str | float,
        time_in_force: str = "fill_or_kill",
        post_only: bool = False,
        client_order_id: str | None = None,
    ) -> dict:
        body = {
            "ticker": ticker,
            "side": side,
            "count": money(Decimal(str(count)), "0.01"),
            "price": money(Decimal(str(price)), "0.0001"),
            "time_in_force": time_in_force,
            "self_trade_prevention_type": "taker_at_cross",
            "client_order_id": client_order_id or str(uuid.uuid4()),
            "post_only": post_only,
        }
        return self.request("POST", "/portfolio/events/orders", json_body=body)
