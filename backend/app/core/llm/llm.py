from enum import Enum


class LLMProvider(str, Enum):
    """LLM Provider types."""
    OPENAI = "openai"
    AZURE = "azure"
    VLLM = "vllm"
    TONGYI = "tongyi"
    EMBEDDING = "embedding"  # New type for embedding
