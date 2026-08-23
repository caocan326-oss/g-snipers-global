from types import SimpleNamespace

from app.geo_loop import (
    compare_prompt_note,
    kinds_from_sample_rows,
    sample_reason_for_ticket,
)


def _row(
    *,
    engine: str,
    mentioned: bool = False,
    owned: list[str] | None = None,
    third: list[str] | None = None,
    competitors: str = "",
):
    import json

    return SimpleNamespace(
        engine=engine,
        mentioned=mentioned,
        owned_citations_json=json.dumps(owned or []),
        third_party_citations_json=json.dumps(third or []),
        competitor_hits=competitors,
    )


def test_kinds_no_owned_only_when_overseas_mentioned_without_site() -> None:
    assert kinds_from_sample_rows(
        [
            _row(engine="tavily", mentioned=True, third=["https://other.example"]),
            _row(engine="bocha", mentioned=False, third=["https://item.jd.com/1"]),
        ]
    ) == ["no_owned"]


def test_kinds_skips_no_owned_when_only_bocha_mentioned() -> None:
    assert (
        kinds_from_sample_rows(
            [
                _row(engine="tavily", mentioned=False),
                _row(engine="bocha", mentioned=True, third=["https://item.jd.com/1"]),
            ]
        )
        == []
    )


def test_kinds_absent_when_nobody_mentioned() -> None:
    assert kinds_from_sample_rows(
        [
            _row(engine="tavily", mentioned=False),
            _row(engine="bocha", mentioned=False, third=["https://item.jd.com/1"]),
        ]
    ) == ["absent"]


def test_kinds_no_ticket_gap_when_owned_present() -> None:
    assert (
        kinds_from_sample_rows(
            [
                _row(engine="tavily", mentioned=True, owned=["https://www.ugreen.com/x"]),
                _row(engine="bocha", mentioned=True, third=["https://item.jd.com/1"]),
            ]
        )
        == []
    )


def test_ticket_reason_names_overseas_gap_not_shop_fight() -> None:
    rows = [
        _row(engine="tavily", mentioned=True),
        _row(engine="bocha", mentioned=False, third=["https://item.jd.com/1"]),
    ]
    reason = sample_reason_for_ticket(rows, "no_owned")
    assert "海外联网源提到了品牌" in reason
    assert "没有给出客户官网" in reason
    assert "Tavily 提到" in reason
    assert "外来网址" not in reason


def test_compare_prompt_ignores_bocha_only_mention_flip() -> None:
    previous = [
        _row(engine="tavily", mentioned=False),
        _row(engine="bocha", mentioned=False, third=["https://item.jd.com/1"]),
    ]
    latest = [
        _row(engine="tavily", mentioned=False),
        _row(engine="bocha", mentioned=True, third=["https://item.jd.com/1", "https://item.jd.com/2"]),
    ]
    note = compare_prompt_note(latest, previous)
    assert "仍没有提到" in note
    assert "两次都没有给出官网" in note
    assert "这次提到了" not in note


def test_compare_prompt_sees_tavily_mention_and_owned() -> None:
    previous = [
        _row(engine="tavily", mentioned=False),
        _row(engine="bocha", mentioned=True, third=["https://item.jd.com/1"]),
    ]
    latest = [
        _row(engine="tavily", mentioned=True, owned=["https://www.ugreen.com/x"]),
        _row(engine="bocha", mentioned=True, third=["https://item.jd.com/1"]),
    ]
    note = compare_prompt_note(latest, previous)
    assert "上次没有提到，这次提到了" in note
    assert "这次给出了疑似官网" in note
