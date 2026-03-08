from tenacity import Retrying, RetryError, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional

from app.core.common.logging import TerraLogUtil
from app.core.common.config import settings
from app.core.llm.model_factory import LLMConfig, LLMFactory, get_default_config, get_backup_config


class LLMService:
    def __init__(self, config: LLMConfig = None, backup_config: LLMConfig = None):
        self.llm_timeout = getattr(settings, "LLM_REQUEST_TIMEOUT", 30)
        self.llm_retry_attempts = getattr(settings, "LLM_RETRY_ATTEMPTS", 2)
        self.backup_config = self._with_timeout(
            backup_config, self.llm_timeout)

        self.config = self._with_timeout(config, self.llm_timeout)

    @classmethod
    async def create(cls, *args, **kwargs):
        config: LLMConfig = await get_default_config()
        backup_config: Optional[LLMConfig] = await get_backup_config('chat')
        instance = cls(*args, **kwargs, config=config,
                       backup_config=backup_config)
        return instance

    @staticmethod
    def _with_timeout(config: Optional[LLMConfig], timeout: int = 30) -> Optional[LLMConfig]:
        if not config:
            return None
        params = dict(
            config.additional_params) if config.additional_params else {}
        params.setdefault("timeout", timeout)
        return config.model_copy(update={"additional_params": params})

    def _set_llm_from_config(self, config: LLMConfig):
        self.config = config
        llm_instance = LLMFactory.create_llm(config)
        self.llm = llm_instance.llm

    def stream_with_retry(self, messages):
        retryer = Retrying(
            stop=stop_after_attempt(self.llm_retry_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=5),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )

        def _call_stream():
            return self.llm.stream(messages)

        try:
            return retryer.call(_call_stream)
        except RetryError as e:
            if self.backup_config:
                TerraLogUtil.info(
                    "Primary LLM failed, switching to backup model")
                self._set_llm_from_config(self.backup_config)
                try:
                    return retryer.call(_call_stream)
                except RetryError as e2:
                    raise e2.last_attempt.exception()
            raise e.last_attempt.exception()
