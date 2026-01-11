#!/usr/bin/env python3
"""
Script to generate responses via LiteLLM proxy gateway.
Sends trivia questions to the LiteLLM endpoint and prints responses.
"""

import os
from openai import OpenAI
from getpass import getpass


# Configuration - can be overridden via environment variables
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", getpass("Enter your Litellm base url: "))
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", getpass("Enter your Litellm API key: "))
MODEL_NAME = os.getenv("MODEL_NAME", "nova-micro")

client = OpenAI(
    api_key=LITELLM_API_KEY,
    base_url=LITELLM_BASE_URL
)

trivia_questions = [
    "What is the only U.S. state that starts with two vowels?",
    "What is the 3rd month of the year in alphabetical order?",
    "What is the capital of Mongolia?",
    "How many minutes are there in a leap year?",
    "If a train leaves New York at 3 PM traveling west at 60 mph, and another leaves Chicago at 4 PM traveling east at 80 mph, at what time will they meet?",
    "Which element has the chemical symbol 'Fe'?",
    "What five-letter word becomes shorter when you add two letters to it?",
    "What country has won the most FIFA World Cups?",
    "If today is Wednesday, what day of the week will it be 100 days from now?",
    "A farmer has 17 sheep and all but 9 run away. How many does he have left?",
]


def generate_response(question: str, model: str = MODEL_NAME) -> str:
    """Send a question to LiteLLM proxy and return the response."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": question}],
        max_tokens=300
    )
    return response.choices[0].message.content


def main():
    print(f"LiteLLM Proxy: {LITELLM_BASE_URL}")
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
