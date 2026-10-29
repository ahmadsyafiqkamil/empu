from empu.enums import Source
from empu.evaluation.baseline import baseline_against_pack, parse_vtt


def test_parse_vtt(tmp_path):
    p = tmp_path / "a.vtt"
    p.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nspang King\n")
    cues = parse_vtt(p)
    assert cues[0].spoken == "spang King"
    assert abs(cues[0].t_start - 1.0) < 0.01


def test_parse_vtt_multiple_cues_and_header(tmp_path):
    p = tmp_path / "a.vtt"
    p.write_text(
        "WEBVTT\n"
        "Kind: captions\n"
        "Language: id\n"
        "\n"
        "00:00:01.000 --> 00:00:03.000 align:start position:0%\n"
        "nyamplung\n"
        "\n"
        "00:01:02.500 --> 00:01:04.000\n"
        "kain\n"
        "mori\n"
    )
    cues = parse_vtt(p)
    assert [c.spoken for c in cues] == ["nyamplung", "kain mori"]
    assert cues[1].t_start == 62.5
    assert cues[1].t_end == 64.0
    assert all(c.source is Source.speech and c.pack_term_id is None for c in cues)


def test_parse_vtt_comma_timestamps_and_note(tmp_path):
    p = tmp_path / "a.vtt"
    p.write_text(
        "WEBVTT\n"
        "\n"
        "NOTE ini bukan ucapan\n"
        "\n"
        "00:00:07,000 --> 00:00:09,500\n"
        "malam\n"
    )
    cues = parse_vtt(p)
    assert [c.spoken for c in cues] == ["malam"]
    assert cues[0].t_start == 7.0
    assert cues[0].t_end == 9.5


def test_parse_vtt_empty_file(tmp_path):
    p = tmp_path / "a.vtt"
    p.write_text("WEBVTT\n")
    assert parse_vtt(p) == []


def test_spang_king_resolves_to_spangkring(pack, tmp_path):
    # Brief mengira "spang King" novel. Ternyata pack memuat varian "spang kring"
    # untuk spangkring, dan fuzz.ratio("spang king", "spang kring") = 95.2 >= ambang
    # 90, jadi cocok fuzzy dan baseline memulihkannya. Perilaku ini yang diuji.
    p = tmp_path / "a.vtt"
    p.write_text("WEBVTT\n\n00:02:02.000 --> 00:02:04.000\nspang King\n")
    out = baseline_against_pack(parse_vtt(p), pack)
    assert len(out) == 1
    assert out[0].term == "spangkring"
    assert out[0].pack_term_id == "spangkring"
    assert out[0].spoken == "spang King"
    assert out[0].t_start == 122.0
    assert out[0].t_end == 124.0
    assert out[0].source is Source.speech


def test_novel_cues_dropped(pack, tmp_path):
    p = tmp_path / "a.vtt"
    p.write_text(
        "WEBVTT\n"
        "\n"
        "00:00:05.000 --> 00:00:07.000\n"
        "selamat pagi semuanya\n"
        "\n"
        "00:00:10.000 --> 00:00:12.000\n"
        "canting\n"
        "\n"
        "00:00:20.000 --> 00:00:22.000\n"
        "terima kasih sudah menonton\n"
    )
    out = baseline_against_pack(parse_vtt(p), pack)
    assert [c.term for c in out] == ["canting"]
    assert out[0].pack_term_id == "canting"
