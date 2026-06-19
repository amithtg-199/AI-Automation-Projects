from scripts.config import config
from scripts.logger import get_logger

logger = get_logger(__name__)

def get_llm():
    """
    Returns the appropriate LangChain ChatModel based on config.LLM_PROVIDER.
    """
    provider = config.LLM_PROVIDER.lower()
    model_name = config.LLM_MODEL_NAME
    api_key = config.LLM_API_KEY
    
    timeout = config.LLM_REQUEST_TIMEOUT or None
    max_retries = config.LLM_MAX_RETRIES

    if provider == "mistral":
        from langchain_mistralai import ChatMistralAI
        logger.info(f"Initializing Mistral LLM ({model_name}) max_retries={max_retries}, timeout={timeout}s")
        return ChatMistralAI(
            api_key=api_key, model=model_name,
            max_retries=max_retries, timeout=timeout,
        )
        
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        logger.info(f"Initializing OpenAI LLM ({model_name})")
        return ChatOpenAI(api_key=api_key, model=model_name)
        
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        logger.info(f"Initializing Anthropic LLM ({model_name})")
        return ChatAnthropic(api_key=api_key, model_name=model_name)
        
    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        base_url = config.OLLAMA_BASE_URL
        logger.info(f"Initializing Ollama LLM ({model_name}) at {base_url}")
        return ChatOllama(model=model_name, base_url=base_url)
        
    else:
        logger.warning(f"Unknown LLM provider '{provider}'. Falling back to Mistral.")
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(api_key=api_key, model=model_name)


def get_embeddings():
    """
    Returns the appropriate LangChain Embeddings model based on config.EMBEDDING_PROVIDER.
    """
    provider = config.EMBEDDING_PROVIDER.lower()
    model_name = config.EMBEDDING_MODEL_NAME
    api_key = config.EMBEDDING_API_KEY or config.LLM_API_KEY
    
    if provider == "mistral":
        from langchain_mistralai.embeddings import MistralAIEmbeddings
        logger.info(f"Initializing Mistral Embeddings ({model_name}) max_retries={config.LLM_MAX_RETRIES}")
        return MistralAIEmbeddings(api_key=api_key, model=model_name, max_retries=config.LLM_MAX_RETRIES)
        
    elif provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        logger.info(f"Initializing OpenAI Embeddings ({model_name})")
        return OpenAIEmbeddings(api_key=api_key, model=model_name)
        
    elif provider == "ollama":
        from langchain_community.embeddings import OllamaEmbeddings
        base_url = config.OLLAMA_BASE_URL
        logger.info(f"Initializing Ollama Embeddings ({model_name}) at {base_url}")
        return OllamaEmbeddings(model=model_name, base_url=base_url)
        
    elif provider == "huggingface":
        from langchain_community.embeddings import HuggingFaceEmbeddings
        logger.info(f"Initializing HuggingFace Embeddings ({model_name})")
        return HuggingFaceEmbeddings(model_name=model_name)
        
    else:
        logger.warning(f"Unknown Embedding provider '{provider}'. Falling back to Mistral.")
        from langchain_mistralai.embeddings import MistralAIEmbeddings
        return MistralAIEmbeddings(api_key=api_key, model=model_name)
