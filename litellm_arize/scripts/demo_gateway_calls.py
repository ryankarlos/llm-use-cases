import os 
import litellm
from openai import OpenAI
from getpass import getpass


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

os.environ["LITELLM_PROXY_API_BASE"] = LITELLM_BASE_URL 
os.environ["LITELLM_PROXY_API_KEY"] = LITELLM_API_KEY 

client = OpenAI(
    api_key=LITELLM_API_KEY,
    base_url=LITELLM_BASE_URL
)

prompt = "what is a support vector machine ? Summarise in two short sentences."
model = "nova-pro"

print(f"------Querying model {model}----------")
print("using open ai chat completions sdk")
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=50,
)
print(response.choices[0].message.content)
print("")

print(f"------Querying model {model}----------")
print("using litellm completions sdk")
stream = litellm.completion(
    model=f"litellm_proxy/{model}",
    messages=[{"content": prompt, "role": "user"}],
    max_tokens=50,
    stream=True
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)

print()  # newline at end
