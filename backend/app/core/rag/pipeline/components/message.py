from __future__ import annotations

from app.core.common.logging import TerraLogUtil as logger
from typing import Any

from app.core.rag.pipeline.base import ComponentBase, ComponentParam
from app.core.rag.pipeline.registry import register_component, register_param



class MessageParam(ComponentParam):
    def __init__(self) -> None:
        super().__init__()
        self.content: str = ""


register_param("Message")(MessageParam)


@register_component("Message")
class MessageComponent(ComponentBase):
    """Output message component. Resolves variable references and produces final text."""

    component_name = "Message"

    async def invoke(self, **kwargs: Any) -> dict[str, Any]:
        param: MessageParam = self._param  # type: ignore[assignment]

        content = self._resolve_template(param.content)

        self.set_output("content", content)
        self._context.set_component_output(self._id, self._outputs)
        logger.info(
            "Message: id=%s, len=%d", self._id, len(content),
        )
        return self._outputs
