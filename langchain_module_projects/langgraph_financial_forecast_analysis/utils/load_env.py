from pathlib import Path
from dotenv import dotenv_values, load_dotenv, set_key


ENV_FOLDER = Path(__file__).resolve().parent.parent / "configs"
ENV_FILE = ENV_FOLDER/".env"

DEFAULT_ENV_VARS = {
    "DEFAULT_LLM_PROVIDER": "mistral",
    "MISTRAL_MODEL": "codestral-latest",
    "MISTRAL_API_KEY": "",
    "OPENAI_MODEL": "gpt-4o-mini",
    "OPENAI_API_KEY": "",
    "ANTHROPIC_MODEL": "claude-3-5-sonnet-latest",
    "ANTHROPIC_API_KEY": "",
    "GEMINI_MODEL": "gemini-1.5-flash",
    "GOOGLE_API_KEY": "",
}

def load_env(path_env: Path = ENV_FILE) -> dict[str, str|None]:

    path_env.parent.mkdir(parents=True, exist_ok=True)

    if not path_env.exists():
        path_env.touch()

        for key, value in DEFAULT_ENV_VARS.items():
            set_key(
                dotenv_path=path_env,
                key_to_set=key,
                value_to_set=value
            )

    load_dotenv(dotenv_path=path_env, override=True)

    return dict(dotenv_values(dotenv_path=path_env))

load_env()