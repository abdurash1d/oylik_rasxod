from enum import Enum


class CategoryKey(str, Enum):
    TRANSPORTATION = "transportation"
    MARKET = "market"
    HEALTH = "health"
    SHOPPING = "shopping"
    PERSONAL_CARE = "personal_care"
    MISCELLANEOUS = "miscellaneous"
    FOOD_GROCERIES = "food_groceries"
    UTILITIES = "utilities"
    HOUSING = "housing"
    OTHERS = "others"


CATEGORY_LABELS_RU = {
    CategoryKey.TRANSPORTATION: "Транспорт",
    CategoryKey.MARKET: "Маркет",
    CategoryKey.HEALTH: "Здоровье",
    CategoryKey.SHOPPING: "Покупки",
    CategoryKey.PERSONAL_CARE: "Личный уход",
    CategoryKey.MISCELLANEOUS: "Разное",
    CategoryKey.FOOD_GROCERIES: "Еда и продукты",
    CategoryKey.UTILITIES: "Коммунальные услуги",
    CategoryKey.HOUSING: "Жилье",
    CategoryKey.OTHERS: "Другое",
}


CATEGORY_LABELS_UZ = {
    CategoryKey.TRANSPORTATION: "Transport",
    CategoryKey.MARKET: "Market",
    CategoryKey.HEALTH: "Sog‘liq",
    CategoryKey.SHOPPING: "Xaridlar",
    CategoryKey.PERSONAL_CARE: "Shaxsiy parvarish",
    CategoryKey.MISCELLANEOUS: "Turli",
    CategoryKey.FOOD_GROCERIES: "Oziq-ovqat",
    CategoryKey.UTILITIES: "Kommunal to‘lovlar",
    CategoryKey.HOUSING: "Uy-joy",
    CategoryKey.OTHERS: "Boshqa",
}


def category_options():
    return [
        {"key": key.value, "label_ru": CATEGORY_LABELS_RU[key], "label_uz": CATEGORY_LABELS_UZ[key]}
        for key in CategoryKey
    ]
