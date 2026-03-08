from sqlmodel import Field, Text, SQLModel

from app.models.base import BaseModel


class AiModelBase:
    supplier: int = Field(nullable=False)  # openai: 1, azure: 2, google: 3
    name: str = Field(max_length=255, nullable=False)
    base_model: str = Field(max_length=255, nullable=False)
    default_model: bool = Field(default=False, nullable=False)
    llm_type: str = Field(max_length=20, nullable=False,
                          default='chat')  # 'chat' or 'embedding'
    # Whether this model is a backup model
    backup_model: bool = Field(default=False, nullable=False)


class AiModelDetail(BaseModel, AiModelBase, table=True):
    __tablename__ = "ai_model"
    id: int = Field(default=None, primary_key=True)
    api_key: str | None = Field(nullable=True)
    api_domain: str = Field(nullable=False)
    # 1: openai-sdk, 2: vllm-sdk
    protocol: int = Field(nullable=False, default=1)
    config: str = Field(sa_type=Text())
    status: int = Field(nullable=False, default=1)
