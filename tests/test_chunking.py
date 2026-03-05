from rag_pipeline.chunking import chunk_text


def test_chunk_boundaries_overlap_are_stable() -> None:
    text = " ".join(f"w{i}" for i in range(1, 401))
    chunks = chunk_text(text, doc_id="doc-a", chunk_size=120, overlap=20)

    assert len(chunks) >= 3
    assert chunks[0].doc_id == "doc-a"
    assert chunks[0].start_char == 0
    assert chunks[1].start_char < chunks[0].end_char
    assert chunks[-1].end_char <= len(" ".join(text.split()))
