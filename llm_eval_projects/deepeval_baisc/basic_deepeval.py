# Its deepeval assert kw used to compare the Actual response with expected response from golden dataset
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase
from deepeval.models import GeminiModel
from dotenv import load_dotenv, set_key, dotenv_values
from pathlib import Path

CONFIG_FOLDER = Path(__file__).resolve().parent / "configs"
CONFIG_ENV = CONFIG_FOLDER / ".env"

def load_env(path: Path=CONFIG_ENV) -> dict[str, str|None]:

    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.touch()

        set_key(
            dotenv_path=path,
            key_to_set="GOOGLE_API_KEY",
            value_to_set=""
        )

    load_dotenv(dotenv_path=path, override=True)

    return dict(dotenv_values(dotenv_path=path))

# Load env var to os.environ
load_env()

# Setup AI Model for Judging
gemini_model = GeminiModel(
    model="gemini-3.6-flash"
)

#Metrics to Evaluate
metrics = AnswerRelevancyMetric(threshold=0.8, model=gemini_model)

#User Input to Evaluate Against
test_case = LLMTestCase(
        input="Who is the CEO of Alphabet?",
        actual_output="Sundar Pichai",
        expected_output="Sundar Pichai"
    )

#Test case for eval.
def test_llm_output():
    assert_test(test_case=test_case, metrics=[metrics])