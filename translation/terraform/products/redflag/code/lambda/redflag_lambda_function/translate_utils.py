# Translation examples provided to the LLM via the prompt - one shot inference to get better performances
translation_examples = {
    "German": {
        "example_source_language_text": """
        CUSTOMER: Was ist mit meiner Auszahlung los? Es sind schon mehr als 24 Stunden vergangen. AGENT: Willkommen beim XXX-Kundendienst! Mein Name ist YYY.  AGENT: Ich verstehe, dass es hier um Ihren Rückzug ZZZ geht. Vielen Dank, dass Sie uns diesbezüglich kontaktiert haben. Lassen Sie mich einen Blick darauf werfen, wie ich Ihnen helfen kann.
        """,
        "example_translated_text": """
        CUSTOMER: What's goin on with my withdrawal it's been over 24 hours   AGENT:  Welcome to XXX Customer Support! My name is YYY.  AGENT:  I understand that this is regarding your withdrawal ZZZ. Thank you for contacting us about this. Let me take a look at how I can help you.
        """
        },
    "Brazilian Portuguese": {
        "example_source_language_text": """
        CUSTOMER: O que está acontecendo com meu saque já se passaram mais de 24 horas AGENT: Bem-vindo ao Suporte ao Cliente XXX! Meu nome é YYY.  AGENT: Entendo que se trata de sua retirada ZZZ. Obrigado por nos contatar sobre isso. Deixe-me dar uma olhada em como posso ajudá-lo.
        """,
        "example_translated_text": """
        CUSTOMER: What's goin on with my withdrawal it's been over 24 hours   AGENT:  Welcome to XXX Customer Support! My name is YYY.  AGENT:  I understand that this is regarding your withdrawal ZZZ. Thank you for contacting us about this. Let me take a look at how I can help you.
        """
        },
    "Brazilian-Portuguese": {
        "example_source_language_text": """
        CUSTOMER: O que está acontecendo com meu saque já se passaram mais de 24 horas AGENT: Bem-vindo ao Suporte ao Cliente XXX! Meu nome é YYY.  AGENT: Entendo que se trata de sua retirada ZZZ. Obrigado por nos contatar sobre isso. Deixe-me dar uma olhada em como posso ajudá-lo.
        """,
        "example_translated_text": """
        CUSTOMER: What's goin on with my withdrawal it's been over 24 hours   AGENT:  Welcome to XXX Customer Support! My name is YYY.  AGENT:  I understand that this is regarding your withdrawal ZZZ. Thank you for contacting us about this. Let me take a look at how I can help you.
        """
        },
    "Portuguese-Brazilian": {
        "example_source_language_text": """
        CUSTOMER: O que está acontecendo com meu saque já se passaram mais de 24 horas AGENT: Bem-vindo ao Suporte ao Cliente XXX! Meu nome é YYY.  AGENT: Entendo que se trata de sua retirada ZZZ. Obrigado por nos contatar sobre isso. Deixe-me dar uma olhada em como posso ajudá-lo.
        """,
        "example_translated_text": """
        CUSTOMER: What's goin on with my withdrawal it's been over 24 hours   AGENT:  Welcome to XXX Customer Support! My name is YYY.  AGENT:  I understand that this is regarding your withdrawal ZZZ. Thank you for contacting us about this. Let me take a look at how I can help you.
        """
        },
    "Portuguese Brazilian": {
        "example_source_language_text": """
        CUSTOMER: O que está acontecendo com meu saque já se passaram mais de 24 horas AGENT: Bem-vindo ao Suporte ao Cliente XXX! Meu nome é YYY.  AGENT: Entendo que se trata de sua retirada ZZZ. Obrigado por nos contatar sobre isso. Deixe-me dar uma olhada em como posso ajudá-lo.
        """,
        "example_translated_text": """
        CUSTOMER: What's goin on with my withdrawal it's been over 24 hours   AGENT:  Welcome to XXX Customer Support! My name is YYY.  AGENT:  I understand that this is regarding your withdrawal ZZZ. Thank you for contacting us about this. Let me take a look at how I can help you.
        """
        },
    "Spanish": {
        "example_source_language_text": """
        CUSTOMER: ¿Qué está pasando con mi retiro? Han pasado más de 24 horas AGENT: ¡Bienvenido al servicio de atención al cliente de XXX! Mi nombre es AAA.  AGENT: Entiendo que esto se refiere a su retiro ZZZ. Gracias por contactarnos sobre esto. Déjame ver cómo puedo ayudarte.
        """,
        "example_translated_text": """
        CUSTOMER: What's goin on with my withdrawal it's been over 24 hours   AGENT:  Welcome to XXX Customer Support! My name is YYY.  AGENT:  I understand that this is regarding your withdrawal ZZZ. Thank you for contacting us about this. Let me take a look at how I can help you.
        """
        },
    "Greek": {
        "example_source_language_text": """
        CUSTOMER: Τι συμβαίνει με την απόσυρσή μου έχουν περάσει πάνω από 24 ώρες AGENT: Καλώς ήρθατε στην Υποστήριξη Πελατών XXX! Το όνομά μου είναι YYY.  AGENT: Καταλαβαίνω ότι πρόκειται για την απόσυρσή σας ZZZ. Σας ευχαριστούμε που επικοινωνήσατε μαζί μας σχετικά με αυτό. Επιτρέψτε μου να ρίξω μια ματιά στο πώς μπορώ να σας βοηθήσω.
        """,
        "example_translated_text": """
        CUSTOMER: What's goin on with my withdrawal it's been over 24 hours   AGENT:  Welcome to XXX Customer Support! My name is YYY.  AGENT:  I understand that this is regarding your withdrawal ZZZ. Thank you for contacting us about this. Let me take a look at how I can help you.
        """
        }
    }

# Prompt feeding into Titan LLM
prompt = """
You are a professional translator working in a customer service team for a betting company. Your task is to translate the given {source_language} text into English.
- Do not translate entities like names of people, team or places. Keep them in their original form.
- Do not translate the instruction strings: "TRANSLATE".
- Do not add explanations, examples, or any additional text. Only provide the direct English translation.
- Only translate the text provided in triple backticks (```)

Example:
TRANSLATE:
``
{example_source_language_text}
``

Answer:
``
{example_translated_text}
``

Now, translate the given text:
TRANSLATE: ```{sentences}```

Answer:
"""

prompt_llama = """
<|begin_of_text|><|start_header_id|>user<|end_header_id|>
You are a professional translator working in a customer service team for a betting company. Your task is to translate the given {source_language} text into English.
- Do not translate entities like names of people, team or places. Keep them in their original form.
- Do not translate the instruction strings: "TRANSLATE".
- Do not add explanations, examples, or any additional text. Only provide the direct English translation.
- Only translate the text provided in triple backticks (```)

Example:
TRANSLATE:
``
{example_source_language_text}
``

Answer:
``
{example_translated_text}
``

Now, translate the given text:
TRANSLATE: ```{sentences}```

Answer:
<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
"""


# Languages mapping to their langauge codes - only needed for Amazon Translate
language_map = {
    "English": "en",
    "German": "de",
    "Greek": "el",
    "Brazilian Portuguese": "pt",
    "Brazilian-Portuguese": "pt",
    "Portuguese-Brazilian": "pt",
    "Portuguese Brazilian": "pt",
    "Spanish": "es"
}

# Function to get language code
def get_language_code(language):
    return language_map.get(language)


# Red words that need to be translated in certain way regardless of the context
redwords_to_flag = ["ludópata","ludopata","enganchado"]
