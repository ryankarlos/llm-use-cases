"""
Lambda fulfillment function for Amazon Lex Q&A Assistant.
Handles greeting, Q&A (via LiteLLM), and closing intents.
"""

import json
import os
import urllib3
import boto3
from botocore.exceptions import ClientError

# Environment variables
LITELLM_ENDPOINT = os.environ.get('LITELLM_ENDPOINT', 'http://localhost:4000')
LITELLM_API_KEY_SECRET = os.environ.get('LITELLM_API_KEY_SECRET', '')
MODEL_NAME = os.environ.get('MODEL_NAME', 'nova-pro')

# Cache for API key
_api_key_cache = None


def get_litellm_api_key():
    """Fetch LiteLLM API key from Secrets Manager (cached)."""
    global _api_key_cache
    if _api_key_cache:
        return _api_key_cache
    
    if not LITELLM_API_KEY_SECRET:
        return ''
    
    try:
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId=LITELLM_API_KEY_SECRET)
        _api_key_cache = response['SecretString']
        return _api_key_cache
    except ClientError as e:
        print(f"Error fetching API key from Secrets Manager: {e}")
        return ''


def lambda_handler(event, context):
    """
    Handle Lex fulfillment requests.
    
    Args:
        event: Lex V2 event containing user input
        context: Lambda context
        
    Returns:
        Lex V2 response
    """
    try:
        user_message = event.get('inputTranscript', '')
        intent_name = event.get('sessionState', {}).get('intent', {}).get('name', 'FallbackIntent')
        
        print(f"Intent: {intent_name}, Message: {user_message}")
        
        # Handle different intents
        if intent_name == 'GreetingIntent':
            return handle_greeting(intent_name)
        elif intent_name == 'ClosingIntent':
            return handle_closing(intent_name)
        elif intent_name == 'QAIntent':
            return handle_qa(intent_name, user_message)
        else:
            # Fallback - treat as QA if there's a message
            if user_message:
                return handle_qa(intent_name, user_message)
            return build_response(
                intent_name=intent_name,
                message="I'm not sure how to help with that. Could you rephrase your question?"
            )
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return build_response(
            intent_name=event.get('sessionState', {}).get('intent', {}).get('name', 'FallbackIntent'),
            message="I'm sorry, I encountered an error. Please try again."
        )


def handle_greeting(intent_name: str) -> dict:
    """Handle greeting intent."""
    return build_response(
        intent_name=intent_name,
        message="Hello! I'm your Q&A assistant powered by AWS Bedrock. How can I help you today? Feel free to ask me any question!"
    )


def handle_closing(intent_name: str) -> dict:
    """Handle closing intent."""
    return build_response(
        intent_name=intent_name,
        message="Goodbye! It was great chatting with you. Have a wonderful day!"
    )


def handle_qa(intent_name: str, user_message: str) -> dict:
    """Handle Q&A intent by forwarding to LiteLLM."""
    if not user_message:
        return build_response(
            intent_name=intent_name,
            message="I didn't catch that. Could you please repeat your question?"
        )
    
    assistant_message = call_litellm(user_message)
    return build_response(intent_name=intent_name, message=assistant_message)


def call_litellm(user_message: str) -> str:
    """
    Call LiteLLM proxy with user message using OpenAI-compatible API.
    
    Args:
        user_message: The user's question
        
    Returns:
        Assistant's response from LLM
    """
    http = urllib3.PoolManager(cert_reqs='CERT_NONE')
    
    api_key = get_litellm_api_key()
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    
    payload = {
        'model': MODEL_NAME,
        'messages': [
            {
                'role': 'system',
                'content': 'You are a helpful Q&A assistant. Provide clear, concise answers.'
            },
            {
                'role': 'user',
                'content': user_message
            }
        ],
        'max_tokens': 500
    }
    
    endpoint = f"{LITELLM_ENDPOINT}/v1/chat/completions"
    print(f"Calling LiteLLM at: {endpoint}")
    
    response = http.request(
        'POST',
        endpoint,
        headers=headers,
        body=json.dumps(payload),
        timeout=30.0
    )
    
    if response.status != 200:
        error_msg = response.data.decode('utf-8')
        print(f"LiteLLM API error: {response.status} - {error_msg}")
        raise Exception(f"LiteLLM API error: {response.status}")
    
    result = json.loads(response.data.decode('utf-8'))
    assistant_message = result['choices'][0]['message']['content']
    
    return assistant_message


def build_response(intent_name: str, message: str) -> dict:
    """Build Lex V2 response format."""
    return {
        'sessionState': {
            'dialogAction': {
                'type': 'Close'
            },
            'intent': {
                'name': intent_name,
                'state': 'Fulfilled'
            }
        },
        'messages': [
            {
                'contentType': 'PlainText',
                'content': message
            }
        ]
    }
