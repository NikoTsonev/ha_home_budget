"""Keyword based categorisation of bank transaction descriptions."""
import re

UNSORTED = "Unsorted"

CATEGORY_RULES = {
    "Tolls & vignettes": [
        "roviniete", "toll", "dunav most", "promachona", "nea egnatia", "egnatia",
        "αυτοκινητ", "εγνατ", "vignette", "bgtoll",
    ],
    "Loans & installments": ["tbi bank", "tbi ", "unicredit consumer", "ocean credit", "home credit"],
    "Shipping": ["ekont", "econt", "speedy", "box now", "boxnow", "dhl", "еконт", "спиди"],
    "Home & DIY": ["bauhaus", "praktiker", "mr. bricolage", "mr bricolage", "bricolage", "jysk",
                   "ikea", "kabelsnab", "technomarket", "technopolis"],
    "Sports & fitness": ["decathlon", "athletic fitness", "fitness", "gym"],
    "Personal care": ["hair salon", "salon", "barber", "beauty", "cosmetic", "douglas"],
    "Pets": ["zootrading", "zoo", "petshop", "pet shop"],
    "Groceries": [
        "lidl", "kaufland", "billa", "fantastico", "t market", "tmarket", "carrefour", "aldi",
        "spar", "metro", "supermarket", "grocery", "cba", "хит", "лидл", "кауфланд", "билла",
        "фантастико", "супермаркет", "market", "prosto myasto", "az mesaria", "mesaria",
        "hleboproiz", "pekarna", "mesar",
    ],
    "Eating out": [
        "glovo", "takeaway", "foodpanda", "wolt", "mcdonald", "kfc", "burger king", "subway",
        "starbucks", "costa", "restaurant", "restorant", "cafe", "coffee", "pizza", "domino",
        "sushi", "bakery", "bar", "pub", "grill", "ресторант", "кафе", "пекарна", "пицерия",
        "gelato", "street food", "wok to walk", "roma i napoli", "pastry", "thefries",
        "barzo hranene", "fries", "burger",
    ],
    "Fuel": [
        "omv", "shell", "lukoil", "eko", "petrol", "gas station", "fuel", "gazprom", "elin",
        "лукойл", "бензиностанция", "газстанция",
    ],
    "Transport": [
        "uber", "bolt", "taxi", "flixbus", "bdz", "sofia metro", "metropolitan", "sofiaplan",
        "urban mobility", "parking", "easypay parking", "такси", "метро", "бдж",
        "budapestgo", "public transport", "transport",
    ],
    "Utilities & bills": [
        "electrohold", "cez", "evn", "energo-pro", "energo pro", "toplofikacia", "toplofikaciq",
        "sofiyska voda", "vik ", "vivacom", "yettel", "telenor", "a1 ", "mtel", "bulgargaz",
        "internet", "electricity", "water bill", "ток", "вода", "топлофикация", "виваком",
        "йеттел", "теленор",
    ],
    "Subscriptions": [
        "netflix", "spotify", "youtube", "apple.com", "icloud", "google", "openai", "chatgpt",
        "microsoft", "disney", "hbo", "prime video", "github", "patreon", "dropbox", "adobe",
    ],
    "Shopping": [
        "amazon", "aliexpress", "temu", "ikea", "zara", "h&m", "decathlon", "emag", "ozone",
        "ardes", "jysk", "mr bricolage", "praktiker", "dm ", "ebay", "shein", "pepco", "tedi",
        "sinsay", "reserved", "ozone.bg",
    ],
    "Health": [
        "pharmacy", "apteka", "sopharmacy", "subra", "marvel", "dental", "clinic", "hospital",
        "doctor", "optic", "аптека", "болница", "клиника", "зъболекар", "medica", "velaclinic",
    ],
    "Entertainment": [
        "cinema", "steam", "playstation", "xbox", "eventim", "epic games", "theatre", "theater",
        "ticket", "кино", "театър", "hippoland",
    ],
    "Travel": [
        "booking.com", "airbnb", "ryanair", "wizz", "airlines", "airways", "hotel", "hostel",
        "expedia", "skyscanner", "lufthansa", "хотел", "camp", "akvapark", "gold beach", "beach",
        "zorkadi",
    ],
}

INCOME_KEYWORDS = ["salary", "payroll", "wage", "заплата", "възнаграждение"]

_COMPILED = {
    category: [re.compile(r"(?<!\w)" + re.escape(word.strip())) for word in words]
    for category, words in CATEGORY_RULES.items()
}
_INCOME = [re.compile(r"(?<!\w)" + re.escape(word)) for word in INCOME_KEYWORDS]


def _normalise_type(tx_type):
    return re.sub(r"[\s_\-]", "", (tx_type or "").upper())


def normalise_text(value):
    return " ".join(str(value or "").lower().split())


def categorise(description, tx_type, kind, user_rules=()):
    """Return a category name, or UNSORTED when no rule matches.

    user_rules is an iterable of (pattern, category) with normalised patterns; they take
    priority over the built-in defaults above.
    """
    text = normalise_text(description)
    for pattern, category in user_rules:
        if pattern and pattern in text:
            return category
    norm_type = _normalise_type(tx_type)
    if norm_type == "TOPUP":
        return "Top-up"
    if norm_type == "TRANSFER":
        if text.startswith("transfer to"):
            return "Transfers out"
        if text.startswith("transfer from"):
            return "Transfers in"
    if norm_type == "REWARD":
        return "Refunds"
    if kind == "income":
        if any(p.search(text) for p in _INCOME):
            return "Income"
        if "REFUND" in norm_type:
            return "Refunds"
        return UNSORTED
    if norm_type == "ATM":
        return "Cash"
    if norm_type == "FEE":
        return "Fees"
    for category, patterns in _COMPILED.items():
        if any(p.search(text) for p in patterns):
            return category
    return UNSORTED
