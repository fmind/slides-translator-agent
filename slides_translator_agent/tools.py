"""Tools for the agents."""

# %% IMPORTS

import json
import logging
from typing import Any

from google.adk.tools import ToolContext
from google.auth.transport.requests import Request
from google.genai import Client
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
            tool_context.state.pop(configs.TOKEN_CACHE_KEY, None)  # type: ignore
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
    genai_client = Client(
        project=configs.PROJECT_ID, location=configs.PROJECT_LOCATION, vertexai=True
    )
    logger.info("Google API services initialized")
    return drive_service, slides_service, genai_client


# def extract_presentation_texts(slides_service, presentation_id: str) -> tuple[dict, list, set]:
#     """Extract all text run elements from a presentation."""
#     logger.info(f"Extracting text from presentation: '{presentation_id}'")
#     presentation = (
#         slides_service.presentations().get(presentationId=presentation_id).execute()
#     )
#     slides = presentation.get("slides", [])
#     logger.debug(f"Found {len(slides)} slides in '{presentation_id}'")

#     texts_to_locations = {}
#     for slide in slides:
#         slide_id = slide["objectId"]
#         for element in slide.get("pageElements", []):
#             if "shape" in element and "text" in element["shape"]:
#                 for text_element in element["shape"].get("textElements", []):
#                     if "textRun" in text_element:
#                         content = text_element["textRun"]["content"].strip()
#                         # Filter out empty strings and text without letters
#                         if content and re.search("[a-zA-Z]", content):
#                             if content not in texts_to_locations:
#                                 texts_to_locations[content] = set()
#                             texts_to_locations[content].add(slide_id)

#     unique_texts = list(texts_to_locations.keys())
#     slides_ids = {
#         slide_id
#         for locations in texts_to_locations.values()
#         for slide_id in locations
#     }
#     logger.info(
#         f"Found {len(unique_texts)} unique texts across {len(slides_ids)} slides in '{presentation_id}'"
#     )
#     logger.debug(f"Unique texts for '{presentation_id}': {unique_texts}")
#     return texts_to_locations, unique_texts, slides


# def translate_texts(
#     client,
#     presentation_id: str,
#     texts: list[str],
#     target_language: str,
#     extra_context: str | None,
#     model_name: str,
#     max_workers: int,
# ) -> tuple[dict, list]:
#     """Translate a list of texts"""
#     logger.info(
#         f"[{presentation_id}] Translating {len(texts)} texts to '{target_language}' using '{model_name}'"
#     )
#     instructions = (
#         f"Translate the following text to {target_language} as accurately as possible. "
#         "Do not add any preamble, intro, or explanation; return only the translated text. "
#     )
#     if extra_context:
#         instructions += (
#             f"You are provide with this context to perform the task: '{extra_context}'"
#         )
#     logger.debug(f"[{presentation_id}] Translation instructions: '{instructions}'")

#     usages = []
#     translations = {}

#     def translate_text(text):
#         """Translate a single text string"""
#         logger.debug(f"[{presentation_id}] Translating text: '{text}'")
#         try:
#             response = client.generate_content(
#                 model=model_name,
#                 contents=text,
#                 generation_config=GenerationConfig(
#                     temperature=0.0,
#                 ),
#                 request_options={"system_instruction": instructions},
#             )
#             translation = response.text.strip()
#             usage = response.usage_metadata
#             logger.debug(
#                 f"[{presentation_id}] Successfully translated '{text}' to '{translation}'"
#             )
#             return text, translation, usage
#         except Exception as error:
#             logger.error(f"[{presentation_id}] Translation error for '{text}': {error}")
#             return text, None, None

#     with ThreadPoolExecutor(max_workers=max_workers) as executor:
#         futures = [executor.submit(translate_text, text) for text in texts]
#         for i, future in enumerate(as_completed(futures)):
#             text, translation, usage = future.result()
#             if usage:
#                 usages.append(usage)
#             if translation:
#                 translations[text] = translation
#             logger.info(
#                 f"[{presentation_id}] Translated ({i+1}/{len(futures)}): '{text}' -> '{translation}'"
#             )

#     logger.info(
#         f"[{presentation_id}] Finished translating {len(translations)} out of {len(texts)} texts"
#     )
#     return translations, usages


# def batch_update_presentation(
#     slides_service,
#     presentation_id: str,
#     translations: dict,
#     texts_to_locations: dict,
# ) -> int:
#     """Prepare and execute batch update requests to replace all text."""
#     logger.info(
#         f"Updating presentation '{presentation_id}' with {len(translations)} translations"
#     )
#     sorted_translations = sorted(
#         translations.items(), key=lambda item: len(item[0]), reverse=True
#     )

#     requests = []
#     for text, translation in sorted_translations:
#         if translation.strip():
#             page_ids = texts_to_locations.get(text)
#             if page_ids:
#                 request = {
#                     "replaceAllText": {
#                         "replaceText": translation,
#                         "pageObjectIds": list(page_ids),
#                         "containsText": {"text": text, "matchCase": True},
#                     }
#                 }
#                 requests.append(request)
#                 logger.debug(
#                     f"[{presentation_id}] Request created for text '{text}': {request}"
#                 )

#     logger.info(f"Created {len(requests)} change requests for '{presentation_id}'")

#     batch_size = 50
#     total_changes = 0
#     for i, start in enumerate(range(0, len(requests), batch_size)):
#         stop = start + batch_size
#         batch = requests[start:stop]
#         body = {"requests": batch}
#         logger.info(
#             f"Updating batch {i+1}/{len(requests)//batch_size+1} for '{presentation_id}': {len(batch)} requests"
#         )
#         response = (
#             slides_service.presentations()
#             .batchUpdate(presentationId=presentation_id, body=body)
#             .execute()
#         )
#         changes = sum(
#             reply.get("replaceAllText", {}).get("occurrencesChanged", 0)
#             for reply in response.get("replies", [])
#         )
#         logger.debug(f"Batch update response for '{presentation_id}': {response}")
#         logger.info(f"[{presentation_id}] Applied {changes} changes in batch {i+1}")
#         total_changes += changes

#     logger.info(
#         f"Finished updating '{presentation_id}'. Total changes: {total_changes}"
#     )
#     return total_changes


# def report_usage(usages: list, model_name: str, presentation_id: str) -> dict:
#     """Report token usage and total cost."""
#     logger.info(
#         f"[{presentation_id}] Calculating usage for {len(usages)} API calls with model '{model_name}'"
#     )
#     prices = {
#         "gemini-2.5-pro": {"input": 1.25 / 1_000_000, "output": 10.00 / 1_000_000},
#         "gemini-2.5-flash": {"input": 0.30 / 1_000_000, "output": 2.50 / 1_000_000},
#         "gemini-2.5-flash-lite": {"input": 0.1 / 1_000_000, "output": 0.4 / 1_000_000},
#     }

#     total_input_tokens = 0
#     total_output_tokens = 0
#     price_table = prices.get(model_name, {"input": 0, "output": 0})
#     logger.debug(
#         f"[{presentation_id}] Using price table for '{model_name}': {price_table}"
#     )
#     price_input_tokens = price_table["input"]
#     price_output_tokens = price_table["output"]

#     for usage in usages:
#         total_input_tokens += usage.prompt_token_count
#         total_output_tokens += usage.candidates_token_count

#     input_cost = total_input_tokens * price_input_tokens
#     output_cost = total_output_tokens * price_output_tokens
#     total_cost = input_cost + output_cost

#     report = {
#         "total_input_tokens": total_input_tokens,
#         "total_output_tokens": total_output_tokens,
#         "total_cost_usd": total_cost,
#     }
#     logger.info(f"[{presentation_id}] Usage report: {report}")
#     return report


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
    # %% Logger initialization
    logger = setup_logger(presentation_id, tool_context)
    logger.info(
        f"Translating presentation '{presentation_id}' to '{target_language}' for '{slides_context}'"
    )
    # %% Negociate auth credentials
    auth_result = negotiate_creds(tool_context, logger=logger)
    if isinstance(auth_result, dict):  # new auth request
        return auth_result
    creds = auth_result
    # %% Initialize Google API services
    drive_service, slides_service, genai_client = initialize_services(creds, logger)
    # %% Copy the original presentation
    new_presentation = copy_presentation(
        drive_service, slides_service, presentation_id, target_language, logger
    )
    # new_presentation_id = new_presentation["presentation_id"]
    new_presentation_url = new_presentation["presentation_url"]
    # %% Extract all text run elements
    # logger.info(f"Extracting text from new presentation '{new_presentation_id}'")
    # # texts_to_locations, unique_texts, slides = extract_presentation_texts(
    # #     slides_service, copied_presentation_id
    # # )
    # logger.info(f"Found {len(unique_texts)} unique text runs")
    # %% Translating text to new language using Vertex AI
    # logger.info(f"Translating {len(unique_texts)} text runs to '{target_language}'")
    # # translations, usages = translate_texts(
    # #     client,
    # #     copied_presentation_id,
    # #     unique_texts,
    # #     target_language,
    # #     extra_context,
    # #     model_name,
    # #     max_workers,
    # # )
    # logger.info(f"Successfully translated {len(translations)} text runs")
    # %% Execute the batch update to replace all text
    # logger.info(f"Updating presentation '{new_presentation_id}' with translated text")
    # # total_changes = batch_update_presentation(
    # #     slides_service, copied_presentation_id, translations, texts_to_locations
    # # )
    # logger.info(f"Applied {total_changes} text changes to the presentation")
    # %% Report token usage and total cost
    # logger.info("Generating usage report")
    # # usage_report = report_usage(usages, model_name, copied_presentation_id)
    # logger.info(f"Usage report generated: {usage_report}")
    report = {
        "new_presentation_url": new_presentation_url,
        # "slides_count": len(slides),
        # "unique_text_runs_found": len(unique_texts),
        # "text_runs_translated": len(translations),
        # "text_occurrences_changed": total_changes,
        # "estimated_words_translated": sum(
        #     len(t.split()) for t in translations.values()
        # ),
        # **usage_report,
    }
    logger.info(
        f"Slides Translation finished. New presentation available at '{new_presentation_url}'"
    )
    return report
