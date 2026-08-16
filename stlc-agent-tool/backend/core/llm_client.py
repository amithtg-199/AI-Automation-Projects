import logging
import psycopg
import json
from typing import Optional, List, Dict, Any, Union
from langchain_core.messages import BaseMessage

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_ollama import ChatOllama

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Basic cost map for fallback logging (cost per 1k tokens in USD)
MODEL_COSTS = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-3-5-sonnet-20240620": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "mistral-large-latest": {"input": 0.002, "output": 0.006},
}

class LLMFactory:
    """
    Constructs LangChain chat models based on provider strings and keys.
    """
    @staticmethod
    def create_model(provider: str, model_name: str, api_key: str, **kwargs):
        provider = provider.lower()
        if provider == "openai":
            return ChatOpenAI(model=model_name, api_key=api_key, **kwargs)
        elif provider == "anthropic" or provider == "claude":
            return ChatAnthropic(model=model_name, api_key=api_key, **kwargs)
        elif provider == "google" or provider == "gemini":
            return ChatGoogleGenerativeAI(model=model_name, api_key=api_key, **kwargs)
        elif provider == "mistral":
            return ChatMistralAI(model=model_name, api_key=api_key, **kwargs)
        elif provider == "ollama":
            # For Ollama, the api_key is usually ignored, but we pass base_url
            base_url = settings.OLLAMA_ENDPOINT
            return ChatOllama(model=model_name, base_url=base_url, **kwargs)
        elif provider == "deepseek":
            # Deepseek is typically OpenAI-compatible
            return ChatOpenAI(model=model_name, api_key=api_key, base_url="https://api.deepseek.com/v1", **kwargs)
        elif provider == "kimi":
            # Moonshot/Kimi is typically OpenAI-compatible
            return ChatOpenAI(model=model_name, api_key=api_key, base_url="https://api.moonshot.cn/v1", **kwargs)
        elif provider == "self_hosted":
            base_url = getattr(settings, "SELF_HOSTED_LLM_BASE_URL", "http://localhost:8000/v1")
            return ChatOpenAI(model=model_name, api_key="EMPTY", base_url=base_url, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM Provider: {provider}")

class CentralizedLLMClient:
    """
    Wraps LangChain Chat Models with a Factory + Fallback pattern to enforce centralized audit logging and cost tracking.
    """
    def __init__(self, username: str, project_name: str, agent_name: str, model_name: Optional[str] = None, provider: Optional[str] = None):
        self.username = username
        self.project_name = project_name
        self.agent_name = agent_name
        
        # Determine routing
        is_self_hosted_enabled = getattr(settings, "SELF_HOSTED_LLM_ENABLED", False)
        
        # Hardcoded dictionary mimicking the "agent_model_routing" Postgres table
        # Defaults routing logic mentioned in spec:
        agent_routing = {
            "rag_retrieval": {"provider": "self_hosted", "model": getattr(settings, "SELF_HOSTED_LLM_MODEL", "meta-llama/Llama-2-7b-chat-hf")},
            "knowledge_hub": {"provider": "self_hosted", "model": getattr(settings, "SELF_HOSTED_LLM_MODEL", "meta-llama/Llama-2-7b-chat-hf")}
        }
        
        route = agent_routing.get(agent_name)
        if route and is_self_hosted_enabled:
            self.provider = route["provider"]
            self.model_name = route["model"]
        else:
            self.provider = (provider or settings.LLM_PROVIDER).lower()
            self.model_name = model_name or settings.LLM_MODEL
        
        self.llm = self._build_model_chain()

    def _get_api_keys(self) -> List[str]:
        """
        Parses LLM_API_KEY from settings. It could be a simple string or a JSON mapping.
        """
        raw_key = settings.LLM_API_KEY
        if not raw_key:
            return ["empty"]
            
        try:
            # Assumes it was decrypted somewhere, but here we just use it directly
            # since config.py doesn't automatically decrypt pydantic fields.
            decrypted = settings.decrypt_secret(raw_key)
            
            # Try to parse as JSON
            key_data = json.loads(decrypted)
            if isinstance(key_data, dict):
                # E.g. {"openai": ["key1", "key2"]} or {"openai": "key1"}
                keys = key_data.get(self.provider)
                if not keys:
                    return ["empty"]
                return keys if isinstance(keys, list) else [keys]
            elif isinstance(key_data, list):
                return key_data
            else:
                return [str(key_data)]
        except Exception:
            # If it's not JSON, assume it's just a raw single key
            return [raw_key]

    def _build_model_chain(self):
        keys = self._get_api_keys()
        
        # Build the primary model using the first key
        primary_model = LLMFactory.create_model(self.provider, self.model_name, keys[0])
        
        # Build fallbacks if multiple keys exist
        fallbacks = []
        if len(keys) > 1:
            for key in keys[1:]:
                fallback_model = LLMFactory.create_model(self.provider, self.model_name, key)
                fallbacks.append(fallback_model)
                
        # If fallbacks exist, chain them
        if fallbacks:
            # Langchain's with_fallbacks will catch standard RequestExceptions (like 429s) and retry
            return primary_model.with_fallbacks(fallbacks)
            
        return primary_model

    def invoke(self, messages: List[BaseMessage], **kwargs) -> BaseMessage:
        """
        Synchronous invocation of the LLM.
        """
        response = self.llm.invoke(messages, **kwargs)
        self._extract_and_log_cost(response)
        return response

    async def ainvoke(self, messages: List[BaseMessage], **kwargs) -> BaseMessage:
        """
        Asynchronous invocation of the LLM.
        """
        response = await self.llm.ainvoke(messages, **kwargs)
        self._extract_and_log_cost(response)
        return response

    def _extract_and_log_cost(self, response: BaseMessage):
        usage_metadata = getattr(response, "response_metadata", {}).get("token_usage", {})
        if not usage_metadata:
            # Some providers structure metadata differently (e.g. Anthropic)
            usage_metadata = getattr(response, "usage_metadata", {}) or {}
            
        input_tokens = usage_metadata.get("prompt_tokens", usage_metadata.get("input_tokens", 0))
        output_tokens = usage_metadata.get("completion_tokens", usage_metadata.get("output_tokens", 0))
        
        # Sometimes it's in response_metadata directly
        if input_tokens == 0 and output_tokens == 0:
            meta = getattr(response, "response_metadata", {})
            input_tokens = meta.get("input_tokens", 0)
            output_tokens = meta.get("output_tokens", 0)
        
        self._log_cost(input_tokens, output_tokens)

    def _log_cost(self, input_tokens: int, output_tokens: int):
        cost_usd = 0.0
        if self.model_name in MODEL_COSTS:
            cost_usd = (
                (input_tokens / 1000.0) * MODEL_COSTS[self.model_name]["input"] +
                (output_tokens / 1000.0) * MODEL_COSTS[self.model_name]["output"]
            )
            
        try:
            with psycopg.connect(settings.POSTGRES_URL, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO token_cost_logs 
                        (username, project_name, agent_name, provider, model, input_tokens, output_tokens, cost_usd)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (self.username, self.project_name, self.agent_name, self.provider, self.model_name, input_tokens, output_tokens, cost_usd)
                    )
        except Exception as e:
            logger.error(f"Failed to log LLM token cost: {e}")
