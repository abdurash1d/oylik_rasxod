from app.models.categories import CATEGORY_LABELS_RU, CategoryKey, category_options


def test_category_labels_present():
    assert CATEGORY_LABELS_RU[CategoryKey.TRANSPORTATION] == "Транспорт"
    assert CATEGORY_LABELS_RU[CategoryKey.OTHERS] == "Другое"


def test_category_options_length():
    opts = category_options()
    assert len(opts) == 10
    assert any(item["key"] == "housing" for item in opts)
