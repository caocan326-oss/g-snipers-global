from app.ce17_speed import auth_code, summarize_rows, speed_request


def test_auth_code_matches_documented_python_formula() -> None:
    assert auth_code("yiqice@qq.com", "secret", "1700000000") == auth_code("yiqice@qq.com", "secret", "1700000000")
    assert len(auth_code("user@example.com", "pwd", "1")) == 32


def test_speed_request_targets_overseas_nodes() -> None:
    body = speed_request("https://example.com/", node_num=3)
    assert body["TestType"] == "HTTP"
    assert body["areas"] == [2, 3]
    assert body["isps"] == [3]
    assert body["num"] == 3


def test_summarize_rows_keeps_open_time_not_pagespeed_score() -> None:
    result = summarize_rows(
        "https://www.example.com/",
        [
            {"HttpCode": 200, "TotalTime": 0.82, "NodeInfo": {"name": "香港"}},
            {"HttpCode": 500, "TotalTime": 1.4, "NodeInfo": {"name": "美国"}},
        ],
    )
    assert result["performance_score"] is None
    assert result["lcp_ms"] == 820
    assert result["inp_ms"] == 820
    assert "通 1/2" in result["detail"]
    assert "香港 200 820ms" in result["detail"]
    assert "美国 失败" in result["detail"]
