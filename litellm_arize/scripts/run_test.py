import time
import openai

client = openai.OpenAI(
    api_key="sk-L5jvenh9qObvYcmc9L74Cw",
    base_url="http://litellm-demo-alb-1496597271.us-east-1.elb.amazonaws.com/"
)

stream = client.chat.completions.create(
    model="nova-micro",
    messages=[
        {
            "role": "user",
            "content": "this is a test request, write a short poem"
        }
    ],
    stream=True
)

# Print each chunk as it arrives
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, flush=True)
        print("---")  # Separator between chunks



curl http://http://litellm-demo-alb-1496597271.us-east-1.elb.amazonaws.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-L5jvenh9qObvYcmc9L74Cw" \
  -d '{
    "model": "nova-pro",
    "messages": [{"role": "user", "content": "What is Amazon Bedrock?"}]
  }'