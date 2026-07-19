from core.config import settings

# Attempt to load the Mistral client depending on the version installed
try:
    from mistralai.client import Mistral
except ImportError:
    try:
        from mistralai import Mistral
    except ImportError:
        from mistralai.client import MistralClient as Mistral

from tenacity import retry, stop_after_attempt, wait_exponential

def get_mistral_client():
    return Mistral(api_key=settings.mistral_api_key)

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def generate_embeddings(client, texts: list[str]) -> list[list[float]]:
    try:
        # v1.x syntax
        response = client.embeddings.create(
            model="mistral-embed",
            inputs=texts
        )
    except AttributeError:
        # v0.x syntax fallback
        response = client.embeddings(
            model="mistral-embed",
            input=texts
        )
    return [data.embedding for data in response.data]
