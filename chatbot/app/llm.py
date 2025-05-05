import boto3


class Llm:
    def __init__(
        self,
        bedrock_region,
        # profile_name="entain"
    ):
        # session = boto3.Session(profile_name=profile_name)
        # Create Bedrock client
        bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=bedrock_region,
        )
        self.bedrock_client = bedrock_client

    def stream_response(self, messages):
        """
        Make a call to the foundation model through Bedrock using converse_stream
        """
        # Prepare a Bedrock API call to invoke a foundation model
        model_id = "eu.amazon.nova-pro-v1:0"

        # Only include system message if it's the first message in the conversation
        include_system = len(messages) == 1  # Assuming first user message only

        # ConverseStream required parameters
        inference_config = {
            "maxTokens": 500,
            "temperature": 0.5,
            "topP": 0.8,
        }

        system_prompts = [
            {
                "text": """
        You are an internal AI assistant for employees for an online sports betting and online casino company. You provide helpful, accurate, and concise answers across departments like HR, IT, Legal, Finance, and Procurement.
        You have access to both internal company knowledge and public general knowledge. For each answer, clarify whether it is based on internal data or general information.
        When internal data is available, always prioritize it. If you're unsure or lack access to specific internal data, say so and suggest the user contact the relevant department.
        You are privacy-conscious, respectful, and professional. Do not speculate or share confidential data unless explicitly requested and permitted.
        When in doubt, ask for clarification rather than assuming user intent.

        If the user has uploaded a document, carefully analyze its contents and refer specifically to information from the document in your responses."""
            }
        ]

        # Prepare request arguments
        kwargs = {
            "modelId": model_id,
            "messages": messages,
            "inferenceConfig": inference_config,
        }

        if include_system:
            kwargs["system"] = system_prompts

        # Stream response from Bedrock
        response_stream = self.bedrock_client.converse_stream(**kwargs)
        return response_stream
