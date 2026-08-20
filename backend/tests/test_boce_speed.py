from app.boce_speed import pick_overseas_node_ids, summarize_rows


def test_pick_overseas_nodes_prefers_known_markets() -> None:
    nodes = [
        {"id": 1, "node_name": "河北", "isp_name": "电信"},
        {"id": 2, "node_name": "美国洛杉矶", "isp_name": ""},
        {"id": 3, "node_name": "香港", "isp_name": "BGP"},
        {"id": 4, "node_name": "新加坡", "isp_name": ""},
        {"id": 5, "node_name": "德国", "isp_name": ""},
    ]
    assert pick_overseas_node_ids(nodes, limit=3) == ["2", "3", "4"]


def test_summarize_rows_keeps_open_time_not_pagespeed_score() -> None:
    result = summarize_rows(
        "https://www.example.com/",
        [
            {"node_name": "香港", "error_code": 0, "http_code": 200, "time_total": 0.82},
            {"node_name": "美国", "error_code": 1, "error": "timeout"},
        ],
    )
    assert result["performance_score"] is None
    assert result["lcp_ms"] == 820
    assert result["inp_ms"] == 820
    assert "通 1/2" in result["detail"]
    assert "香港 200 820ms" in result["detail"]
    assert "美国 失败：timeout" in result["detail"]
