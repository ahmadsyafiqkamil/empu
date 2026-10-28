import pytest
from fakes import analysis, muse_term

from empu.enums import TimeSource
from empu.pipeline.merge import Canonicalizer, collect_occurrences
from empu.pipeline.transcribe import Word, realign, transcribe_cached

WORDS = [
    Word(130.0, 130.4, "lalu"),
    Word(130.5, 131.0, "kita"),
    Word(131.1, 131.6, "rebus"),
    Word(162.0, 162.3, "pakai"),
    Word(162.4, 162.8, "watera"),
    Word(162.9, 163.3, "gelas"),
    Word(163.4, 163.6, "biar"),
    Word(163.7, 164.2, "warnanya"),
    Word(164.3, 164.6, "kuat"),
]


@pytest.fixture(scope="module")
def canon(pack):
    return Canonicalizer(pack)


def occs_for(canon, **kw):
    return collect_occurrences([analysis(2, 130, 205, terms=[muse_term(**kw)])], canon)


def test_realign_moves_shifted_speech_to_asr_time(canon):
    occs = occs_for(
        canon,
        term="waterglass",
        spoken="waterglass",
        t_start=12,
        t_end=13,
        evidence_quote="pakai waterglass biar warnanya kuat",
    )
    (o,) = realign(occs, WORDS)
    assert (o.t_start, o.t_end) == (162.4, 163.3)
    assert o.time_source is TimeSource.asr and o.asr_score >= 80


def test_no_match_keeps_muse_time(canon):
    occs = occs_for(
        canon,
        term="soda abu",
        t_start=12,
        t_end=13,
        evidence_quote="tambahkan soda abu sedikit",
    )
    (o,) = realign(occs, WORDS)
    assert (o.t_start, o.time_source) == (142, TimeSource.muse)


def test_outside_window_keeps_muse_time(canon):
    occs = occs_for(
        canon,
        term="waterglass",
        t_start=12,
        t_end=13,
        evidence_quote="pakai waterglass biar warnanya kuat",
    )
    (o,) = realign(occs, WORDS, window_s=10)
    assert o.time_source is TimeSource.muse


def test_non_speech_untouched(canon):
    occs = occs_for(
        canon,
        term="waterglass",
        source="on_screen_text",
        t_start=12,
        t_end=13,
        evidence_quote="pakai waterglass biar warnanya kuat",
    )
    (o,) = realign(occs, WORDS)
    assert o.time_source is TimeSource.muse and o.t_start == 142


def test_empty_quote_falls_back_to_spoken(canon):
    words = [
        Word(150.0, 150.5, "ini"),
        Word(150.6, 151.2, "spang"),
        Word(151.3, 151.7, "king"),
    ]
    occs = occs_for(
        canon,
        term="spangkring",
        spoken="spangkring",
        t_start=10,
        t_end=11,
        evidence_quote="",
    )
    (o,) = realign(occs, words)
    assert (o.t_start, o.t_end, o.time_source) == (150.6, 151.7, TimeSource.asr)


def test_empty_transcript_is_noop(canon):
    occs = occs_for(
        canon,
        term="waterglass",
        t_start=12,
        t_end=13,
        evidence_quote="pakai waterglass",
    )
    assert realign(occs, [])[0].time_source is TimeSource.muse


def test_transcribe_cached_calls_once(tmp_path):
    media = tmp_path / "a.mp4"
    media.write_bytes(b"audio")
    calls = []

    def fake(path):
        calls.append(path)
        return [Word(0.0, 0.5, "halo")]

    a = transcribe_cached(media, fake, cache_root=tmp_path / "asr", model_name="small")
    b = transcribe_cached(media, fake, cache_root=tmp_path / "asr", model_name="small")
    assert a == b == [Word(0.0, 0.5, "halo")] and len(calls) == 1
