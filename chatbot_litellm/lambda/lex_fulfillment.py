"""
Lambda fulfillment function for Amazon Lex Q&A Assistant.
Forwards user queries to LiteLLM proxy and returns responses to Lex.
"""

import json
import os
import urllib3

# Environment variables
LITELLM_ENDPOINT = os.environ.get('LITELLM_ENDPOINT', 'http://localhost:4000')
LITELLM_API_KEY = os.environ.get('LITELLM_API_KEY', '')
MODEL_NAME = os.environ.get('MODEL_NAME', 'claude-3-sonnet')


def lambda_handler(event, context):
    """
    Handle Lex fulfillment requests by forwarding to LiteLLM.
    
    Args:
        event: Lex V2 event containing user input
        context: Lambda context
        
    Returns:
        Lex V2 response with LLM-generated content
    """
    try:
        # Extract user message from Lex event
        user_message = event.get('inputTranscript', '')
        intent_name = event.get('sessionState', {}).get('intent', {}).get('name', 'FallbackIntent')
        session_id = event.get('sessionId', '')
        
        if not user_message:
            return build_response(
                intent_name=intent_name,
                message="I didn't catch that. Could you please repeat your question?"
            )
        
        # Call LiteLLM proxy
        assistant_message = call_litellm(user_message)
        
        return build_response(
            intent_name=intent_name,
            message=assistant_message
        )
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return build_response(
            intent_name=event.get('sessionState', {}).get('intent', {}).get('name', 'FallbackIntent'),
            message="I'm sorry, I encountered an error processing your request. Please try again."
        )


def call_litellm(user_message: str) -> str:
    """
    Call LiteLLM proxy with user message.
    
    Args:
        user_message: The user's question or message
        
    Returns:
        Assistant's response from LLM
    """
    http = urllib3.PoolManager()
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    if LITELLM_API_KEY:
        headers['Authorization'] = f'Bearer {LITELLM_API_KEY}'
    
    payload = {
        'model': MODEL_NAME,
        'messages': [
            {
                'role': 'system',
                'content': 'You are a helpful Q&A assistant. Provide clear, concise answers to user questions.'
            },
            {
                'role': 'user',
                'content': user_message
            }
        ],
        'max_tokens': 500
    }
    
    response = http.request(
        'POST',
        f"{LITELLM_ENDPOINT}/chat/completions",
        headers=headers,
        body=json.dumps(payload),
        timeout=30.0
    )
    
    if response.status != 200:
        raise Exception(f"LiteLLM API error: {response.status} - {response.data.decode('utf-8')}")
    
    result = json.loads(response.data.decode('utf-8'))
    assistant_message = result['choices'][0]['message']['content']
    
    return assistant_message


def build_response(intent_name: str, message: str) -> dict:
    """
    Build Lex V2 response format.
    
    Args:
        intent_name: Name of the intent being fulfilled
        message: Response message to send to user
        
    Returns:
        Lex V2 formatted response
    """
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
