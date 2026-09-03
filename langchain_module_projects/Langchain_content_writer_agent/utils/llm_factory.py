import os
from typing import Optional
from utils.load_env import load_env

# Import env varibales
load_env()

# Setup LLM Factory
def get_llm(provider: Optional[str] = None):

    provider = (provider or os.getenv("DEFAULT_LLM_PROVIDER", "mistral")).lower()
    try:
        if provider == "mistral":
            from langchain_mistralai import ChatMistralAI
            api_key = os.getenv("MISTRAL_API_KEY")

            if not api_key:
                raise ValueError("MISTRAL_API_KEY is missing or empty in configuration.")
            return ChatMistralAI(model_name=os.getenv("MISTRAL_MODEL"), api_key=api_key, temperature=0.7, verbose=True)
        
        elif provider == "openai":
            from langchain_openai import ChatOpenAI
            api_key = os.getenv("OPENAI_API_KEY")

            if not api_key:
                raise ValueError("OPENAI_API_KEY is missing or empty in configuration.")
            return ChatOpenAI(model_name=os.getenv("OPENAI_MODEL"), api_key=api_key, temperature=0.7, verbose=True)

        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")

            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY is missing or empty in configuration.")
            return ChatAnthropic(model_name=os.getenv("ANTHROPIC_MODEL"), api_key=api_key, temperature=0.7, verbose=True)

        elif provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = os.getenv("GOOGLE_API_KEY")

            if not api_key:
                raise ValueError("GOOGLE_API_KEY is missing or empty in configuration.")
            return ChatGoogleGenerativeAI(model_name=os.getenv("GEMINI_MODEL"), api_key=api_key, temperature=0.7, verbose=True)
        else:
            raise Exception(f"Unknown LLM provider: {provider}")

    except ValueError as e:
        print(f"Configuration Error {e}")
        return None
    except Exception as e:
        print(f"Initilaization Error: Unable to find provider {provider}: {e}")
        return None
