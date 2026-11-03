from .categorizer import UNSORTED

DOMAIN = "home_budget"
PLATFORMS = ["sensor"]

CONF_CURRENCY = "currency"
DEFAULT_CURRENCY = "EUR"
CONF_CATEGORIES = "categories"
DEFAULT_CATEGORIES = [UNSORTED]

SERVICE_ADD_TRANSACTION = "add_transaction"
SERVICE_DELETE_TRANSACTION = "delete_transaction"
SERVICE_REFRESH = "refresh"

ATTR_AMOUNT = "amount"
ATTR_KIND = "kind"
ATTR_CATEGORY = "category"
ATTR_DATE = "date"
ATTR_DESCRIPTION = "description"
ATTR_ACCOUNT = "account"
ATTR_EXTERNAL_ID = "external_id"
ATTR_TRANSACTION_ID = "transaction_id"

KINDS = ["expense", "income"]
