import json

import boto3

import phoenix as px
from phoenix.evals import (
TOOL_CALLING_PROMPT_RAILS_MAP,
TOOL_CALLING_PROMPT_TEMPLATE,
BedrockModel,
llm_classify,
)

import os
from getpass import getpass

# Change the following line if you're self-hosting
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = "https://app.phoenix.arize.com/s/ryankarlos"

# Remove the following lines if you're self-hosting
os.environ["PHOENIX_API_KEY"] = getpass("Enter your Phoenix API key: ")
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"api_key={os.environ['PHOENIX_API_KEY']}"
os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={os.environ['PHOENIX_API_KEY']}"


a_template = """You are given a question and an answer. You must determine whether the
given answer correctly answers the question. Here is the data:
    [BEGIN DATA]
    ************
    [Question]: {Question}
    ************
    [Answer]: {Answer}
    [END DATA]
    d, either "correct" or "incorrect",
and should not contain any text or characters aside from that word.
"correct" means that the question is correctly and fully answered by the answer.
"incorrect" means that the question is not correctly or only partially answered by the
answer."""



spans_df = px.Client().get_spans_dataframe(project_name="aws_litellm_demo")
spans_df = spans_df.iloc[0:16]
print(spans_df)


eval_df = spans_df[["context.span_id", "attributes.input.value", "attributes.output.value"]].copy()
eval_df.set_index("context.span_id", inplace=True)


evals_copy = eval_df.copy()
evals_copy["attributes.input.value"] = (
    evals_copy["attributes.input.value"]
    .str.replace(r"^Human: ", "", regex=True)
    .str.replace(r"Assistant:$", "", regex=True)
)

evals_copy = evals_copy.rename(
    columns={"attributes.input.value": "Question", "attributes.output.value": "Answer"}
)
print(evals_copy.head())


eval_model = BedrockModel(session=session, model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")

response_classifications = llm_classify(
    data=trace_df,
    template=TOOL_CALLING_PROMPT_TEMPLATE,
    model=eval_model,
    rails=rails,
    provide_explanation=True,
)
response_classifications["score"] = response_classifications.apply(
    lambda x: 1 if x["label"] == "correct" else 0, axis=1
)

px.Client().log_evaluations(
SpanEvaluations(eval_name="Tool Calling Eval", dataframe=response_classifications),
)