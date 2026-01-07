"""
SQuAD Evaluation with Arize Phoenix Cloud.

Loads SQuAD dataset, creates Phoenix dataset, runs experiments
comparing LLM responses against ground truth answers.
"""

import os
import openai
from datasets import load_dataset
from phoenix.experiments import run_experiment, evaluate_experiment
import phoenix as px


# Configuration
LITELLM_API_KEY = os.environ.get('LITELLM_API_KEY') or os.environ.get('API_KEY')
LITELLM_ENDPOINT = os.environ.get('LITELLM_ENDPOINT') or os.environ.get('BASE_URL', 'http://localhost:4000')

# export these env vars (from phoenix console)
# os.environ["PHOENIX_API_KEY"] = ""
# os.environ['PHOENIX_BASE_URL'] =  ''

MODEL_NAME = os.environ.get('MODEL_NAME', 'nova-pro')
NUM_SAMPLES = int(os.environ.get('NUM_SAMPLES', '50'))


def load_squad_samples(num_samples: int = 50) -> list:
    """Load samples from SQuAD dataset."""
    dataset = load_dataset("squad", split="validation")
    
    samples = []
    seen_questions = set()
    
    for item in dataset:
        question = item['question']
        if question in seen_questions:
            continue
        seen_questions.add(question)
        
        samples.append({
            "question": question,
            "context": item['context'],
            "ground_truth": item['answers']['text'][0] if item['answers']['text'] else "",
            "id": item['id']
        })
        
        if len(samples) >= num_samples:
            break
    
    return samples


def create_phoenix_dataset(client, samples: list, dataset_name: str = "squad-eval"):
    """Create Phoenix dataset from SQuAD samples."""
    dataset = client.upload_dataset(
        dataset_name=dataset_name,
        inputs=[{"question": s["question"], "context": s["context"]} for s in samples],
        outputs=[{"answer": s["ground_truth"]} for s in samples],
        metadata=[{"id": s["id"]} for s in samples]
    )
    return dataset


def get_llm_response(question: str, context: str) -> str:
    """Get LLM response for a question given context."""
    client = openai.OpenAI(api_key=LITELLM_API_KEY, base_url=LITELLM_ENDPOINT)
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system", 
                "content": "Answer the question based on the context. Be concise and accurate."
            },
            {
                "role": "user", 
                "content": f"Context: {context}\n\nQuestion: {question}"
            }
        ],
        max_tokens=150,
        temperature=0
    )
    
    return response.choices[0].message.content


def task_fn(input_data: dict) -> str:
    """Task function for Phoenix experiment."""
    question = input_data["question"]
    context = input_data["context"]
    return get_llm_response(question, context)


def exact_match_evaluator(output: str, expected: dict) -> float:
    """Check if output contains the expected answer."""
    ground_truth = expected.get("answer", "").lower()
    return 1.0 if ground_truth in output.lower() else 0.0


def f1_score_evaluator(output: str, expected: dict) -> float:
    """Calculate F1 score between output and expected answer."""
    ground_truth = expected.get("answer", "")
    
    pred_tokens = set(output.lower().split())
    truth_tokens = set(ground_truth.lower().split())
    
    if not pred_tokens or not truth_tokens:
        return 0.0
    
    common = pred_tokens & truth_tokens
    if not common:
        return 0.0
    
    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(truth_tokens)
    
    return 2 * (precision * recall) / (precision + recall)


def run_squad_evaluation():
    """Run full SQuAD evaluation with Phoenix."""
    
    client = px.Client()
    
    print(f"Loading {NUM_SAMPLES} SQuAD samples...")
    samples = load_squad_samples(NUM_SAMPLES)
    print(f"Loaded {len(samples)} samples")
    
    print("Creating Phoenix dataset...")
    dataset = create_phoenix_dataset(client, samples)
    print(f"Created dataset: {dataset.name}")
    
    print(f"Running experiment with model: {MODEL_NAME}...")
    experiment = run_experiment(
        dataset=dataset,
        task=task_fn,
        experiment_name=f"squad-eval-{MODEL_NAME}",
        experiment_description=f"SQuAD evaluation using {MODEL_NAME} via LiteLLM"
    )
    
    print("Evaluating results...")
    evaluate_experiment(
        experiment=experiment,
        evaluators=[
            ("exact_match", exact_match_evaluator),
            ("f1_score", f1_score_evaluator)
        ]
    )
    
    print(f"\nExperiment complete: {experiment.name}")
    print(f"View results at: {PHOENIX_ENDPOINT}")
    
    return experiment


if __name__ == "__main__":
    run_squad_evaluation()
