import os
from getpass import getpass

import phoenix as px
from phoenix.evals import (
    LiteLLMModel,
    llm_classify,
)


def get_env_or_prompt(env_var: str, prompt_msg: str, is_secret: bool = False) -> str:
    """Get value from env var or prompt user if not set."""
    value = os.getenv(env_var)
    if not value:
        if is_secret:
            value = getpass(prompt_msg)
        else:
            value = input(prompt_msg)
    return value


# # Phoenix configuration
# PHOENIX_COLLECTOR_ENDPOINT = get_env_or_prompt(
#     "PHOENIX_COLLECTOR_ENDPOINT", "Enter Phoenix Collector Endpoint: "
# )
PHOENIX_API_KEY = get_env_or_prompt(
    "PHOENIX_API_KEY", "Enter Phoenix API Key: ", is_secret=True
)
PHOENIX_PROJECT_NAME = "aws_litellm_demo"

# LiteLLM configuration
LITELLM_BASE_URL = get_env_or_prompt("LITELLM_BASE_URL", "Enter LiteLLM Base URL: ")
LITELLM_API_KEY = get_env_or_prompt("LITELLM_API_KEY", "Enter LiteLLM API Key: ", is_secret=True)

# Set environment variables
# os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = PHOENIX_COLLECTOR_ENDPOINT
os.environ["PHOENIX_API_KEY"] = PHOENIX_API_KEY
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"api_key={PHOENIX_API_KEY}"
os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={PHOENIX_API_KEY}"
os.environ["LITELLM_PROXY_API_BASE"] = LITELLM_BASE_URL
os.environ["LITELLM_PROXY_API_KEY"] = LITELLM_API_KEY

MODEL = "nova-pro"

prompt_template = """You are given a question and an answer. You must determine whether the
given answer correctly answers the question. Here is the data:
    [BEGIN DATA]
    ************
    [Question]: {Question}
    ************
    [Answer]: {Answer}
    [END DATA]
    
    Return a label for your response as "correct" or "incorrect" , where correct is if the answer is factually correct and  incorrect is if the answer
    is factually incorrect"""


spans_df = px.Client().get_spans_dataframe(project_name=PHOENIX_PROJECT_NAME, root_spans_only=True)
spans_df = spans_df[["context.span_id", "attributes.input.value", "attributes.output.value"]]
spans_df = spans_df.set_index("context.span_id")
spans_df = spans_df.rename(
    columns={"attributes.input.value": "Question", "attributes.output.value": "Answer"}
)

print(spans_df.head())

eval_model = LiteLLMModel(model=f"litellm_proxy/{MODEL}")

response_classifications = llm_classify(
    data=spans_df,
    template=prompt_template,
    model=eval_model,
    rails=["correct", "incorrect"],
    provide_explanation=True
)

response_classifications = response_classifications[['prompt', '"Question", "Answer", label']]
print(response_classifications)
