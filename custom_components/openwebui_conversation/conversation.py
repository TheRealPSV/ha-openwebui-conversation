"""OpenWebUI conversation agent."""

from __future__ import annotations

from typing import Literal

from hassil import recognize
from hassil.intents import Intents

from homeassistant.components import conversation
from homeassistant.components.conversation import async_get_chat_log
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    HomeAssistantError,
)
from homeassistant.helpers import intent
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import ulid

from markdown_it import MarkdownIt
from mdit_plain.renderer import RendererPlain

from .api import OpenWebUIApiClient
from .const import (
    LOGGER,
    DO_SEARCH_INTENT,
    CONF_BASE_URL,
    CONF_API_KEY,
    CONF_TIMEOUT,
    CONF_MODEL,
    CONF_LANGUAGE_CODE,
    CONF_SEARCH_ENABLED,
    CONF_SEARCH_SENTENCES,
    CONF_SEARCH_RESULT_PREFIX,
    CONF_STRIP_MARKDOWN,
    CONF_VERIFY_SSL,
    DEFAULT_TIMEOUT,
    DEFAULT_MODEL,
    DEFAULT_LANGUAGE_CODE,
    DEFAULT_SEARCH_ENABLED,
    DEFAULT_SEARCH_SENTENCES,
    DEFAULT_SEARCH_RESULT_PREFIX,
    DEFAULT_STRIP_MARKDOWN,
    DEFAULT_VERIFY_SSL,
)
from .exceptions import ApiCommError, ApiJsonError, ApiTimeoutError
from .message import Message


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
    """Set up OpenWebUI Conversation Agent from a config entry."""
    agent = OpenWebUIAgent(hass, entry)
    async_add_entities([agent])
    return True


class OpenWebUIAgent(conversation.ConversationEntity):
    """OpenWebUI conversation agent."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.timeout = entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        self.client = OpenWebUIApiClient(
            base_url=entry.data[CONF_BASE_URL],
            api_key=entry.data[CONF_API_KEY],
            timeout=entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
            session=async_get_clientsession(hass),
            verify_ssl=entry.options.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        )
        self.history: dict[str, list[Message]] = {}
        self.search_enabled = entry.options.get(
            CONF_SEARCH_ENABLED, DEFAULT_SEARCH_ENABLED
        )
        self.search_sentences = [
            x
            for x in entry.options.get(
                CONF_SEARCH_SENTENCES, DEFAULT_SEARCH_SENTENCES
            ).splitlines()
            if x.strip()
        ]
        self.search_result_prefix = entry.options.get(
            CONF_SEARCH_RESULT_PREFIX, DEFAULT_SEARCH_RESULT_PREFIX
        )
        self.lang = entry.options.get(CONF_LANGUAGE_CODE, DEFAULT_LANGUAGE_CODE).strip()
        self._attr_name = entry.title
        self._attr_unique_id = entry.entry_id
        self.strip_markdown = entry.options.get(
            CONF_STRIP_MARKDOWN, DEFAULT_STRIP_MARKDOWN
        )
        self.markdown_parser = MarkdownIt(renderer_cls=RendererPlain)

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self.entry.async_on_unload(
            self.entry.add_update_listener(self._async_entry_update_listener)
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        await super().async_will_remove_from_hass()

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""

        LOGGER.error("=== OPENWEBUI AGENT async_process called ===")
        LOGGER.error("  input conversation_id=%s", user_input.conversation_id)
        LOGGER.error("  input text=%r", user_input.text)
        LOGGER.error("  search_enabled=%s, search_sentences_count=%d", self.search_enabled, len(self.search_sentences))

        user_message = Message("user", user_input.text)
        prompt = user_message.message

        should_search = False

        if self.search_enabled and len(self.search_sentences):
            i = Intents.from_dict(
                {
                    "language": self.lang,
                    "settings": {"ignore_whitespace": True},
                    "intents": {
                        DO_SEARCH_INTENT: {
                            "data": [{"sentences": self.search_sentences}]
                        }
                    },
                    "lists": {"query": {"wildcard": True}},
                }
            )
            r = recognize(prompt, i)
            if r is not None:
                if (
                    r.intent.name == DO_SEARCH_INTENT
                    and r.entities.get("query", None) is not None
                ):
                    prompt = r.entities["query"].value
                    should_search = True

        LOGGER.error("After search logic: should_search=%s, effective prompt=%r", should_search, prompt)

        conversation_result = None
        conversation_id = user_input.conversation_id or ulid.ulid()
        conversation_history: list[Message] = []

        LOGGER.error("About to get chat_log for conversation_id=%s", conversation_id)

        with async_get_chat_log(self.hass, user_input) as chat_log:
            LOGGER.error("Entered chat_log context, chat_log type=%s, has conversation_id attr=%s, has content=%s", type(chat_log), hasattr(chat_log, 'conversation_id'), hasattr(chat_log, 'content'))

            conversation_id = chat_log.conversation_id or user_input.conversation_id or ulid.ulid()

            # Build previous conversation history as list[Message] from HA's managed chat_log.
            # This ensures proper retention for ConversationEntity threads (e.g. Assistant UI).
            for content in chat_log.content:
                if hasattr(content, "role") and hasattr(content, "content") and content.role in ("user", "assistant"):
                    conversation_history.append(Message(content.role, content.content))

            # chat_log.content usually ends with the current user message (added by the pipeline).
            # We will append the (possibly search-rewritten) current user prompt inside query(),
            # so drop the last user entry to avoid sending duplicate current user turn.
            if conversation_history and conversation_history[-1].role == "user":
                conversation_history.pop()

            LOGGER.error(
                "Chat history for conv_id=%s: built %d previous messages from chat_log (raw content items: %d)",
                conversation_id,
                len(conversation_history),
                len(chat_log.content),
            )

            # Also log the self.history size for comparison (legacy)
            LOGGER.error(
                "Legacy self.history size for this conv_id: %d",
                len(self.history.get(conversation_id, [])),
            )

            # If chat_log didn't provide previous turns (as seen in logs where built=0 even on follow-up),
            # fall back to our legacy self.history which is accumulating the turns.
            if len(conversation_history) == 0 and conversation_id in self.history:
                conversation_history = list(self.history[conversation_id])
                LOGGER.error(
                    "Falling back to legacy self.history for history (now %d previous turns)",
                    len(conversation_history),
                )

            try:
                response = await self.query(
                    prompt, conversation_history, should_search
                )
            except (ApiCommError, ApiJsonError, ApiTimeoutError) as err:
                LOGGER.error("Error generating prompt: %s (cause: %s)", err, err.__cause__)
                intent_response = intent.IntentResponse(language=user_input.language)
                intent_response.async_set_error(
                    intent.IntentResponseErrorCode.UNKNOWN,
                    f"Something went wrong, {err}",
                )
                conversation_result = conversation.ConversationResult(
                    response=intent_response, conversation_id=conversation_id
                )
            except HomeAssistantError as err:
                LOGGER.error("Something went wrong: %s", err)
                intent_response = intent.IntentResponse(language=user_input.language)
                intent_response.async_set_error(
                    intent.IntentResponseErrorCode.UNKNOWN,
                    "Something went wrong, please check the logs for more information.",
                )
                conversation_result = conversation.ConversationResult(
                    response=intent_response, conversation_id=conversation_id
                )
            else:
                response_data = response["choices"][0]["message"]["content"]
                if self.strip_markdown:
                    response_data = self.markdown_parser.render(response_data)
                if should_search:
                    response_data = f"{self.search_result_prefix} {response_data}"
                response_message = Message("assistant", response_data)

                conversation_history.append(user_message)
                conversation_history.append(response_message)
                self.history[conversation_id] = conversation_history

                # Sync the turn back to HA's chat_log so the thread state is correct for future calls
                # and the Assistant UI.
                try:
                    from homeassistant.components.conversation.chat_log import AssistantContent
                    chat_log.async_add_assistant_content(
                        AssistantContent(
                            agent_id=self.entity_id,
                            content=response_data,
                        )
                    )
                except Exception as err:
                    LOGGER.error("Failed to add assistant turn to chat_log (history may not persist): %s", err)
                    # Still continue; self.history is updated for this instance's lifetime.

                intent_response = intent.IntentResponse(language=user_input.language)
                intent_response.async_set_speech(response_data)
                conversation_result = conversation.ConversationResult(
                    response=intent_response, conversation_id=conversation_id
                )

        return conversation_result

    async def query(self, prompt: str, history: list[Message], search: bool) -> any:
        """Process a sentence."""
        model = self.entry.options.get(CONF_MODEL, DEFAULT_MODEL)

        message_list = [{"role": x.role, "content": x.message} for x in history]
        message_list.append({"role": "user", "content": prompt})

        LOGGER.error("Sending %d messages to OpenWebUI (prev history + current)", len(message_list))

        payload = {
            "model": model,
            "messages": message_list,
            "stream": False,
            "features": {"web_search": search},
        }

        result = await self.client.async_generate(payload)

        return result

    async def _async_entry_update_listener(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Handle options update."""
        # Reload as we update device info + entity name + supported features
        await hass.config_entries.async_reload(entry.entry_id)
