"""Parser for Revolut statement exports (CSV and XLSX)."""

import csv
import hashlib
import io
import re
import zipfile
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from .categorizer import categorise

# EXCHANGE moves money between own pockets, so it is never real income/expense.
ALWAYS_SKIPPED_TYPES = {"EXCHANGE"}
TRANSFER_TYPES = {"TOPUP", "TRANSFER"}
NUM_TAG = "\x00num:"

_ALIASES = {
    "type": ("type",),
    "product": ("product",),
    "date": (
        "completed date",
        "date completed (utc)",
        "started date",
        "date started (utc)",
    ),
    "description": ("description",),
    "amount": ("amount",),
    "fee": ("fee",),
    "currency": ("currency",),
    "state": ("state",),
    "balance": ("balance",),
    "category": ("category",),
}


def _col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    index = 0
    for ch in letters:
        index = index * 26 + ord(ch) - 64
    return index - 1


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _read_xlsx(content):
    """Return the first worksheet as (list of dict rows, header). Numeric cells are tagged."""
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ElementTree.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root:
                shared.append(
                    "".join(t.text or "" for t in si.iter() if _local(t.tag) == "t")
                )
        sheets = sorted(
            n for n in zf.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)
        )
        if not sheets:
            raise ValueError("XLSX file has no worksheets")
        root = ElementTree.fromstring(zf.read(sheets[0]))

    rows = []
    for row in root.iter():
        if _local(row.tag) != "row":
            continue
        values = {}
        for cell in row:
            ref = cell.get("r")
            if not ref:
                continue
            kind = cell.get("t")
            raw = ""
            if kind == "inlineStr":
                raw = "".join(t.text or "" for t in cell.iter() if _local(t.tag) == "t")
            else:
                for child in cell:
                    if _local(child.tag) == "v":
                        raw = child.text or ""
            if kind == "s" and raw:
                raw = shared[int(raw)]
            elif kind not in ("s", "inlineStr", "str") and raw:
                raw = NUM_TAG + raw
            values[_col_index(ref)] = raw
        if values:
            rows.append([values.get(i, "") for i in range(max(values) + 1)])
    if not rows:
        raise ValueError("XLSX file is empty")
    header = [h.replace(NUM_TAG, "").strip() for h in rows[0]]
    return [dict(zip(header, r)) for r in rows[1:]], header


def _read_csv(content):
    text = content.decode("utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("File is empty")
    return list(reader), reader.fieldnames


def _fix_mojibake(text):
    """Repair UTF-8 text that was decoded as cp1252/latin-1 (e.g. 'Î•Î³Î½Î±Ï„Î¯Î±')."""
    if not any(ch in text for ch in "ÃÂÎÏÐÑâ"):
        return text
    raw = bytearray()
    for ch in text:
        try:
            raw += ch.encode("cp1252")
        except UnicodeEncodeError:
            if ord(ch) > 255:
                return text
            raw.append(ord(ch))
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return text


def _plain(value):
    return _fix_mojibake((value or "").replace(NUM_TAG, "").strip())


def _decimal(value):
    value = _plain(value).replace(" ", "")
    if not value:
        return Decimal(0)
    return Decimal(value)


def _iso_date(value):
    value = (value or "").strip()
    if value.startswith(NUM_TAG):
        serial = float(value[len(NUM_TAG) :])
        return (date(1899, 12, 30) + timedelta(days=int(serial))).isoformat()
    match = re.match(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", value)
    if match:
        day, month, year = match.groups()
        year = f"20{year}" if len(year) == 2 else year
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return value[:10]


def parse_revolut(content, skip_transfers=False, user_rules=()):
    """Return (transactions, skipped, errors) parsed from a Revolut CSV/XLSX export (bytes)."""
    rows, fieldnames = (
        _read_xlsx(content) if content[:2] == b"PK" else _read_csv(content)
    )
    lowered = {name.strip().lower(): name for name in fieldnames if name}
    cols = {
        k: [lowered[n] for n in names if n in lowered] for k, names in _ALIASES.items()
    }
    if not cols["amount"] or not cols["currency"] or not cols["date"]:
        raise ValueError(
            "Not a Revolut statement: missing Amount, Currency or Date columns"
        )

    def get(row, key):
        for col in cols[key]:
            if row.get(col):
                return row[col]
        return ""

    transactions, errors = [], []
    skipped = 0
    seen = {}
    for line, row in enumerate(rows, start=2):
        state = _plain(get(row, "state")).upper()
        if state and state != "COMPLETED":
            skipped += 1
            continue
        tx_type = _plain(get(row, "type"))
        norm_type = re.sub(r"[\s_\-]", "", tx_type.upper())
        if norm_type in ALWAYS_SKIPPED_TYPES or (
            skip_transfers and norm_type in TRANSFER_TYPES
        ):
            skipped += 1
            continue
        try:
            amount = _decimal(get(row, "amount"))
            fee = _decimal(get(row, "fee"))
        except InvalidOperation:
            errors.append(f"line {line}: invalid amount")
            continue
        total = amount - fee
        if total == 0:
            skipped += 1
            continue
        kind = "income" if total > 0 else "expense"
        description = _plain(get(row, "description"))
        raw = "|".join(
            _plain(get(row, k))
            for k in (
                "date",
                "type",
                "description",
                "amount",
                "fee",
                "currency",
                "balance",
                "product",
            )
        )
        # Identical rows within one file stay distinct; re-importing yields the same ids.
        seen[raw] = seen.get(raw, 0) + 1
        external_id = (
            "revolut|" + hashlib.sha256(f"{raw}|{seen[raw]}".encode()).hexdigest()
        )
        categories = HomeBudgetOptionsFlow._categories()
        file_category = _plain(get(row, "category"))
        if file_category and file_category in categories:
            category = file_category
        else:
            category = categorise(description, tx_type, kind, user_rules)
        transactions.append(
            {
                "amount": abs(total),
                "currency": _plain(get(row, "currency")),
                "kind": kind,
                # "category": _plain(get(row, "category")) or categorise(description, tx_type, kind, user_rules),
                "category": category,
                "tx_date": _iso_date(get(row, "date")),
                "description": description,
                "account": f"Revolut {_plain(get(row, 'product'))}".strip(),
                "source": "revolut",
                "external_id": external_id,
            }
        )
    return transactions, skipped, errors
