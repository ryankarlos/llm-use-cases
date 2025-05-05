import json
import rd_utils as rd
import translate_utils as tu
import rd_config
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, ReadTimeoutError
import logging
import time
from concurrent.futures import ThreadPoolExecutor
import configparser
from datetime import datetime

import threading

import os
import re

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

#s3 connection
s3_client = boto3.client('s3')

S3_BUCKET_NAME = os.getenv('S3_LOGS_BUCKET')
LOG_FOLDER = "redword-flagger-logs/"
# Import Red Words rules
rules = rd_config.load_rules()


# Import config
config = rd_config.load_config()

# AWS Bedrock service parameters
aws_region = config["aws"]["region"]
aws_service_name = config["aws"]["service_name"]
model_id_titan = config["model"]["model_id_titan"]
model_id_mistral = config["model"]["model_id_mistral"]

# LLM parameters
chunking_length_threshold = int(config["chunking"]["chunking_length_threshold"])
chunking_length_threshold_el = int(config["chunking"]["chunking_length_threshold_el"])
chunking_length_threshold_pt = int(config["chunking"]["chunking_length_threshold_pt"])
split_threshold = int(config["chunking"]["split_threshold"])
max_workers = int(config["chunking"]["max_workers"])

redwords_to_flag = tu.redwords_to_flag

# Set Bedrock parameters
my_config = Config(region_name = aws_region, retries={"total_max_attempts": 1}, read_timeout=50, connect_timeout=5)
brt = boto3.client(service_name = aws_service_name, config = my_config)

# Set Amazon translate client
translate_client = boto3.client('translate')


def translate_with_titan(prompt, model_id):
    """Helper function to translate using Amazon Titan with timeout handling"""
    native_request = {
        "inputText": prompt,
        "textGenerationConfig": {"maxTokenCount": 8192, "temperature": 0.0, "topP": 0.9},
    }
    request = json.dumps(native_request)

    response = brt.invoke_model(modelId=model_id, body=request)
    model_response = json.loads(response["body"].read())
    return model_response["results"][0]["outputText"]


def translate_with_mistral(formatted_prompt, model_id):
    """Helper function to translate using Mistral with timeout handling"""
    native_request = {
        "prompt": formatted_prompt,
        "max_tokens": 8192,
        "temperature": 0.0,
    }
    request = json.dumps(native_request)

    response = brt.invoke_model(modelId=model_id, body=request)
    model_response = json.loads(response["body"].read())
    return model_response["outputs"][0]["text"]


def translate_with_amazon_translate(text, source_language_code):
    """Helper function to translate using Amazon Translate"""
    translate_response = translate_client.translate_text(
        Text=text,
        SourceLanguageCode=source_language_code,
        TargetLanguageCode="en"
    )
    return translate_response["TranslatedText"]


def run_titan_translation(prompt, model_id, output):
    """Helper function to call Bedrock API inside a thread"""
    try:
        output["result"] = translate_with_titan(prompt, model_id)
    except Exception as e:
        output["error"] = str(e)


def run_mistral_translation(formatted_prompt, model_id, output):
    """Helper function to call Bedrock API inside a thread"""
    try:
        output["result"] = translate_with_mistral(formatted_prompt, model_id)
    except Exception as e:
        output["error"] = str(e)



def lambda_handler(event, context):
    logger.info("Lambda function started.")

    # Extract inputs from the event payload
    sentences = event['IncrementalTranscript']
    source_language = event['Language']
    name_mapping = {
    event['CustomerName']: "CUSTOMER",
    event['AgentName']: "AGENT"
        }
    channel = event["Channel"]
    source_language_code = tu.get_language_code(source_language)
    ticket_id = event["TicketId"]
    conversation_id = event["ConversationId"]

    # Get the example translation source and translated texts to feed into Bedrock's LLM prompt
    example_translations = tu.translation_examples.get(source_language, {})
    example_source_language_text = example_translations.get("example_source_language_text", "")
    example_translated_text = example_translations.get("example_translated_text", "")

    logger.info(f"Input received: ticket_id={ticket_id}, conversation_id={conversation_id}, source_language={source_language}, length of sentences={len(sentences)}")

    # Initialize translation service tracker
    translation_service_used = None

    if channel.lower() != "chat":
        flagged = False
        sentence_to_rule = None
        sentences_to_flag = None
        translation_service_used = "No Translation Service"
        overall_translation_time = 0.0
        rd_total_time = 0.0
        logger.info("Channel not set as chat, skipping whole Red Words logic and setting response as 0.")

    else:
        if source_language.lower() in ("english","en"):
            # If the source language is English, skip translation
            logger.info("Source language is English, skipping translation.")
            sentences_to_flag = sentences
            translation_service_used = "No Translation Service"
            overall_translation_time = 0.0
        else:
            logger.info("Source language is not English, starting translation.")

            if len(sentences) >= chunking_length_threshold or \
                (source_language_code == "el" and len(sentences) > chunking_length_threshold_el) or \
                (source_language_code == "pt" and len(sentences) > chunking_length_threshold_pt):

                for attempt in range (1,3): # Maximum 2 attempts (1st Mistral, 2nd Amazon Translate if needed)
                    logger.info(f"Translation attempt {attempt} of 2")

                    # Chunking is required
                    logger.info(f"Chunking is required due to sentence length: {len(sentences)}")
                    markers = ["CUSTOMER:", "CUSTOMER NAME:", "AGENT:", "AGENT NAME:", "BOT:"]
                    split_index = chunking_length_threshold
                    closest_index = -1

                    # Find a suitable splitting point
                    for marker in markers:
                        index = sentences.rfind(marker, 0, chunking_length_threshold + 500)
                        if index != -1 and index > closest_index:
                            closest_index = index

                    if closest_index != -1:
                        split_index = closest_index

                    # Create initial chunks
                    chunk1 = sentences[:split_index]
                    chunk2 = sentences[split_index:]

                    # Further split chunks if necessary
                    secondary_chunks1 = (
                        [chunk1[i : i + split_threshold] for i in range(0, len(chunk1), split_threshold)]
                        if len(chunk1) > split_threshold
                        else [chunk1]
                        )
                    secondary_chunks2 = (
                        [chunk2[i : i + split_threshold] for i in range(0, len(chunk2), split_threshold)]
                        if len(chunk2) > split_threshold
                        else [chunk2]
                        )

                    # Combine all chunks
                    chunks = secondary_chunks1 + secondary_chunks2
                    # Drop empty chunks (if any)
                    chunks = [chunk for chunk in chunks if chunk.strip()]
                    logger.info(f"Final chunks created: {[len(c) for c in chunks]}")

                    # Function to translate a single chunk using either Mistral or Amazon Translate
                    def translate_chunk(chunk, source_language_code):
                        nonlocal translation_service_used
                        if source_language_code == "el":
                            try:
                                logger.info(f"Invoking Amazon Translate for chunk with length={len(chunk)}.")
                                start_time = time.time()
                                translated_text = translate_with_amazon_translate(chunk, source_language_code)
                                api_call_time = time.time() - start_time
                                logger.info(f"Amazon Translate API call for chunk (length={len(chunk)}) took {api_call_time:.2f} seconds.")
                                translation_service_used = "Amazon Translate"
                                return translated_text
                            except Exception as e:
                                logger.error(f"Error invoking Amazon Translate: {e}")
                                return None
                        else:
                            try:
                                logger.info(f"Invoking Mistral for chunk with length={len(chunk)}.")
                                start_time = time.time()
                                prompt = tu.prompt.format(
                                        source_language=source_language,
                                        sentences=chunk,  # Ensure correct input format
                                        example_source_language_text=example_source_language_text,
                                        example_translated_text=example_translated_text,
                                    )

                                # Embed the prompt in Mistral's instruction format.
                                formatted_prompt = f"<s>[INST] {prompt} [/INST]"
                                translated_text = translate_with_mistral(formatted_prompt, model_id_mistral)
                                api_call_time = time.time() - start_time
                                logger.info(f"Mistral API call for chunk (length={len(chunk)}) took {api_call_time:.2f} seconds.")
                                translation_service_used = "Mistral LLM"
                                return translated_text
                            except Exception as e:
                                logger.error(f"Error invoking Mistral: {e}")
                                return None


                    # Process chunks in parallel using ThreadPoolExecutor
                    overall_start_time = time.time()
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        translated_chunks = list(executor.map(lambda chunk: translate_chunk(chunk, source_language_code), chunks))


                    # Remove failed translations
                    translated_chunks = [chunk for chunk in translated_chunks if chunk]

                    # Log total translation time
                    overall_translation_time = time.time() - overall_start_time
                    logger.info(f"Total wall-clock time for translating all chunks in parallel: {overall_translation_time:.2f} seconds.")
                    logger.info(f"Note: Individual chunk translation times may sum to more due to parallel execution.")

                    # Check if all chunks were translated successfully
                    if len(translated_chunks) == len(chunks):
                        sentences_to_flag = " ".join(translated_chunks)
                        logger.info("All chunks translated and merged successfully.")
                        break  # Exit the retry loop as the translation was successful
                    else:
                        failed_chunks = len(chunks) - len(translated_chunks)
                        logger.warning(f"Translation failed for {failed_chunks} chunks.")

                        # If this was the first attempt (Mistral), retry with Amazon Translate
                        if attempt == 1 and source_language_code != "el":
                            logger.info("Retrying translation with Amazon Translate for all chunks.")

                            # Switch to Amazon Translate
                            translation_service_used = "Amazon Translate"
                            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                                translated_chunks = list(executor.map(lambda chunk: translate_with_amazon_translate(chunk, source_language_code), chunks))

                            # Remove failed translations again
                            translated_chunks = [chunk for chunk in translated_chunks if chunk]

                            # Check if Amazon Translate succeeded
                            if len(translated_chunks) == len(chunks):
                                sentences_to_flag = " ".join(translated_chunks)
                                logger.info("Amazon Translate successfully translated all chunks.")
                                break
                            else:
                                logger.error("Amazon Translate also failed for some chunks.")
                        else:
                            logger.error("Max retries reached. Translation failed.")
                            sentences_to_flag = None  # Prevent further processing

            else:
                if (source_language_code == "el"):
                    # Try Amazon Titan translation with a 50-second timeout
                    logger.info("No chunking required. Attempting Amazon Titan translation with 50-second timeout.")
                    overall_start_time = time.time()

                    prompt = tu.prompt.format(
                        source_language=source_language,
                        sentences=sentences,  # Ensure correct input format
                        example_source_language_text=example_source_language_text,
                        example_translated_text=example_translated_text,
                    )

                    # Dictionary to store output
                    output = {}

                    # Start Amazon Titan translation in a separate thread
                    titan_thread = threading.Thread(target=run_titan_translation, args=(prompt, model_id_titan, output))
                    titan_thread.start()
                    titan_thread.join(timeout=50)

                    #  Check if Amazon Titan translation exceeded the timeout
                    if titan_thread.is_alive():
                        logger.warning("Amazon Titan translation timed out after 50 seconds. Falling back to Amazon Translate.")

                        # Amazon Titan call exceeded timeout; fallback to Amazon Translate
                        sentences_to_flag = translate_with_amazon_translate(sentences, source_language_code)
                        translation_service_used = "Amazon Translate"
                        logger.info("Amazon Translate fallback completed successfully.")

                    else:
                        # Define known Amazon Titan refusal messages
                        refusal_messages = ["Sorry - this model is unable to respond to this request."]

                        # Amazon Titan finished within 50 seconds
                        sentences_to_flag = output.get("result", None)
                        if not sentences_to_flag or (isinstance(sentences_to_flag, str) and sentences_to_flag.strip() in ["", "```\n\n```"]) or not isinstance(sentences_to_flag, str):
                            logger.info("Amazon Titan returned empty translation or not a string as expected - run Amazon Translate.")
                            sentences_to_flag = translate_with_amazon_translate(sentences, source_language_code)
                            translation_service_used = "Amazon Translate"
                            logger.info("Amazon Translate fallback completed successfully.")
                        elif (len(sentences_to_flag) < len(sentences) / 2) or (any(msg in sentences_to_flag.strip() for msg in refusal_messages)):
                            logger.info("Amazon Titan hallucinated - running Amazon Translate.")
                            sentences_to_flag = translate_with_amazon_translate(sentences, source_language_code)
                            translation_service_used = "Amazon Translate"
                            logger.info("Amazon Translate fallback completed successfully.")
                        elif sentences_to_flag:
                            logger.info("Amazon Titan translation completed successfully.")
                            translation_service_used = "Amazon Titan"
                        else:
                            logger.error(f"Amazon Titan translation failed: {output.get('error', 'Unknown error')}")
                            logger.info("Falling back to Amazon Translate due to Titan failure.")
                            sentences_to_flag = translate_with_amazon_translate(sentences, source_language_code)
                            translation_service_used = "Amazon Translate"
                            logger.info("Amazon Translate fallback completed successfully.")
                    # Log translation duration
                    overall_translation_time = time.time() - overall_start_time
                    logger.info(f"Total time for translation: {overall_translation_time:.2f} seconds.")
                else:
                    # Try Mistral translation with a 50-second timeout
                    logger.info("No chunking required. Attempting Mistral translation with 50-second timeout.")
                    overall_start_time = time.time()

                    prompt = tu.prompt.format(
                        source_language=source_language,
                        sentences=sentences,  # Ensure correct input format
                        example_source_language_text=example_source_language_text,
                        example_translated_text=example_translated_text,
                    )

                    # Embed the prompt in Mistral's instruction format.
                    formatted_prompt = f"<s>[INST] {prompt} [/INST]"

                    # Dictionary to store output
                    output = {}

                    # Start Mistral translation in a separate thread
                    mistral_thread = threading.Thread(target=run_mistral_translation, args=(formatted_prompt, model_id_mistral, output))
                    mistral_thread.start()
                    mistral_thread.join(timeout=50)

                    #  Check if Mistral translation exceeded the timeout
                    if mistral_thread.is_alive():
                        logger.warning("Mistral translation timed out after 50 seconds. Falling back to Amazon Translate.")

                        # Mistral call exceeded timeout; fallback to Amazon Translate
                        sentences_to_flag = translate_with_amazon_translate(sentences, source_language_code)
                        translation_service_used = "Amazon Translate"
                        logger.info("Amazon Translate fallback completed successfully.")

                    else:
                        # Mistral finished within 50 seconds
                        sentences_to_flag = output.get("result", None)
                        if not sentences_to_flag or (isinstance(sentences_to_flag, str) and sentences_to_flag.strip() in ["", "```\n\n```"]) or not isinstance(sentences_to_flag, str):
                            logger.info("Mistral returned empty translation or not a string as expected - run Amazon Translate.")
                            sentences_to_flag = translate_with_amazon_translate(sentences, source_language_code)
                            translation_service_used = "Amazon Translate"
                            logger.info("Amazon Translate fallback completed successfully.")
                        elif (len(sentences_to_flag) < len(sentences) / 2):
                            logger.info("Mistral hallucinated - running Amazon Translate.")
                            sentences_to_flag = translate_with_amazon_translate(sentences, source_language_code)
                            translation_service_used = "Amazon Translate"
                            logger.info("Amazon Translate fallback completed successfully.")
                        elif sentences_to_flag:
                            logger.info("Mistral translation completed successfully.")
                            translation_service_used = "Mistral LLM"
                        else:
                            logger.error(f"Mistral translation failed: {output.get('error', 'Unknown error')}")
                            logger.info("Falling back to Amazon Translate due to Mistral failure.")
                            sentences_to_flag = translate_with_amazon_translate(sentences, source_language_code)
                            translation_service_used = "Amazon Translate"
                            logger.info("Amazon Translate fallback completed successfully.")
                    # Log translation duration
                    overall_translation_time = time.time() - overall_start_time
                    logger.info(f"Total time for translation: {overall_translation_time:.2f} seconds.")

        # Apply Red Words logic if translation was successful
        if sentences_to_flag:
            if source_language.lower() in ("spanish","es"):
                pattern = "|".join(redwords_to_flag)
                if re.search(pattern, sentences, re.IGNORECASE):
                    logger.info(f"Make sure that certain Spanish terms for addiciton are translated as expected.")
                    if sentences_to_flag.endswith("```"):
                        sentences_to_flag = sentences_to_flag[:-3] + "CUSTOMER: I am addicted```"
                    else:
                        sentences_to_flag += " CUSTOMER: I am addicted"

            logger.info("Applying Red Words logic.")
            rd_start_time = time.time()
            flagged, sentence_to_rule = rd.flag_sentences(sentences_to_flag, rules, name_mapping, debug=True)
            rd_total_time = time.time() - rd_start_time
        else:
            flagged, sentence_to_rule = False, []

        logger.info("Application Red Words logic ended.")

    # Prepare and return response
    data = {
        "red_word_flag": int(flagged)
        }
    logger.info("Lambda function completed successfully.")
    #logging into s3 buckets
    date = str(datetime.today().strftime('%Y-%m-%d'))
    logs = {
        "red_word_flag": int(flagged),
        "sentences_flagged": sentence_to_rule,
        # "sentences_to_flag": sentences_to_flag,
        "ticket_id": ticket_id,
        "conversation_id":conversation_id,
        "create_timestamp": event["TicketCreatedTime"],
        "language":source_language,
        "channel": channel,
        "translation_service_used": translation_service_used,
        "total_translation_time": overall_translation_time,
        "total_engine_time": overall_translation_time + rd_total_time
        }
    json_logs = json.dumps(logs, indent=4)
    log_filename = f"{LOG_FOLDER}{date}/logs_{conversation_id}_{int(time.time())}.json"
    s3_client.put_object(
    Bucket=S3_BUCKET_NAME,
    Key=log_filename,
    Body=json_logs.encode('utf-8'),
    ContentType="application/json"
    )
    return data
