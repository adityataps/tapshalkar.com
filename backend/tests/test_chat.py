import pytest
from app.core.chat import search_graph

SAMPLE_GRAPH = {
    "nodes": [
        {"id": "skill-python", "type": "skill", "label": "Python", "description": "Primary language", "metadata": {}},
        {"id": "skill-fastapi", "type": "skill", "label": "FastAPI", "description": "Python web framework", "metadata": {}},
        {"id": "project-portfolio", "type": "project", "label": "Portfolio Site", "description": "This site", "metadata": {}},
    ],
    "edges": [
        {"source": "skill-python", "target": "project-portfolio", "type": "used_in", "weight": 1.0},
        {"source": "skill-fastapi", "target": "project-portfolio", "type": "used_in", "weight": 0.9},
    ]
}


def test_search_graph_finds_by_label():
    nodes, ids, edges = search_graph("python", SAMPLE_GRAPH)
    assert any(n["id"] == "skill-python" for n in nodes)
    assert "skill-python" in ids


def test_search_graph_returns_connected_edges():
    nodes, ids, edges = search_graph("portfolio", SAMPLE_GRAPH)
    assert "project-portfolio" in ids
    # edges where BOTH endpoints are in matched ids are not returned here
    # since skill nodes aren't matched, but the function returns edges
    # between matched nodes only


def test_search_graph_case_insensitive():
    nodes, ids, edges = search_graph("FASTAPI", SAMPLE_GRAPH)
    assert "skill-fastapi" in ids


def test_search_graph_returns_empty_on_no_match():
    nodes, ids, edges = search_graph("nonexistent-xyz", SAMPLE_GRAPH)
    assert nodes == []
    assert ids == []
    assert edges == []


def test_search_graph_caps_at_ten_results():
    big_graph = {
        "nodes": [{"id": f"skill-{i}", "type": "skill", "label": f"skill {i}", "description": "", "metadata": {}} for i in range(20)],
        "edges": []
    }
    nodes, ids, edges = search_graph("skill", big_graph)
    assert len(nodes) <= 10
