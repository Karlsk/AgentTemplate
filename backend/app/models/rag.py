"""RAG Instance model for storing RAG configurations and collection metadata."""

from typing import Optional
from sqlalchemy import Column, Integer, String, Text, BigInteger
from sqlmodel import Field
from app.models.base import BaseModel


class RagInstanceModel(BaseModel, table=True):
    """RagInstance model for storing RAG instances.

    Each instance corresponds to a unique vector collection in Milvus.

    Attributes:
        id: The primary key
        workspace_id: The workspace ID for data isolation
        name: Name of the RAG instance
        collection_name: The name of the collection in Milvus (instance_{id})
        embedding_model_id: Foreign key to AiModelDetail
        config: JSON string for additional RAG configurations
    """

    __tablename__ = "rag_instances"

    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(sa_column=Column(BigInteger, index=True, nullable=False))
    name: str = Field(sa_column=Column(String(255), nullable=False))
    collection_name: str = Field(sa_column=Column(String(255), unique=True, nullable=False))
    embedding_model_id: int = Field(sa_column=Column(Integer, nullable=False))
    config: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
