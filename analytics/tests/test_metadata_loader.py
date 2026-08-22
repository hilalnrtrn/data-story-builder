from app.config.metadata_loader import load_dataset_metadata


def test_load_dataset_metadata_returns_expected_dataset():
    metadata = load_dataset_metadata()

    assert metadata["dataset"]["name"] == "NovaRetail Sales Performance"
    assert metadata["dataset"]["frequency"] == "DAILY"
    assert metadata["dataset"]["grain"] == [
        "Date",
        "Region",
        "Product",
        "Channel",
    ]


def test_discount_metadata_matches_data_dictionary():
    metadata = load_dataset_metadata()
    discount = metadata["columns"]["Discount"]

    assert discount["role"] == "METRIC"
    assert discount["metricType"] == "RATIO"
    assert discount["aggregation"] == "AVG"
    assert discount["nullable"] is False
    assert discount["negativeAllowed"] is False
    assert discount["min"] == 0.0
    assert discount["max"] == 0.5


def test_region_metadata_preserves_canonical_values():
    metadata = load_dataset_metadata()

    assert metadata["columns"]["Region"]["validValues"] == [
        "Marmara",
        "Ege",
        "İç Anadolu",
        "Akdeniz",
        "Karadeniz",
    ]


def test_product_category_mapping_contains_expected_relationship():
    metadata = load_dataset_metadata()

    mapping = metadata["relationships"]["productCategoryMapping"]

    assert mapping["Smart Watch"] == "Electronics"
    assert mapping["Office Chair"] == "Office"


def test_returns_cross_column_rule_is_defined():
    metadata = load_dataset_metadata()

    rules = metadata["crossColumnRules"]

    assert {
        "code": "RETURNS_NOT_GREATER_THAN_QUANTITY",
        "leftColumn": "Returns",
        "operator": "<=",
        "rightColumn": "Quantity",
    } in rules