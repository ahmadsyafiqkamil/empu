from empu.ask.index import Evidence, IndexEntry
from empu.ask.prompts import ASK_PROMPT_VERSION, RESPONSE_SCHEMA, build_prompt, format_rows


def _row(id: int, term: str, *, source: str = "speech", status: str = "accepted",
         variants: tuple[str, ...] = (), quote: str = "contoh kalimat") -> IndexEntry:
    return IndexEntry(
        id=id,
        term=term,
        category="tool",
        stage_id="nglowong",
        gloss_id="arti",
        gloss_en="meaning",
        status=status,
        variants=variants,
        evidence=(Evidence(source=source, quote=quote, t_start=134.0),),
    )


def test_prompt_lists_every_row_id_and_source_label():
    rows = [_row(1, "canting"), _row(2, "nglorod", source="visual_only")]

    prompt = build_prompt(rows, "apa itu canting?", pack_name="batik", scope="public")

    assert "id=1" in prompt
    assert "id=2" in prompt
    assert "speech@" in prompt
    assert "visual_only@" in prompt


def test_prompt_forbids_outside_knowledge_and_requires_ids():
    prompt = build_prompt([_row(1, "canting")], "apa itu canting?", pack_name="batik",
                          scope="public")
    assert "HANYA dari daftar istilah" in prompt
    assert "Jangan menambah pengetahuan dari luar daftar" in prompt
    assert "entry_ids" in prompt
    assert "insufficient" in prompt


def test_prompt_includes_status_only_for_studio_scope():
    rows = [_row(1, "canting", status="proposed")]

    public = build_prompt(rows, "q", pack_name="batik", scope="public")
    studio = build_prompt(rows, "q", pack_name="batik", scope="studio")

    assert "status=" not in public
    assert "status=proposed" in studio


def test_prompt_is_deterministic():
    rows = [_row(1, "a"), _row(2, "b")]
    once = build_prompt(rows, "q", pack_name="p", scope="public")
    twice = build_prompt(rows, "q", pack_name="p", scope="public")
    assert once == twice


def test_prompt_version_is_pinned():
    assert ASK_PROMPT_VERSION == "ask-v1"


def test_format_rows_is_one_line_per_entry():
    rows = [_row(1, "canting"), _row(2, "mori", variants=("mori", "kain putih"))]
    lines = format_rows(rows, scope="public").splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("- id=1 |")
    assert "varian=kain putih" in lines[1]


def test_response_schema_is_strict_and_pins_the_four_keys():
    assert RESPONSE_SCHEMA["additionalProperties"] is False
    assert RESPONSE_SCHEMA["required"] == ["answer", "lang", "entry_ids", "insufficient"]
    assert RESPONSE_SCHEMA["properties"]["lang"]["enum"] == ["id", "en", "jv", "other"]
    assert RESPONSE_SCHEMA["properties"]["entry_ids"]["items"]["type"] == "integer"
