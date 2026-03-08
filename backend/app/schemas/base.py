from pydantic import BaseModel, Field


class BaseEditDTO(BaseModel):
    id: int = Field(..., description="Resource ID")
