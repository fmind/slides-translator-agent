"""Tools for the agents."""

# %% IMPORTS

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from google.adk.tools import ToolContext
from google.auth.transport.requests import Request
from google.genai import Client
from google.genai.types import GenerateContentConfig, ThinkingConfig
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from slides_translator_agent import auths, configs

# %% HELPERS


def setup_logger(presentation_id: str, tool_context: ToolContext) -> logging.Logger:
    """Initialize and configure a logger for the tool."""
    invocation_id = tool_context.invocation_id
    user_id = tool_context.session.user_id
    session_id = tool_context.session.id
    logger_name = (
        f"{__name__}:"
        f"user:{user_id},"
        f"session:{session_id},"
        f"invocation:{invocation_id},"
        f"presentation:{presentation_id}"
    )
    return logging.getLogger(logger_name)


def negotiate_creds(tool_context: ToolContext, logger: logging.Logger) -> Credentials | dict:
    """Handle the OAuth 2.0 flow to get valid credentials."""
    logger.info("Negotiating credentials")
    # 1. Check for cached credentials in the tool state
    if cached_token := tool_context.state.get(configs.TOKEN_CACHE_KEY):
        logger.debug("Found cached token")
        try:
            creds = Credentials.from_authorized_user_info(cached_token, auths.SCOPES.keys())
            if creds.valid:
                logger.debug("Cached credentials are valid")
                return creds
            if creds.expired and creds.refresh_token:
                logger.debug("Cached credentials expired, attempting refresh")
                creds.refresh(Request())
                tool_context.state[configs.TOKEN_CACHE_KEY] = json.loads(creds.to_json())
                logger.debug("Credentials refreshed and cached successfully")
                return creds
        except Exception as error:
            logger.error(f"Error loading/refreshing cached credentials: {error}")
            tool_context.state[configs.TOKEN_CACHE_KEY] = None  # reset cache
    # 2. If no valid cached credentials, check for auth response
    logger.debug("No valid cached token. Checking for auth response")
    if exchanged_creds := tool_context.get_auth_response(auths.AUTH_CONFIG):
        logger.debug("Received auth response, creating credentials")
        auth_scheme = auths.AUTH_CONFIG.auth_scheme
        auth_credential = auths.AUTH_CONFIG.raw_auth_credential
        creds = Credentials(
            token=exchanged_creds.oauth2.access_token,
            refresh_token=exchanged_creds.oauth2.refresh_token,
            token_uri=auth_scheme.flows.authorizationCode.tokenUrl,
            client_id=auth_credential.oauth2.client_id,
            client_secret=auth_credential.oauth2.client_secret,
            scopes=list(auth_scheme.flows.authorizationCode.scopes.keys()),
        )
        tool_context.state[configs.TOKEN_CACHE_KEY] = json.loads(creds.to_json())
        logger.debug("New credentials created and cached successfully")
        return creds
    # 3. If no auth response, initiate auth request
    logger.debug("No credentials available. Requesting user authentication")
    tool_context.request_credential(auths.AUTH_CONFIG)
    logger.info("Awaiting user authentication")
    return {"pending": True, "message": "Awaiting user authentication"}


def copy_presentation(
    drive_service,
    slides_service,
    presentation_id: str,
    target_language: str,
    logger: logging.Logger,
) -> dict[str, str]:
    """Copy the original presentation and return details of the new one."""
    logger.info(f"Copying presentation '{presentation_id}' for target language '{target_language}'")
    # original presentation
    logger.debug(f"Getting original presentation by ID: '{presentation_id}'")
    original_presentation = (
        slides_service.presentations().get(presentationId=presentation_id).execute()
    )
    original_presentation_title = original_presentation.get("title", "Untitled")
    # copy presentation
    copy_presentation_title = f"{original_presentation_title} ({target_language})"
    logger.debug(
        f"Original title: '{original_presentation_title}', New title: '{copy_presentation_title}'"
    )
    copy_presentation_body = {"name": copy_presentation_title}
    logger.debug(
        f"Copying file with ID '{presentation_id}' and new title '{copy_presentation_title}'"
    )
    copy_presentation = (
        drive_service.files().copy(fileId=presentation_id, body=copy_presentation_body).execute()
    )
    copy_presentation_id = copy_presentation["id"]
    copy_presentation_url = f"https://docs.google.com/presentation/d/{copy_presentation_id}/edit"
    result = {
        "presentation_id": copy_presentation_id,
        "presentation_url": copy_presentation_url,
        "presentation_title": copy_presentation_title,
    }
    logger.info(
        f"Successfully copied presentation. New presentation ID: '{copy_presentation_id}',"
        f" URL: '{copy_presentation_url}', Title: '{copy_presentation_title}'"
    )
    return result


def initialize_services(creds: Credentials, logger: logging.Logger) -> tuple[Any, Any, Client]:
    """Initialize and return Google API services."""
    logger.info("Initializing Google API services")
    drive_service = build("drive", "v3", credentials=creds)
    slides_service = build("slides", "v1", credentials=creds)
    genai_service = Client(
        project=configs.PROJECT_ID, location=configs.PROJECT_LOCATION, vertexai=True
    )
    logger.info("Google API services initialized")
    return drive_service, slides_service, genai_service


def _extract_text_from_page_elements(
    page_elements: list, slide_id: str, index: dict[str, list[str]]
):
    """Recursively extract text from page elements."""
    for element in page_elements:
        if "shape" in element and "text" in element["shape"]:
            for text_element in element["shape"]["text"].get("textElements", []):
                if "textRun" in text_element:
                    content = text_element["textRun"]["content"].strip()
                    if content and re.search("[a-zA-Z]", content):
                        if content not in index:
                            index[content] = set()
                        index[content].add(slide_id)
        elif "group" in element:
            _extract_text_from_page_elements(element["group"].get("children", []), slide_id, index)
        elif "table" in element:
            for row in element["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    _extract_text_from_page_elements(
                        cell.get("text", {}).get("textElements", []), slide_id, index
                    )


def index_presentation_texts(
    slides_service, presentation_id: str, logger: logging.Logger
) -> dict[str, list[str]]:
    """Extract all text run elements from a presentation to a location index."""
    logger.info(f"Extracting text from presentation: '{presentation_id}'")
    presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
    slides = presentation.get("slides", [])
    logger.debug(f"Found {len(slides)} slides in '{presentation_id}'")
    index = {}
    for slide in slides:
        slide_id = slide["objectId"]
        _extract_text_from_page_elements(slide.get("pageElements", []), slide_id, index)
    logger.info(
        f"Found {len(index)} unique texts across {len(slides)} slides in '{presentation_id}'"
    )
    return index


def translate_texts_with_genai(
    genai_service: Client,
    target_language: str,
    extra_context: str,
    texts: list[str],
    logger: logging.Logger,
) -> tuple[dict, list]:
    """Translate a list of texts"""
    translations = {}
    total_usages = {
        "input_tokens": 0,
        "output_tokens": 0,
    }
    model_name = configs.MODEL_NAME_TRANSLATION
    max_workers = configs.CONCURRENT_TRANSLATION_WORKERS
    logger.info(
        f"Translating {len(texts)} texts to '{target_language}' using '{model_name}' with {max_workers} workers"
    )
    instructions = (
        f"Translate the following text to '{target_language}' as accurately as possible. "
        "Do not add any preamble, intro, or explanation; just return the translated text. "
        f"Use the following user context to help perform the translation task: '{extra_context}'"
    )

    def translate_text(text):
        """Translate a single text string"""
        try:
            response = genai_service.models.generate_content(
                model=model_name,
                contents=text,
                config=GenerateContentConfig(
                    temperature=0.0,
                    system_instruction=instructions,
                    thinking_config=ThinkingConfig(thinking_budget=0),
                ),
            )
            usage = response.usage_metadata
            translation = response.text.strip()
            return text, translation, usage
        except Exception as error:
            logger.error(f"Translation error for '{text}': {error}")
            return text, None, None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(translate_text, text) for text in texts]
        for i, future in enumerate(as_completed(futures)):
            text, translation, usage = future.result()
            if usage:
                total_usages["input_tokens"] += usage.prompt_token_count
                total_usages["output_tokens"] += usage.candidates_token_count
            if translation:
                translations[text] = translation
    logger.info(f"Finished translating {len(translations)} out of {len(texts)} texts")
    logger.info(f"Total token usage for translations: {total_usages}")
    return translations, total_usages


def replace_text_in_presentation(
    slides_service,
    presentation_id: str,
    translations: dict[str, str],
    index: dict[str, list[str]],
    logger: logging.Logger,
) -> int:
    """Replace all text elements in the presentation with the provided translations."""
    logger.info(f"Updating presentation '{presentation_id}' with {len(translations)} translations")
    sorted_translations = sorted(translations.items(), key=lambda item: len(item[0]), reverse=True)
    batch_size = configs.CONCURRENT_SLIDES_BATCH_UPDATES
    total_changes = 0
    requests = []
    for text, translation in sorted_translations:
        if translation.strip():
            page_ids = index.get(text)
            if page_ids:
                request = {
                    "replaceAllText": {
                        "replaceText": translation,
                        "pageObjectIds": list(page_ids),
                        "containsText": {"text": text, "matchCase": True},
                    }
                }
                requests.append(request)
    logger.info(f"Created {len(requests)} change requests for '{presentation_id}'")
    for i, start in enumerate(range(0, len(requests), batch_size)):
        stop = start + batch_size
        batch = requests[start:stop]
        body = {"requests": batch}
        response = (
            slides_service.presentations()
            .batchUpdate(presentationId=presentation_id, body=body)
            .execute()
        )
        changes = sum(
            reply.get("replaceAllText", {}).get("occurrencesChanged", 0)
            for reply in response.get("replies", [])
        )
        total_changes += changes
    logger.info(f"Finished replace texts in '{presentation_id}'. Total changes: {total_changes}")
    return total_changes


# %% TOOLS


def translate_presentation(
    presentation_id: str,
    target_language: str,
    slides_context: str,
    tool_context: ToolContext,
) -> dict:
    """Copy and translate a Google Slides presentation and returns the new presentation URL.

    Args:
        presentation_id: The ID of the Google Slides presentation to translate.
            Example: "1234567890abcdefghijklmnopqrstuvwxyz"
        target_language: The English language name to translate the text into.
            Example: "Spanish", "French", "German"
        slides_context: Optional user context to guide the translation model.
            Example: "The presentation is for a technical audience"
        tool_context: The ADK tool context. Provided automatically by ADK.

    Returns:
        A dictionary with information about the translation process,
        may return a demand for a user authentication request
    """
    # Logger initialization
    logger = setup_logger(presentation_id, tool_context)
    logger.info(
        f"Translating presentation '{presentation_id}' to '{target_language}' for '{slides_context}'"
    )
    # Negociate auth credentials
    auth_result = negotiate_creds(tool_context, logger=logger)
    if isinstance(auth_result, dict):  # new auth request
        return auth_result
    creds = auth_result
    # Initialize Google API services
    drive_service, slides_service, genai_service = initialize_services(creds, logger)
    # Copy the original presentation
    new_presentation = copy_presentation(
        drive_service, slides_service, presentation_id, target_language, logger
    )
    new_presentation_id = new_presentation["presentation_id"]
    new_presentation_url = new_presentation["presentation_url"]
    # Extract all text run elements
    index = index_presentation_texts(slides_service, new_presentation_id, logger)
    # Translating text to new language
    translations, total_usages = translate_texts_with_genai(
        genai_service, target_language, slides_context, list(index.keys()), logger
    )
    # Execute batch update to replace all text
    total_changes = replace_text_in_presentation(
        slides_service, new_presentation_id, translations, index, logger
    )
    # Report new presentation URL and statistics
    report = {
        "new_presentation_url": new_presentation_url,
        "total_changes": total_changes,
        "total_model_usages": total_usages,
        "total_original_texts": len(index),
        "total_translation_texts": len(translations),
    }
    logger.info(
        f"Slides Translation finished. New presentation available at '{new_presentation_url}'"
    )
    return report
