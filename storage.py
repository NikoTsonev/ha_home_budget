import asyncio
import hashlib
import json
import os
import sqlite3
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from homeassistant.core import HomeAssistant

DB_FILENAME = "home_budget.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date TEXT NOT NULL,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('expense','income')),
    category TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    account TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'manual',
    external_id TEXT,
    dedupe_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
"""

def _connect(path):
    con = sqlite3.connect(path, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    return con

def _money(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("amount must be a valid number")
    if not amount.is_finite() or amount <= 0:
        raise ValueError("amount must be greater than zero")
    return amount

def _normalise_date(value):
    if not value:
        return date.today().isoformat()
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except ValueError:
        raise ValueError("date must use YYYY-MM-DD format")

def _dedupe_key(kind, tx_date, amount, currency, category, description, account, external_id):
    if external_id:
        raw = f"external|{external_id.strip()}"
    else:
        # Manual transactions are intentionally not deduplicated by content:
        # two legitimate purchases can have the same amount and description.
        raw = f"manual|{datetime.now().isoformat()}|{os.urandom(8).hex()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

class BudgetStore:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.path = hass.config.path(DB_FILENAME)
        self._lock = asyncio.Lock()

    async def async_setup(self):
        await self.hass.async_add_executor_job(self._init_db)

    def _init_db(self):
        con = _connect(self.path)
        con.close()

    async def async_add(self, *, amount, currency, kind, category, tx_date=None,
                        description="", account="", source="manual", external_id=None):
        if kind not in ("expense", "income"):
            raise ValueError("kind must be expense or income")
        money = _money(amount)
        tx_date = _normalise_date(tx_date)
        category = str(category).strip()
        if not category:
            raise ValueError("category is required")
        currency = str(currency).upper().strip()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a 3-letter code")
        description = str(description or "").strip()
        account = str(account or "").strip()
        external_id = str(external_id).strip() if external_id else None
        key = _dedupe_key(kind, tx_date, money, currency, category, description, account, external_id)
        async with self._lock:
            return await self.hass.async_add_executor_job(
                self._insert, tx_date, str(money), currency, kind, category,
                description, account, source, external_id, key
            )

    def _insert(self, tx_date, amount, currency, kind, category, description, account, source, external_id, key):
        con = _connect(self.path)
        try:
            cur = con.execute(
                """INSERT OR IGNORE INTO transactions
                (transaction_date,amount,currency,kind,category,description,account,source,external_id,dedupe_key,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (tx_date, amount, currency, kind, category, description, account, source, external_id, key, datetime.now().isoformat(timespec="seconds"))
            )
            con.commit()
            if cur.rowcount == 0:
                row = con.execute("SELECT id FROM transactions WHERE dedupe_key=?", (key,)).fetchone()
                return {"inserted": False, "id": row["id"]}
            return {"inserted": True, "id": cur.lastrowid}
        finally:
            con.close()

    async def async_delete(self, transaction_id):
        async with self._lock:
            return await self.hass.async_add_executor_job(self._delete, int(transaction_id))

    def _delete(self, transaction_id):
        con = _connect(self.path)
        try:
            cur = con.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
            con.commit()
            return cur.rowcount > 0
        finally:
            con.close()

    async def async_summary(self, currency):
        async with self._lock:
            return await self.hass.async_add_executor_job(self._summary, currency)

    def _summary(self, currency):
        month = date.today().strftime("%Y-%m")
        con = _connect(self.path)
        try:
            rows = con.execute(
                """SELECT kind, COALESCE(SUM(CAST(amount AS REAL)),0) AS total
                FROM transactions WHERE currency=? AND substr(transaction_date,1,7)=?
                GROUP BY kind""", (currency, month)
            ).fetchall()
            totals = {"expense": 0.0, "income": 0.0}
            for row in rows:
                totals[row["kind"]] = round(float(row["total"]), 2)
            cats = con.execute(
                """SELECT category, ROUND(SUM(CAST(amount AS REAL)),2) AS total
                FROM transactions WHERE currency=? AND kind='expense'
                AND substr(transaction_date,1,7)=? GROUP BY category ORDER BY total DESC""",
                (currency, month)
            ).fetchall()
            recent = con.execute(
                """SELECT id,transaction_date,amount,currency,kind,category,description,account,source
                FROM transactions ORDER BY transaction_date DESC,id DESC LIMIT 10"""
            ).fetchall()
            count = con.execute(
                "SELECT COUNT(*) AS n FROM transactions WHERE substr(transaction_date,1,7)=?",
                (month,)
            ).fetchone()["n"]
            return {
                "month": month, "expenses": totals["expense"], "income": totals["income"],
                "balance": round(totals["income"] - totals["expense"], 2),
                "categories": {r["category"]: float(r["total"]) for r in cats},
                "recent": [dict(r) for r in recent], "transaction_count": count,
            }
        finally:
            con.close()
