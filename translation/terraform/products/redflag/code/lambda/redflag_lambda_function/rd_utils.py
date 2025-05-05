import re
from itertools import product
import os

import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
from nltk.tokenize import sent_tokenize
from nltk import pos_tag

import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Set up path for NLTK data
nltk_data_path = '/tmp/nltk_data'
nltk.data.path.append('/opt/python/nltk_data')


# Initialize the lemmatizer
lemmatizer = WordNetLemmatizer()


def log_execution_time(func):
    """Decorator to log execution time of a function."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"Function {func.__name__} executed in {end_time - start_time:.4f} seconds")
        return result
    return wrapper


def get_wordnet_pos(treebank_tag):
    """
    Convert a TreeBank POS tag to a WordNet POS tag.

    This function maps the part-of-speech (POS) tags from the TreeBank format,
    as used by NLTK's pos_tag function, to the format used by WordNet lemmatizer.

    :param treebank_tag: A POS tag in TreeBank format (e.g., 'NN', 'VB', 'JJ').
    :return: A WordNet POS tag (e.g., wordnet.NOUN, wordnet.VERB). Defaults to wordnet.NOUN.
    """
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.NOUN


def lemmatize_words(words):
    """
    Lemmatize individual words.

    :param words: List of words to normalize.
    :return: Normalized list of words.
    """
    # Perform POS tagging
    pos_tagged = nltk.pos_tag(words)

    # Normalize words with lemmatization
    normalized_words = [
        lemmatizer.lemmatize(word.lower(), pos=get_wordnet_pos(tag))
        for word, tag in pos_tagged
    ]
    return normalized_words


# Optimized flexible order check
def check_rules_any_order(normalized_words, sentence, keywords, max_distance, regex_patterns=None, regex_exclusion_patterns=None):
    """
    Check if a sequence of keywords is matched in any order within a sentence.

    This function first attempts regex-based matching with optional inclusion and
    exclusion patterns. If no regex match occurs, it checks for the presence of
    keywords in any order, ensuring that their positions fall within a specified
    maximum distance.

    :param normalized_words: List of normalized words from the sentence.
    :param sentence: The original sentence as a string.
    :param keywords: List of keywords to search for in the sentence.
    :param max_distance: Maximum allowable distance (in terms of word positions)
                         between the keywords in the sentence.
    :param regex_patterns: Optional list of regex patterns for inclusion matching.
    :param regex_exclusion_patterns: Optional list of regex patterns for exclusion.
    :return: A tuple (boolean_result, logic_source), where:
             - boolean_result: True if the keywords or regex match, False otherwise.
             - logic_source: "regex" if matched via regex, "flexible_order" otherwise.
    """
    # Use the full sentence for regex matching
    full_text = sentence.lower()

    # 1. Perform match_with_regex(full_text, regex_patterns) if regex_patterns is not None
    if regex_patterns:
        if match_with_regex(full_text, regex_patterns):
            # 2. Perform match_with_regex(full_text, regex_exclusion_patterns) only if regex_patterns matched
            #    and regex_exclusion_patterns is not None
            if regex_exclusion_patterns:
                if match_with_regex(full_text, regex_exclusion_patterns):
                    # 3. If regex_exclusion_patterns match, return False
                    return False, "regex"
            # 4. If regex_exclusion_patterns is None, return True
            return True, "regex"

    keywords = [word.lower() for word in keywords] # just added

    # 5. If regex_patterns do not match, perform the original strict order logic
    positions = [
        [i for i, word in enumerate(normalized_words) if word == keyword_set]
        for keyword_set in keywords
    ]
    # Debugging output
    #print(f"Normalized words: {normalized_words}")
    #print(f"Keyword positions: {positions}")

    if any(not pos for pos in positions):
        return False, "flexible_order"

    # Flatten positions for matching
    all_positions = sorted(set(pos for sublist in positions for pos in sublist))
    #print(f"All positions: {all_positions}")

    # Check valid combinations
    for i in range(len(all_positions) - len(keywords) + 1):
        if all_positions[i + len(keywords) - 1] - all_positions[i] <= max_distance:
            #print(f"Matched positions within max_distance: {all_positions}")
            return True, "flexible_order"

    print("No valid matches found within max_distance.")
    return False, "flexible_order"


def match_with_regex(full_text, regex_patterns):
    """
    Match a string against a list of regex patterns.

    This function performs case-insensitive regex matching to determine if the
    input text matches any of the provided patterns.

    :param full_text: The input text to be checked.
    :param regex_patterns: List of regex patterns to match against.
    :return: True if any pattern matches the input text, False otherwise.
    """
    for pattern in regex_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):  # Case-insensitive matching
            return True
    return False


def check_rules(normalized_words, sentence, keywords, max_distance, regex_patterns=None, regex_exclusion_patterns=None):
    """
    Check if a sequence of keywords is matched in strict order within a sentence.

    This function first attempts regex-based matching with optional inclusion and
    exclusion patterns. If no regex match occurs, it checks if the keywords appear
    in the sentence in strict order and within a specified maximum distance.

    :param normalized_words: List of normalized words from the sentence.
    :param sentence: The original sentence as a string.
    :param keywords: List of keywords to search for in strict order.
    :param max_distance: Maximum allowable distance (in terms of word positions)
                         between the first and last keywords in the sequence.
    :param regex_patterns: Optional list of regex patterns for inclusion matching.
    :param regex_exclusion_patterns: Optional list of regex patterns for exclusion.
    :return: A tuple (boolean_result, logic_source), where:
             - boolean_result: True if the keywords or regex match, False otherwise.
             - logic_source: "regex" if matched via regex, "strict_order" otherwise.
    """
    # Use the full sentence for regex matching
    full_text = sentence.lower()

    # 1. Perform match_with_regex(full_text, regex_patterns) if regex_patterns is not None
    if regex_patterns:
        if match_with_regex(full_text, regex_patterns):
            # 2. Perform match_with_regex(full_text, regex_exclusion_patterns) only if regex_patterns matched
            #    and regex_exclusion_patterns is not None
            if regex_exclusion_patterns:
                if match_with_regex(full_text, regex_exclusion_patterns):
                    # 3. If regex_exclusion_patterns match, return False
                    return False, "regex"
            # 4. If regex_exclusion_patterns is None, return True
            return True, "regex"

    # 5. If regex_patterns do not match, perform the original strict order logic
    positions = []
    keywords = [word.lower() for word in keywords] # just added
    for keyword in keywords:
        keyword_positions = [i for i, word in enumerate(normalized_words) if word == keyword]
        if not keyword_positions:
            return False, "strict_order"
        positions.append(keyword_positions)

    from itertools import product
    for combination in product(*positions):
        if list(combination) == sorted(combination):
            if max(combination) - min(combination) <= max_distance:
                return True, "strict_order"

    return False, "strict_order"


@log_execution_time
def replace_names_with_placeholders(transcript, name_mapping):
    """
    Replace actual names in the transcript with standardized placeholders.

    :param transcript: The raw transcript as a string.
    :param name_mapping: A dictionary mapping actual names to placeholders.
                         E.g., {"Alice": "CUSTOMER", "Bob": "AGENT"}
    :return: The transcript with names replaced by placeholders.
    """
    # for name, placeholder in name_mapping.items():
    #     transcript = re.sub(rf"\b{name}\b", placeholder, transcript)
    # return transcript

    for name, placeholder in name_mapping.items():
        if not name or not placeholder:  # Skip if either key or value is empty
            continue
        # transcript = re.sub(rf"\b{name}\b", placeholder, transcript)

        # Split full name into parts
        name_parts = name.split()

        # Create regex pattern that matches:
        # - The full name (e.g., "NAME1 NAME2 NAME3")
        # - Any combination of the words (e.g., "NAME1 NAME2", "NAME2 NAME1", "NAME1", "NAME2")
        pattern = r"\b(" + "|".join(map(re.escape, name_parts)) + r")\b"

        # Perform replacement
        transcript = re.sub(pattern, placeholder, transcript, flags=re.IGNORECASE)

    # Step 2: Remove "AGENT" if not preceded by a timestamp
    timestamp_pattern = r"\(\d{2}:\d{2}:\d{2}(?:\s[APM]{2})?\)"

    # Use regex to find all "AGENT" occurrences and check if preceded by a timestamp
    def remove_unless_timestamped(match):
        before_match = transcript[:match.start()]  # Get text before the match
        if re.search(timestamp_pattern + r"\s$", before_match):  # Check if preceded by a timestamp
            return match.group()  # Keep "AGENT"
        else:
            return ""  # Remove "AGENT"

    transcript = re.sub(r"\bAGENT\b", remove_unless_timestamped, transcript)

    return transcript


@log_execution_time
def preprocess_transcript(transcript):
    """
    Preprocess a transcript by adding a period before 'CUSTOMER', 'BOT', and 'AGENT'
    if the preceding text does not already end with a punctuation mark.

    This ensures that each sender label (e.g., 'CUSTOMER:', 'BOT:', 'AGENT:') is
    properly preceded by punctuation for better parsing.

    :param transcript: The raw transcript as a string.
    :return: The preprocessed transcript with adjusted punctuation.
    """
    # Regular expression to find occurrences of CUSTOMER, BOT, AGENT without a preceding period or punctuation
    transcript = re.sub(
        r"(?<![.!?])\s+((?:CUSTOMER|BOT|AGENT)(?:\s+[A-Za-z]+)*):?",
        r". \1:",
        transcript
    )
    return transcript.strip()


@log_execution_time
def parse_transcript(transcript):
    """
    Parse a transcript into a list of sender-message pairs.

    This function splits the transcript into segments based on sender labels
    (e.g., 'CUSTOMER:', 'BOT:', 'AGENT:') and extracts the sender and their
    respective messages into structured dictionaries.

    :param transcript: The preprocessed transcript as a string.
    :return: A list of dictionaries, each containing:
             - 'sender': The sender label (e.g., 'CUSTOMER', 'BOT', 'AGENT').
             - 'message': The corresponding message text.
    """
    messages = []
    parts = re.split(r"(?=(?:(?:CUSTOMER|BOT|AGENT)(?:\s+[A-Za-z]+)*:))", transcript)
    for part in parts:
        part = part.strip()
        if "AGENT:" in part:
            sender, message = part.split("AGENT:", 1)
            sender = "AGENT"
            message = message.strip()
            messages.append({"sender": sender, "message": message})
        if "BOT:" in part:
            sender, message = part.split("BOT:", 1)
            sender = "BOT"
            message = message.strip()
            messages.append({"sender": sender, "message": message})
        if "CUSTOMER:" in part:
            sender, message = part.split("CUSTOMER:", 1)
            sender = "CUSTOMER"
            message = message.strip()
            messages.append({"sender": sender, "message": message})
    return messages


@log_execution_time
def flag_sentences(sentences, rules, name_mapping, debug=False):
    """
    Flag sentences by matching them against predefined rules.

    This function processes a list of sentences to identify those that match
    specific rules. It uses regex patterns and keyword-based logic (flexible or strict order)
    to detect matches and returns details about the matched rules, keywords,
    and the flagged sentences.

    :param sentences: A string containing one or more sentences to process.
    :param rules: A list of dictionaries, where each dictionary defines a rule with:
                  - 'keywords': List of keywords to match.
                  - 'max_distance': Maximum allowable distance between keywords.
                  - 'regex_patterns': Optional list of regex patterns for inclusion matching.
                  - 'regex_exclusion_patterns': Optional list of regex patterns for exclusion.
                  - 'flexible_order': Boolean indicating whether flexible order matching is allowed.
    :param name_mapping: A dictionary containing the mapping of customer's and agent's names to be replaced with placeholders.
    :param channel: string defining channel of the transcript to process
    :param debug: Boolean flag to enable debug output for troubleshooting.
    :return: A tuple containing:
             - flagged (bool): True if any rule matches, False otherwise.
             - sentence_to_rule (list): A list of tuples, where each tuple contains:
                                        - The flagged sentence.
                                        - A list of keywords associated with the matched rules.
    """
    matched_rules = []
    matched_keywords = []
    matched_logic = []
    flagged_sentences = []  # List to store flagged sentences
    sentence_to_rule_map = {}  # Dictionary to map sentences to aggregated keywords

    tokenization_start = time.time()
    all_sentences = []

    sentences_names_replaced = replace_names_with_placeholders(sentences, name_mapping)
    processed_transcript = preprocess_transcript(sentences_names_replaced)
    messages = parse_transcript(processed_transcript)  # Parse messages into sender and text

    # if "CUSTOMER" not in processed_transcript:
    if ("CUSTOMER" not in processed_transcript) or ("CUSTOMER:@" in processed_transcript) or ("Web User" in processed_transcript):
        messages = [{"sender": "CUSTOMER", "message": sentences}]

    # Process each customer message or block of text
    for entry in messages:
        #if entry['sender'].lower() == "customer":
        if "customer" in entry['sender'].lower():
            #sentences = sent_tokenize(entry['message'])  # Split customer message into sentences
            all_sentences.extend(sent_tokenize(entry['message']))

    tokenization_end = time.time()
    print(f"Total sentence tokenization time: {tokenization_end - tokenization_start:.4f} seconds")

    rules_start = time.time()
    for sentence in all_sentences:
        words = re.findall(r'\b\w+\b', sentence.lower())
        normalized_words = lemmatize_words(words)

        for rule in rules:
            if rule.get("flexible_order", False):
                result, logic = check_rules_any_order(normalized_words, sentence, rule['keywords'], rule['max_distance'],
                                            rule.get('regex_patterns'), rule.get('regex_exclusion_patterns'))
            else:
                result, logic = check_rules(normalized_words, sentence, rule['keywords'], rule['max_distance'],
                                            rule.get('regex_patterns'), rule.get('regex_exclusion_patterns'))

            if result:
                matched_rules.append(rule)
                matched_keywords.append(rule['keywords'])
                matched_logic.append(logic)
                flagged_sentences.append(sentence)
                # Aggregate keywords for the sentence
                if sentence not in sentence_to_rule_map:
                    sentence_to_rule_map[sentence] = set(rule['keywords'])
                else:
                    sentence_to_rule_map[sentence].update(rule['keywords'])

    rules_end = time.time()
    print(f"Total rules application time: {rules_end - rules_start:.4f} seconds")

    # Convert the sentence-to-rule mapping to a list with sorted keywords
    sentence_to_rule = [(sentence, sorted(list(keywords))) for sentence, keywords in sentence_to_rule_map.items()]

    # Remove duplicates
    matched_rules = list({str(rule): rule for rule in matched_rules}.values())
    matched_keywords = list({str(rule): keywords for rule, keywords in zip(matched_rules, matched_keywords)}.values())
    matched_logic = list({str(rule): logic for rule, logic in zip(matched_rules, matched_logic)}.values())
    flagged_sentences = list(set(flagged_sentences))  # Remove duplicate sentences

    if debug and matched_rules:
        print(f"Any Sentence flagged: {bool(matched_rules)}")
        print(f"Sentence-to-Rule Mapping: {sentence_to_rule}")  # Debug sentence-to-rule mapping

    return bool(matched_rules), sentence_to_rule
