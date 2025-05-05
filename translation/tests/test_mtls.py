
import requests

import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.fernet import Fernet
import os
from base64 import b64decode

def load_private_key(key_content, password):
    """
    Load private key from PEM content

    Args:
        key_content (bytes): Private key content in PEM format
        password (bytes, optional): Password if key is encrypted

    Returns:
        bytes: Private key in PEM format
    """
    try:
        private_key = serialization.load_pem_private_key(
            key_content,
            password=password,
        )
        # Convert to PEM format
        pem_private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        return pem_private_key

    except Exception as e:
        raise Exception(f"Failed to load private key: {str(e)}")

def make_mtls_request(url, cert_chain, cert_pem, private_key, key_password):
    """
    Make HTTPS request using mutual TLS authentication with support for encrypted private key

    Args:
        url (str): The URL to make the request to
        cert_chain (str): Path to the certificate chain file
        cert_pem (str): Path to the certificate file
        private_key (str): Encrypted private key content or path to private key file
        key_password (str, optional): Password for encrypted private key

    Returns:
        requests.Response: Response from the server
    """
    try:
        # If no encryption key provided, assume private_key is a file path
        with open(private_key, 'rb') as f:
            decrypted_key = f.read()
        key_password = key_password.encode()
        formatted_key = load_private_key(decrypted_key, key_password)

        # Create temporary file for the decrypted private key
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as temp_key_file:
            temp_key_file.write(formatted_key)
            temp_key_path = temp_key_file.name

        try:
            # Make request with cert and CA chain verification
            response = requests.post(
                url = url,
                json={
                "TicketId": "5457728",
                "ConversationId": "10163008360907",
                "TicketCreatedTime": "October 27, 2022, 08:50",
                "TranscriptEndTime": "October 27, 2022, 08:55",
                "Language": "English",
                "Label": "LabelName",
                "CustomerName": "James Zanzarelli",
                "CustomerCountry": "United Kingdom",
                "BotName": "Chatbot",
                "AgentName": "HHH Zanzarelli",
                "AgentTeamName": "AGENT TEAMNAME",
                "CustomerPriorityLevel": "P3",
                "TranscriptAuthorName": "System",
                "IncrementalTranscript": "HHH Zanzarelli: Hi How can I help you? \n\n James Zanzarelli:I am addicted to football. \n\n HHH Zanzarelli: ok let me check",
                "Category": "-",
                "OutboundCategory": "-",
                "Channel": "chat",
                "LoginStatus": "1",
                "RegisteredContact": "",
                "CustomerEmailID": "",
                "RecievedAtEmailId": "",
                "Subject": "Withdrawal Update",
                "AccountId": "12645678",
                "LabelPrefix": "fb"
                },
                cert=(cert_pem, temp_key_path),
                verify=cert_chain
            )

            return response

        finally:
            # Clean up temporary file
            os.unlink(temp_key_path)

    except Exception as e:
        raise Exception(f"Failed to make mTLS request: {str(e)}")

# Example usage
if __name__ == "__main__":
    password = os.environ.get("PRIVATE_KEY_PASSWORD", "redflag")
    cert_chain = os.environ.get("CERTIFICATE_CHAIN", "./certificate_chain.pem")
    cert = os.environ.get("CERTIFICATE", "./certificate.pem")
    private_key = os.environ.get("CERTIFICATE", "./private_key.pem")
    response = make_mtls_request(
        "https://redword.dsai-redword-flagger-dev.aws.local/redwords-dev",
        cert_chain,
        cert,
        private_key,  # Encrypted private key content # Reference to environment variable
        password
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
