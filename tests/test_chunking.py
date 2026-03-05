from rag_pipeline.chunking import chunk_text


def test_paragraph_strategy_splits_oversized_paragraph_into_multiple_chunks() -> None:
    text = "A" * 120

    chunks = chunk_text(
        text,
        doc_id="doc-1",
        strategy="paragraph",
        chunk_size=50,
        overlap=10,
    )

    assert len(chunks) == 3
    assert all(len(chunk.text) <= 50 for chunk in chunks)
    assert [chunk.start for chunk in chunks] == [0, 40, 80]
    assert [chunk.end for chunk in chunks] == [50, 90, 120]
