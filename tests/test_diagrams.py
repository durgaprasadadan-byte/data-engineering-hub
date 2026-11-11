from src.diagrams.definitions import ARCHITECTURES, to_dot, to_mermaid


def test_four_architectures_defined():
    assert set(ARCHITECTURES) == {"etl", "elt", "lakehouse", "streaming"}


def test_stage_ids_unique_and_edges_directional():
    for arch in ARCHITECTURES.values():
        ids = [s.id for s in arch.stages]
        assert len(ids) == len(set(ids))
        assert to_mermaid(arch).count("-->") == len(ids) - 1
        assert to_dot(arch).count("->") == len(ids) - 1


def test_highlight_applied():
    arch = ARCHITECTURES["etl"]
    assert "style trf" in to_mermaid(arch, "trf")
    assert "style" not in to_mermaid(arch)


def test_required_flows():
    labels = [s.label for s in ARCHITECTURES["streaming"].stages]
    assert labels == ["Data Sources", "Kafka", "Spark Structured Streaming", "Delta Lake", "Monitoring"]
    assert [s.label for s in ARCHITECTURES["elt"].stages][3:6] == ["Bronze", "Silver", "Gold"]
