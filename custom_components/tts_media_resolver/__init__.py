"""The TTS Media Resolver integration.

Exposes a single service, ``tts_media_resolver.resolve_media``, that turns a
``media-source://`` reference (such as the identifier a ``tts.speak`` call
produces) into a real, absolute, directly-playable URL.

This uses Home Assistant's own media-source resolution machinery
(``homeassistant.components.media_source``) plus its own helper for turning
a resolved media-source URL into an absolute, correctly-signed playable URL
(``homeassistant.components.media_player.async_process_play_media_url``) —
no external credentials, tokens, or secrets are stored or required.
"""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components import media_source
from homeassistant.components.media_player import async_process_play_media_url
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

DOMAIN = "tts_media_resolver"
SERVICE_RESOLVE_MEDIA = "resolve_media"

_LOGGER = logging.getLogger(__name__)

SERVICE_RESOLVE_MEDIA_SCHEMA = vol.Schema(
    {
        vol.Required("media_content_id"): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the tts_media_resolver component and register its service."""

    async def async_resolve_media(call: ServiceCall) -> dict:
        media_content_id = call.data["media_content_id"]

        resolved = await media_source.async_resolve_media(hass, media_content_id, None)

        # media_source.async_resolve_media() does NOT sign protected paths
        # (e.g. local media under /media/...) on its own -- that is a
        # separate step every built-in media_player integration performs
        # before handing a URL to an external player. Without it, local
        # media-source URLs come back unsigned and any external fetcher
        # (e.g. Music Assistant) gets a 401 Unauthorized. TTS proxy URLs
        # are self-authenticating and pass through unchanged either way.
        url = async_process_play_media_url(hass, resolved.url)

        _LOGGER.debug(
            "Resolved %s to %s (mime_type=%s)", media_content_id, url, resolved.mime_type
        )

        return {"url": url, "mime_type": resolved.mime_type}

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESOLVE_MEDIA,
        async_resolve_media,
        schema=SERVICE_RESOLVE_MEDIA_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    return True
