from empu.text import normalize


def test_normalize_casefold_punct_space():
    assert normalize("  Isen-Isen!! ") == "isen isen"
    assert normalize("HCl") == "hcl"
    assert normalize("snake_case_id") == "snake case id"
    assert normalize("Ngelorot,") == "ngelorot"


def test_normalize_empty():
    assert normalize(None) == ""
    assert normalize("") == ""
    assert normalize("  -- ") == ""
