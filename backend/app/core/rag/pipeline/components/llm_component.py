from __future__ import annotations

from app.core.common.logging import TerraLogUtil as logger
from typing import Any

from app.core.common.config import settings
from app.core.llm.openai.llm import BaseChatOpenAI as OpenAIChat
from app.core.rag.pipeline.base import ComponentBase, ComponentParam
from app.core.rag.pipeline.registry import register_component, register_param



class LLMParam(ComponentParam):
    def __init__(self) -> None:
        super().__init__()
        self.llm_id: str = ""
        self.sys_prompt: str = ""
        self.prompt_template: str = "{sys.query}"
        self.max_tokens: int = 0
        self.temperature: float = 0.7

    def check(self) -> None:
        if not self.prompt_template:
            raise ValueError("LLM component requires a prompt_template")


register_param("LLM")(LLMParam)


@register_component("LLM")
class LLMComponent(ComponentBase):
    """LLM chat component. Sends a prompt (with variable resolution) to an LLM."""

    component_name = "LLM"

    async def invoke(self, **kwargs: Any) -> dict[str, Any]:
        param: LLMParam = self._param  # type: ignore[assignment]

        prompt = self._resolve_template(param.prompt_template)

        messages: list[dict[str, str]] = []
        if param.sys_prompt:
            sys_prompt = self._resolve_template(param.sys_prompt)
            messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": prompt})

        model = param.llm_id or "gpt-4o-mini"
        llm = OpenAIChat(
            model=model,
            api_key=getattr(settings, "OPENAI_API_KEY", "") or "Empty",
            base_url=getattr(settings, "OPENAI_BASE_URL", None),
        )

        llm_kwargs: dict[str, Any] = {}
        if param.max_tokens > 0:
            llm_kwargs["max_tokens"] = param.max_tokens
        if param.temperature >= 0:
            llm_kwargs["temperature"] = param.temperature

        try:
            resp = await llm.ainvoke(messages, **llm_kwargs)
            content = resp.content

        except Exception as e:
            self._error = str(e)
            content = ""
            logger.exception("rag_llm_invoke_failed", component_id=self._id)

        self.set_output("content", content)
        self._context.set_component_output(self._id, self._outputs)
        return self._outputs
