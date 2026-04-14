"""Built-in pipeline components. Auto-discovered by the registry."""

# Import all components so they self-register via decorators
from app.core.rag.pipeline.components.begin import BeginComponent
from app.core.rag.pipeline.components.categorize import CategorizeComponent
from app.core.rag.pipeline.components.llm_component import LLMComponent
from app.core.rag.pipeline.components.message import MessageComponent
from app.core.rag.pipeline.components.retrieval import RetrievalComponent
from app.core.rag.pipeline.components.switch import SwitchComponent

__all__ = [
    "BeginComponent",
    "LLMComponent",
    "RetrievalComponent",
    "MessageComponent",
    "CategorizeComponent",
    "SwitchComponent",
]
