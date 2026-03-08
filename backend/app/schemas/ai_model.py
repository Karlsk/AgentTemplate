
from typing import List
from pydantic import BaseModel, Field

from app.schemas.base import BaseEditDTO


class AiModelItem(BaseModel):
    name: str = Field(description=f"model_name")
    base_model: str = Field(description=f"base_model")
    supplier: int = Field(description=f"supplier")
    protocol: int = Field(description=f"protocol")
    default_model: bool = Field(
        default=False, description=f"default_model")
    # 'chat' or 'embedding'
    llm_type: str = Field(
        default='chat', description=f"llm_type")
    # Whether this model is a backup model
    backup_model: bool = Field(
        default=False, description=f"backup_model")


class AiModelGridItem(AiModelItem, BaseEditDTO):
    pass


class AiModelConfigItem(BaseModel):
    key: str = Field(description=f"arg_name")
    val: object = Field(description=f"arg_val")
    name: str = Field(description=f"arg_show_name")


class AiModelCreator(AiModelItem):
    api_domain: str = Field(description=f"api_domain")
    api_key: str = Field(description=f"api_key")
    config_list: List[AiModelConfigItem] = Field(
        description=f"config_list")


class AiModelEditor(AiModelCreator, BaseEditDTO):
    pass
