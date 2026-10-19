import asyncio
import hashlib
import json
import os
import sqlite3
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from homeassistant.core import HomeAssistant

from .categorizer import UNSORTED, normalise_text

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
CREATE TABLE IF NOT EXISTS category_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

def _upsert_rule(con, pattern, category):
    con.execute(
        """INSERT INTO category_rules (pattern, category, created_at) VALUES (?,?,?)
        ON CONFLICT(pattern) DO UPDATE SET category=excluded.category""",
        (pattern, category, datetime.now().isoformat(timespec="seconds")),
    )

def _apply_rule(con, pattern, category):
    """Move every Unsorted transaction whose description contains the pattern."""
    rows = con.execute(
        "SELECT id, description FROM transactions WHERE category=?", (UNSORTED,)
    ).fetchall()
    ids = [(category, r["id"]) for r in rows if pattern in normalise_text(r["description"])]
    con.executemany("UPDATE transactions SET category=? WHERE id=?", ids)
    return len(ids)

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

def _clean_fields(amount, currency, kind, category, tx_date, description, account):
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
    return (money, tx_date, currency, kind, category,
            str(description or "").strip(), str(account or "").strip())

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
        money, tx_date, currency, kind, category, description, account = _clean_fields(
            amount, currency, kind, category, tx_date, description, account
        )
        external_id = str(external_id).strip() if external_id else None
        key = _dedupe_key(kind, tx_date, money, currency, category, description, account, external_id)
        async with self._lock:
            return await self.hass.async_add_executor_job(
                self._insert, tx_date, str(money), currency, kind, category,
                description, account, source, external_id, key
            )

    async def async_update(self, transaction_id, *, amount, currency, kind, category, tx_date,
                           description="", account=""):
        money, tx_date, currency, kind, category, description, account = _clean_fields(
            amount, currency, kind, category, tx_date, description, account
        )
        async with self._lock:
            return await self.hass.async_add_executor_job(
                self._update, int(transaction_id), tx_date, str(money), currency, kind,
                category, description, account
            )

    def _update(self, transaction_id, tx_date, amount, currency, kind, category, description, account):
        con = _connect(self.path)
        try:
            cur = con.execute(
                """UPDATE transactions SET transaction_date=?, amount=?, currency=?, kind=?,
                category=?, description=?, account=? WHERE id=?""",
                (tx_date, amount, currency, kind, category, description, account, transaction_id),
            )
            con.commit()
            return cur.rowcount > 0
        finally:
            con.close()

    async def async_list(self, *, currency, month=None, category=None, kind=None,
                         search=None, limit=100, offset=0):
        async with self._lock:
            return await self.hass.async_add_executor_job(
                self._list, currency, month, category, kind, search, int(limit), int(offset)
            )

    def _list(self, currency, month, category, kind, search, limit, offset):
        where, params = [], []
        if month:
            where.append("substr(transaction_date,1,7)=?")
            params.append(month)
        if category:
            where.append("category=?")
            params.append(category)
        if kind:
            where.append("kind=?")
            params.append(kind)
        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            where.append("(description LIKE ? ESCAPE '\\' OR account LIKE ? ESCAPE '\\')")
            params += [f"%{escaped}%", f"%{escaped}%"]
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        con = _connect(self.path)
        try:
            total = con.execute(f"SELECT COUNT(*) AS n FROM transactions {clause}", params).fetchone()["n"]
            sums = con.execute(
                f"""SELECT kind, COALESCE(SUM(CAST(amount AS REAL)),0) AS total
                FROM transactions {clause}{' AND' if clause else 'WHERE'} currency=?
                GROUP BY kind""", params + [currency]
            ).fetchall()
            rows = con.execute(
                f"""SELECT id,transaction_date,amount,currency,kind,category,description,account,source
                FROM transactions {clause}
                ORDER BY transaction_date DESC,id DESC LIMIT ? OFFSET ?""",
                params + [limit, offset],
            ).fetchall()
            totals = {"expense": 0.0, "income": 0.0}
            for row in sums:
                totals[row["kind"]] = round(float(row["total"]), 2)
            used = [r["category"] for r in con.execute(
                "SELECT DISTINCT category FROM transactions ORDER BY category"
            ).fetchall()]
            return {
                "items": [dict(r) for r in rows], "total": total,
                "expenses": totals["expense"], "income": totals["income"],
                "used_categories": used,
            }
        finally:
            con.close()

    async def async_import(self, transactions):
        """Insert many transactions; invalid ones are reported, duplicates ignored."""
        inserted = duplicates = 0
        errors = []
        for index, tx in enumerate(transactions, start=1):
            try:
                result = await self.async_add(**tx)
            except ValueError as err:
                errors.append(f"#{index}: {err}")
                continue
            if result["inserted"]:
                inserted += 1
            else:
                duplicates += 1
        return {"inserted": inserted, "duplicates": duplicates, "errors": errors}

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

    async def async_unsorted_groups(self, unsorted):
        async with self._lock:
            return await self.hass.async_add_executor_job(self._unsorted_groups, unsorted)

    def _unsorted_groups(self, unsorted):
        con = _connect(self.path)
        try:
            rows = con.execute(
                """SELECT description, kind, COUNT(*) AS n,
                ROUND(SUM(CAST(amount AS REAL)),2) AS total, MIN(currency) AS currency
                FROM transactions WHERE category=? GROUP BY description, kind
                ORDER BY n DESC, description""", (unsorted,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            con.close()

    async def async_recategorize(self, *, from_category, to_category, description=None,
                                 transaction_id=None, remember=False):
        """Move transactions to a category; with remember=True also store a rule for the
        description and apply it to every matching Unsorted transaction."""
        to_category = str(to_category).strip()
        if not to_category:
            raise ValueError("category is required")
        async with self._lock:
            return await self.hass.async_add_executor_job(
                self._recategorize, from_category, to_category, description, transaction_id, remember
            )

    def _recategorize(self, from_category, to_category, description, transaction_id, remember):
        con = _connect(self.path)
        try:
            count = 0
            if transaction_id is not None:
                count += con.execute(
                    "UPDATE transactions SET category=? WHERE id=?", (to_category, int(transaction_id))
                ).rowcount
            elif description is not None:
                count += con.execute(
                    "UPDATE transactions SET category=? WHERE category=? AND description=?",
                    (to_category, from_category, description),
                ).rowcount
            pattern = normalise_text(description)
            if remember and pattern and to_category != UNSORTED:
                _upsert_rule(con, pattern, to_category)
                count += _apply_rule(con, pattern, to_category)
            con.commit()
            return count
        finally:
            con.close()

    async def async_rules(self):
        async with self._lock:
            return await self.hass.async_add_executor_job(self._rules)

    def _rules(self):
        con = _connect(self.path)
        try:
            rows = con.execute(
                "SELECT id, pattern, category FROM category_rules ORDER BY LENGTH(pattern) DESC, id"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            con.close()

    async def async_add_rule(self, pattern, category):
        pattern = normalise_text(pattern)
        category = str(category).strip()
        if not pattern or not category:
            raise ValueError("pattern and category are required")
        async with self._lock:
            return await self.hass.async_add_executor_job(self._add_rule, pattern, category)

    def _add_rule(self, pattern, category):
        con = _connect(self.path)
        try:
            _upsert_rule(con, pattern, category)
            applied = _apply_rule(con, pattern, category)
            con.commit()
            return applied
        finally:
            con.close()

    async def async_delete_rule(self, rule_id):
        async with self._lock:
            return await self.hass.async_add_executor_job(self._delete_rule, int(rule_id))

    def _delete_rule(self, rule_id):
        con = _connect(self.path)
        try:
            cur = con.execute("DELETE FROM category_rules WHERE id=?", (rule_id,))
            con.commit()
            return cur.rowcount > 0
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
                AND category != 'Top-up'
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
