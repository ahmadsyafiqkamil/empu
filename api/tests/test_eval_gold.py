from conftest import FIXTURES

from empu.evaluation.gold import load_gold


def test_skips_example_rows():
    rows = load_gold(FIXTURES / "eval/tiny.csv")
    assert [r.term for r in rows] == ["pola", "nyamplung"]
    assert rows[0].source.value == "speech"
    assert rows[1].source.value == "on_screen_text"
