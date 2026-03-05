from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf"}


def collect_documents(paths: list[str | Path]) -> dict[str, str]:
    docs: dict[str, str] = {}
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            for file in sorted(path.rglob("*")):
                if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS:
                    docs[str(file)] = load_document(file)
        elif path.is_file():
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise ValueError(f"unsupported extension: {path.suffix}")
            docs[str(path)] = load_document(path)
        else:
            raise ValueError(f"path not found: {path}")
    return docs


def load_document(path: str | Path) -> str:
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        reader = PdfReader(str(p))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = p.read_text(encoding="utf-8", errors="ignore")
    cleaned = text.strip()
    if not cleaned:
        raise ValueError(f"document has no extractable text: {p}")
    return cleaned
