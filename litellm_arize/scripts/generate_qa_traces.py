#!/usr/bin/env python3
"""
Script to generate responses via LiteLLM proxy gateway.
Sends trivia questions to the LiteLLM endpoint and prints responses.
"""

import os
from openai import OpenAI
from getpass import getpass
import polars as pl
from datasets import load_dataset


def get_env_or_prompt(env_var: str, prompt_msg: str, is_secret: bool = False) -> str:
    """Get value from env var or prompt user if not set."""
    value = os.getenv(env_var)
    if not value:
        if is_secret:
            value = getpass(prompt_msg)
        else:
            value = input(prompt_msg)
    return value


LITELLM_BASE_URL = get_env_or_prompt("LITELLM_BASE_URL", "Enter LiteLLM Base URL: ")
LITELLM_API_KEY = get_env_or_prompt("LITELLM_API_KEY", "Enter LiteLLM API Key: ", is_secret=True)
MODEL_NAME = "nova-micro"

client = OpenAI(
    api_key=LITELLM_API_KEY,
    base_url=LITELLM_BASE_URL
)

# Fetch SQUAD dataset and convert to polars dataframe
dataset = load_dataset("rajpurkar/squad", split="train")
df = pl.from_arrow(dataset.data.table)

# Take random 30 questions from the dataframe
trivia_questions = df.select("question").sample(n=30, seed=42).to_series().to_list()


def generate_response(question: str, model: str = MODEL_NAME) -> str:
    """Send a question to LiteLLM proxy and return the response."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": question}],
        max_tokens=300
    )
    return response.choices[0].message.content


def main():
    print(f"Model: {MODEL_NAME}")
    print("=" * 60)
    
    for i, question in enumerate(trivia_questions, start=1):
        print(f"\nQ{i}: {question}")
        try:
            answer = generate_response(question)
            print(f"A{i}: {answer}")
        except Exception as e:
            print(f"Error: {e}")
        print("-" * 60)


if __name__ == "__main__":
    main()
