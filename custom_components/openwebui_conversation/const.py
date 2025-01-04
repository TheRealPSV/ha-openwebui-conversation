"""Constants for openwebui_conversation."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "OpenWebUI Conversation"
DOMAIN = "openwebui_conversation"

DO_SEARCH_INTENT = "DoSearch"

MENU_OPTIONS = ["general_config", "model_config", "search_config"]

CONF_SERVICE_NAME = "service_name"
CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_TIMEOUT = "timeout"
CONF_MODEL = "chat_model"
CONF_LANGUAGE_CODE = "lang_code"
CONF_SEARCH_ENABLED = "search_enabled"
CONF_SEARCH_SENTENCES = "search_sentences"
CONF_SEARCH_RESULT_PREFIX = "search_result_prefix"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_SERVICE_NAME = "OpenWebUI"
DEFAULT_BASE_URL = "http://openwebui.homeassistant.local"
DEFAULT_TIMEOUT = 60
DEFAULT_MODEL = "llama2:latest"
DEFAULT_LANGUAGE_CODE = "en"
DEFAULT_SEARCH_ENABLED = False
DEFAULT_SEARCH_SENTENCES = """look up {query}
search [the web | the internet] for {query}"""
DEFAULT_SEARCH_RESULT_PREFIX = "Based on a search of the internet: "
DEFAULT_VERIFY_SSL = True
