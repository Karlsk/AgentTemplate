"""Document parser facade.

Delegates to the pluggable parser registry (``parsers`` package).
Maintains backward-compatible ``parse_file`` and ``SUPPORTED_FILE_TYPES``
exports used by the ingestion pipeline and RAG service.
"""

import os
from typing import List

from llama_index.core.schema import Document

from app.core.common.logging import TerraLogUtil
from app.core.rag.ingestion import parsers  # noqa: F401  triggers auto-registration
from app.core.rag.ingestion.parsers import registry

# Dynamic set — grows when custom parsers are registered at runtime.
SUPPORTED_FILE_TYPES = registry.supported_extensions()


def parse_file(file_path: str, file_type: str) -> List[Document]:
    """Parse a file into LlamaIndex Document objects.

    Uses the registered parser for the given file type.

    Args:
        file_path: Absolute path to the file.
        file_type: Extension without dot (e.g. "pdf").

    Returns:
        List of LlamaIndex Document objects.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file type is unsupported.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = file_type.lower().lstrip(".")

    # Re-check live extensions in case parsers were registered after import
    current_exts = registry.supported_extensions()
    if ext not in current_exts:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            f"Supported: {', '.join(sorted(current_exts))}"
        )

    parser = registry.get_by_ext(ext)
    docs = parser.parse(file_path)

    TerraLogUtil.info(
        "file_parsed",
        file_path=file_path,
        file_type=ext,
        parser=parser.name,
        doc_count=len(docs),
    )
    return docs
