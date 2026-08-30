from pathlib import Path
from dotenv import load_dotenv, set_key, dotenv_values

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
ENV_FILE = CONFIG_DIR / ".env"

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

def load_env(env_path: Path = ENV_FILE) -> dict[str, str|None]:

    #Create .env file parent dicrectory if the path not exists
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Create .env and add env variables in it.
    if not env_path.exists():
        env_path.touch()
        for key, value in DEFAULT_ENV_VARS.items():
            set_key(dotenv_path=env_path,
                key_to_set=key,
                value_to_set=value)

    #Load env varibles to os.environ
    load_dotenv(dotenv_path=env_path, override=True)

    # Return a clean dictionary values
    return dict(dotenv_values(dotenv_path=ENV_FILE))

load_env()