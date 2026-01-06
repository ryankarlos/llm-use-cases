"""
LiteLLM Load Test with SQuAD-style prompts for Arize Phoenix evaluation.

Uses small, diverse prompts to minimize cost while enabling
quality evaluation metrics.
"""

import os
import random
from locust import HttpUser, task, between, events


"""
SQuAD-style prompts for LiteLLM load testing and Arize Phoenix evaluation.

These prompts are designed to:
1. Be short to minimize token costs during load testing
2. Have clear expected answers for evaluation metrics
3. Cover diverse categories for comprehensive testing
"""

# SQuAD-style question-context-answer triplets for evaluation
SQUAD_PROMPTS = [
    # Science
    {
        "category": "science",
        "question": "What is photosynthesis?",
        "context": "Photosynthesis is the process by which plants convert sunlight, water, and carbon dioxide into glucose and oxygen.",
        "expected_answer": "Photosynthesis is the process plants use to convert sunlight into energy/food."
    },
    {
        "category": "science",
        "question": "What causes rain?",
        "context": "Rain occurs when water vapor in the atmosphere condenses into droplets that become heavy enough to fall.",
        "expected_answer": "Rain is caused by water vapor condensing in clouds and falling as droplets."
    },
    {
        "category": "science",
        "question": "What is gravity?",
        "context": "Gravity is a fundamental force that attracts objects with mass toward each other.",
        "expected_answer": "Gravity is the force that attracts objects with mass toward each other."
    },
    {
        "category": "science",
        "question": "What is the speed of light?",
        "context": "Light travels at approximately 299,792 kilometers per second in a vacuum.",
        "expected_answer": "The speed of light is approximately 300,000 km/s or 186,000 miles/s."
    },
    {
        "category": "science",
        "question": "What is DNA?",
        "context": "DNA (deoxyribonucleic acid) is a molecule that carries genetic instructions for living organisms.",
        "expected_answer": "DNA is a molecule that carries genetic information in living organisms."
    },
    
    # Technology
    {
        "category": "technology",
        "question": "What is an API?",
        "context": "An API (Application Programming Interface) allows different software applications to communicate with each other.",
        "expected_answer": "An API is an interface that allows software applications to communicate."
    },
    {
        "category": "technology",
        "question": "What is cloud computing?",
        "context": "Cloud computing delivers computing services over the internet, including servers, storage, and databases.",
        "expected_answer": "Cloud computing provides computing resources over the internet on-demand."
    },
    {
        "category": "technology",
        "question": "What is machine learning?",
        "context": "Machine learning is a subset of AI where systems learn from data to improve performance without explicit programming.",
        "expected_answer": "Machine learning enables systems to learn and improve from data automatically."
    },
    
    # History
    {
        "category": "history",
        "question": "When did World War 2 end?",
        "context": "World War 2 ended in 1945 with Germany surrendering in May and Japan in September.",
        "expected_answer": "World War 2 ended in 1945."
    },
    {
        "category": "history",
        "question": "Who invented the telephone?",
        "context": "Alexander Graham Bell is credited with inventing the first practical telephone in 1876.",
        "expected_answer": "Alexander Graham Bell invented the telephone in 1876."
    },
    {
        "category": "history",
        "question": "What was the Renaissance?",
        "context": "The Renaissance was a cultural movement in Europe from the 14th to 17th century emphasizing art, science, and humanism.",
        "expected_answer": "The Renaissance was a European cultural movement emphasizing art and learning."
    },
    {
        "category": "history",
        "question": "When was the Declaration of Independence signed?",
        "context": "The United States Declaration of Independence was signed on August 2, 1776.",
        "expected_answer": "The Declaration of Independence was signed in 1776."
    },
    
    # Geography
    {
        "category": "geography",
        "question": "What is the largest ocean?",
        "context": "The Pacific Ocean is the largest and deepest ocean, covering about 63 million square miles.",
        "expected_answer": "The Pacific Ocean is the largest ocean."
    },
    {
        "category": "geography",
        "question": "What is the capital of France?",
        "context": "Paris is the capital and largest city of France, located on the Seine River.",
        "expected_answer": "Paris is the capital of France."
    },
    {
        "category": "geography",
        "question": "What is the longest river?",
        "context": "The Nile River in Africa is traditionally considered the longest river at about 6,650 km.",
        "expected_answer": "The Nile River is the longest river at about 6,650 km."
    },
    {
        "category": "geography",
        "question": "How many continents are there?",
        "context": "There are seven continents: Africa, Antarctica, Asia, Australia, Europe, North America, and South America.",
        "expected_answer": "There are seven continents."
    },
    
    # Math & Logic
    {
        "category": "math",
        "question": "What is a prime number?",
        "context": "A prime number is a natural number greater than 1 that is only divisible by 1 and itself.",
        "expected_answer": "A prime number is only divisible by 1 and itself."
    },
    {
        "category": "math",
        "question": "What is the Pythagorean theorem?",
        "context": "The Pythagorean theorem states that in a right triangle, a² + b² = c², where c is the hypotenuse.",
        "expected_answer": "The Pythagorean theorem states a² + b² = c² for right triangles."
    },
    {
        "category": "math",
        "question": "What is pi?",
        "context": "Pi (π) is a mathematical constant approximately equal to 3.14159, representing the ratio of a circle's circumference to its diameter.",
        "expected_answer": "Pi is approximately 3.14159, the ratio of circumference to diameter."
    },
    
    # Literature
    {
        "category": "literature",
        "question": "Who wrote Romeo and Juliet?",
        "context": "Romeo and Juliet is a tragedy written by William Shakespeare around 1594-1596.",
        "expected_answer": "William Shakespeare wrote Romeo and Juliet."
    },
    {
        "category": "literature",
        "question": "What is a metaphor?",
        "context": "A metaphor is a figure of speech that directly compares two unlike things without using 'like' or 'as'.",
        "expected_answer": "A metaphor is a direct comparison between two unlike things."
    },
    {
        "category": "literature",
        "question": "Who wrote 1984?",
        "context": "1984 is a dystopian novel written by George Orwell, published in 1949.",
        "expected_answer": "George Orwell wrote 1984."
    },
    
    # AWS & Cloud
    {
        "category": "aws",
        "question": "What is Amazon S3?",
        "context": "Amazon S3 (Simple Storage Service) is an object storage service offering scalability, availability, and security.",
        "expected_answer": "Amazon S3 is an object storage service for storing and retrieving data."
    },
    {
        "category": "aws",
        "question": "What is AWS Lambda?",
        "context": "AWS Lambda is a serverless compute service that runs code in response to events without managing servers.",
        "expected_answer": "AWS Lambda is a serverless compute service that runs code on-demand."
    },
    {
        "category": "aws",
        "question": "What is Amazon Bedrock?",
        "context": "Amazon Bedrock is a fully managed service for building generative AI applications with foundation models.",
        "expected_answer": "Amazon Bedrock is a managed service for generative AI with foundation models."
    },
    {
        "category": "aws",
        "question": "What is Amazon ECS?",
        "context": "Amazon ECS (Elastic Container Service) is a container orchestration service for running Docker containers.",
        "expected_answer": "Amazon ECS is a container orchestration service for Docker containers."
    },
    {
        "category": "aws",
        "question": "What is Amazon RDS?",
        "context": "Amazon RDS (Relational Database Service) is a managed database service supporting multiple database engines.",
        "expected_answer": "Amazon RDS is a managed relational database service."
    },
    
    # General Knowledge
    {
        "category": "general",
        "question": "What is the chemical symbol for water?",
        "context": "Water is a chemical compound with the formula H2O, consisting of two hydrogen atoms and one oxygen atom.",
        "expected_answer": "The chemical symbol for water is H2O."
    },
    {
        "category": "general",
        "question": "What is the largest planet in our solar system?",
        "context": "Jupiter is the largest planet in our solar system, with a mass more than twice that of all other planets combined.",
        "expected_answer": "Jupiter is the largest planet in our solar system."
    },
    {
        "category": "general",
        "question": "What is the boiling point of water?",
        "context": "Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at standard atmospheric pressure.",
        "expected_answer": "Water boils at 100°C or 212°F at standard pressure."
    },
]

# Categories for filtering
CATEGORIES = list(set(p["category"] for p in SQUAD_PROMPTS))

def get_prompts_by_category(category: str) -> list:
    """Get all prompts for a specific category."""
    return [p for p in SQUAD_PROMPTS if p["category"] == category]

def get_random_prompt() -> dict:
    """Get a random prompt from the dataset."""
    import random
    return random.choice(SQUAD_PROMPTS)

def format_for_evaluation(prompt: dict) -> dict:
    """
    Format a prompt for Arize Phoenix evaluation.
    
    Returns a dict with:
    - input: The question to send to the model
    - context: Reference context for RAG evaluation
    - expected_output: Expected answer for comparison
    - metadata: Category and other metadata
    """
    return {
        "input": prompt["question"],
        "context": prompt["context"],
        "expected_output": prompt["expected_answer"],
        "metadata": {
            "category": prompt["category"],
            "test_type": "squad_evaluation"
        }
    }

def get_all_for_evaluation() -> list:
    """Get all prompts formatted for evaluation."""
    return [format_for_evaluation(p) for p in SQUAD_PROMPTS]

# Track LiteLLM overhead duration
overhead_durations = []

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    if response and hasattr(response, 'headers'):
        overhead_duration = response.headers.get('x-litellm-overhead-duration-ms')
        if overhead_duration:
            try:
                overhead_durations.append(float(overhead_duration))
            except (ValueError, TypeError):
                pass


class SquadEvaluationTest(HttpUser):
    """Load test using SQuAD prompts for evaluation."""
    
    wait_time = between(0.5, 2)

    def on_start(self):
        self.api_key = os.getenv('LITELLM_API_KEY') or os.getenv('API_KEY')
        if not self.api_key:
            raise ValueError("LITELLM_API_KEY or API_KEY environment variable required")
        self.client.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        self.request_count = 0

    @task(10)
    def chat_completion_nova(self):
        """Nova Pro model requests."""
        self._send_completion("nova-pro")

    @task(5)
    def chat_completion_titan(self):
        """Titan Text model requests."""
        self._send_completion("titan-text")

    def _send_completion(self, model: str):
        """Send chat completion with random SQuAD prompt."""
        prompt_data = get_random_prompt()
        self.request_count += 1
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Give concise answers in 1-2 sentences maximum."},
                {"role": "user", "content": f"Answer briefly: {prompt_data['question']}"}
            ],
            "max_tokens": 100,
            "temperature": 0.7,
            "metadata": {
                "category": prompt_data["category"],
                "expected_context": prompt_data["context"],
                "expected_answer": prompt_data["expected_answer"],
                "test_type": "squad_evaluation",
                "request_id": f"eval-{self.request_count}"
            }
        }
        
        with self.client.post(
            "/v1/chat/completions",
            json=payload,
            name=f"chat/completions [{model}]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}: {response.text[:200]}")

    @task(1)
    def health_check(self):
        """Health check."""
        with self.client.get("/health/liveliness", name="health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
