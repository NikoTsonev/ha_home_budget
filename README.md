# Home Budget — custom Home Assistant integration (MVP)

This integration stores personal finance transactions locally in `/config/home_budget.sqlite3`.

## Install
1. Copy `custom_components/home_budget` into `/config/custom_components/home_budget`.
2. Restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and search for **Home Budget**.
4. Select your reporting currency (default EUR).

## Add a transaction
Use **Developer Tools → Actions** (called Services in older HA versions), select `home_budget.add_transaction` and use:

```yaml
amount: 12.50
kind: expense
category: Groceries
date: "2026-10-14"
description: "Supermarket"
account: "Revolut"
currency: EUR
```

`kind` must be `expense` or `income`. Amount must be positive; choose the kind to determine the direction.

## Delete a transaction
Use action `home_budget.delete_transaction`:

```yaml
transaction_id: 1
```

Transaction IDs are visible in the `recent_transactions` attribute of `sensor.home_budget_monthly_expenses` (depending on entity naming; inspect the entity attributes).

## Entities
- `sensor.home_budget_monthly_expenses`
- `sensor.home_budget_monthly_income`
- `sensor.home_budget_monthly_balance`
- `sensor.home_budget_monthly_transactions`

Actual entity IDs may be adjusted by Home Assistant if those IDs already exist. The sensors update every 5 minutes and reload after add/delete actions.

## Dashboard
Add an Entities card containing the four sensors. Add a Markdown card for quick navigation/instructions. See `dashboard-example.yaml`.

## Important limitations in v0.1
- CSV upload/import is not implemented yet.
- This first version provides backend services and summary sensors, not a custom form panel.
- No category management UI yet; categories are free text.
- Reporting sums only transactions in the configured currency. Multi-currency conversion is not implemented.
- The manual-entry service intentionally allows identical purchases; deduplication will use stable external IDs for imported transactions.
- Keep a Home Assistant backup and separately back up `/config/home_budget.sqlite3`.
