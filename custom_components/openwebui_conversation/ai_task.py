"""AI Task platform for OpenWebUI Conversation."""

from __future__ import annotations

import base64
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from homeassistant.components import ai_task, conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, llm
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.json import json_loads

from .const import CONF_MODEL, DEFAULT_MODEL, DOMAIN, LOGGER
from .coordinator import OpenWebUIDataUpdateCoordinator
from .exceptions import ApiCommError, ApiJsonError, ApiTimeoutError

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OpenWebUI AI Task entities from a config entry."""
    coordinator: OpenWebUIDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([OpenWebUITaskEntity(entry, coordinator)])


def _read_image_base64(path: Path) -> str:
    """Read and encode an image off the event loop."""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _schema_to_openapi(
    structure: Any,
    custom_serializer: Any,
) -> dict[str, Any]:
    """Convert an HA structure schema to OpenAPI/JSON Schema."""
    try:
        import probatio

        return probatio.to_openapi(
            structure,
            custom_serializer=custom_serializer,
            openapi_version="3.1.0",
        )
    except ImportError:
        from voluptuous_openapi import convert

        return convert(structure, custom_serializer=custom_serializer)


def _format_structured_output(
    structure: Any,
    chat_log: conversation.ChatLog,
) -> dict[str, Any]:
    """Convert a Home Assistant structure schema to OpenAI-compatible JSON schema."""
    custom_serializer = (
        chat_log.llm_api.custom_serializer
        if chat_log.llm_api
        else llm.selector_serializer
    )
    return _schema_to_openapi(structure, custom_serializer)


async def _attachment_parts(
    hass: HomeAssistant,
    attachments: list[conversation.Attachment] | None,
) -> list[dict[str, Any]]:
    """Convert image attachments to OpenAI-compatible image_url parts."""
    if not attachments:
        return []

    parts: list[dict[str, Any]] = []
    for attachment in attachments:
        mime_type = attachment.mime_type.partition(";")[0].strip().lower()
        if mime_type == "image/jpg":
            mime_type = "image/jpeg"
        if not mime_type.startswith("image/"):
            raise HomeAssistantError(
                f"OpenWebUI AI Task only supports image attachments; "
                f"received {attachment.mime_type}"
            )
        try:
            encoded = await hass.async_add_executor_job(
                _read_image_base64, attachment.path
            )
        except OSError as err:
            raise HomeAssistantError("Unable to read attachment") from err
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
            }
        )
    return parts


async def _chat_log_to_messages(
    hass: HomeAssistant,
    chat_log: conversation.ChatLog,
) -> list[dict[str, Any]]:
    """Convert a Home Assistant chat log to OpenWebUI chat messages."""
    messages: list[dict[str, Any]] = []

    for content in chat_log.content:
        if isinstance(content, conversation.SystemContent):
            if content.content:
                messages.append({"role": "system", "content": content.content})
            continue

        if isinstance(content, conversation.UserContent):
            text = content.content or ""
            image_parts = await _attachment_parts(hass, content.attachments)
            if image_parts:
                message_content: str | list[dict[str, Any]] = [
                    {"type": "text", "text": text},
                    *image_parts,
                ]
            else:
                message_content = text
            messages.append({"role": "user", "content": message_content})
            continue

        if isinstance(content, conversation.AssistantContent):
            if content.content:
                messages.append({"role": "assistant", "content": content.content})
            continue

    return messages


class OpenWebUITaskEntity(ai_task.AITaskEntity):
    """OpenWebUI AI Task entity for data generation."""

    _attr_has_entity_name = True
    _attr_name = "AI Task"
    _attr_supported_features = (
        ai_task.AITaskEntityFeature.GENERATE_DATA
        | ai_task.AITaskEntityFeature.SUPPORT_ATTACHMENTS
    )

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: OpenWebUIDataUpdateCoordinator,
    ) -> None:
        """Initialize the entity."""
        self.entry = entry
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_ai_task"
        # Tie the entity to the config entry title so multiple OpenWebUI
        # setups are distinguishable (e.g. "Kitchen OpenWebUI AI Task").
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="OpenWebUI",
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    async def _async_generate_data(
        self,
        task: ai_task.GenDataTask,
        chat_log: conversation.ChatLog,
    ) -> ai_task.GenDataTaskResult:
        """Handle a generate data task."""
        model = self.entry.options.get(CONF_MODEL, DEFAULT_MODEL)
        messages = await _chat_log_to_messages(self.hass, chat_log)

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

        if task.structure is not None:
            schema = _format_structured_output(task.structure, chat_log)
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "ai_task_data",
                    "schema": schema,
                    "strict": True,
                },
            }

        LOGGER.debug(
            "AI Task generate_data for %s with %d messages (structured=%s)",
            model,
            len(messages),
            task.structure is not None,
        )

        try:
            result = await self.coordinator.client.async_generate(payload)
        except (ApiCommError, ApiJsonError, ApiTimeoutError) as err:
            raise HomeAssistantError(f"Error talking to OpenWebUI: {err}") from err

        try:
            text = result["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as err:
            raise HomeAssistantError(
                "OpenWebUI returned an unexpected response"
            ) from err

        chat_log.async_add_assistant_content_without_tools(
            conversation.AssistantContent(
                agent_id=self.entity_id,
                content=text,
            )
        )

        if not task.structure:
            return ai_task.GenDataTaskResult(
                conversation_id=chat_log.conversation_id,
                data=text,
            )

        try:
            data = json_loads(text)
        except JSONDecodeError as err:
            LOGGER.error(
                "Failed to parse JSON response: %s. Response: %s",
                err,
                text,
            )
            raise HomeAssistantError(
                "Error with OpenWebUI structured response"
            ) from err

        return ai_task.GenDataTaskResult(
            conversation_id=chat_log.conversation_id,
            data=data,
        )
