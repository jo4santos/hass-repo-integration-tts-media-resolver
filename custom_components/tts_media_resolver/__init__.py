"""The TTS Media Resolver integration.

Exposes a single service, ``tts_media_resolver.resolve_media``, that turns a
``media-source://`` reference (such as the identifier a ``tts.speak`` call
produces, or a local media file) into a real, absolute, directly-playable
and correctly-signed URL.

This uses Home Assistant's own media-source resolution machinery
(``homeassistant.components.media_source``) plus its own path-signing
helper (``homeassistant.components.http.auth.async_sign_path``) -- no
external credentials, tokens, or secrets are stored or required.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import urlsplit, urlunsplit

import voluptuous as vol

from homeassistant.components import media_source
from homeassistant.components.http.auth import async_sign_path
from homeassistant.components.media_player import async_process_play_media_url
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

DOMAIN = "tts_media_resolver"
SERVICE_RESOLVE_MEDIA = "resolve_media"

_LOGGER = logging.getLogger(__name__)

# How long a signed media URL stays valid once handed to an external
# consumer (e.g. Music Assistant fetching it over HTTP).
SIGNED_URL_EXPIRY = timedelta(hours=2)

SERVICE_RESOLVE_MEDIA_SCHEMA = vol.Schema(
    {
        vol.Required("media_content_id"): cv.string,
    }
)


def _sign_url(hass: HomeAssistant, url: str) -> str:
    """Return `url` with a fresh signed-path token, whatever shape it has.

    Home Assistant's built-in media-source resolvers are inconsistent
    about what they hand back: the TTS proxy returns a *relative* path
    (which ``async_process_play_media_url`` happily makes absolute *and*
    signs), while the local media source already returns a full
    *absolute* URL (built as ``f"{get_url(hass)}/media/{quoted_path}"``).
    ``async_process_play_media_url`` returns an already-absolute URL
    completely unchanged -- it never signs it -- so local media came back
    unsigned and an external consumer (Music Assistant) got a 401
    Unauthorized fetching it, while TTS kept working because its proxy
    URL carries its own token and needs no HA auth signature at all.

    To cover both shapes uniformly, always re-sign the path ourselves via
    ``async_sign_path`` (which works outside an HTTP/WebSocket request
    context by falling back to Home Assistant's built-in "Home Assistant
    Content" user), then reassemble the result with the original
    scheme/host when the input was already absolute.
    """
    parsed = urlsplit(url)

    signed_path = async_sign_path(hass, parsed.path, SIGNED_URL_EXPIRY)
    signed_parts = urlsplit(signed_path)

    if parsed.scheme and parsed.netloc:
        # Already absolute (e.g. local media source) -- keep the original
        # scheme/host, swap in the freshly-signed path/query.
        return urlunsplit(
            (parsed.scheme, parsed.netloc, signed_parts.path, signed_parts.query, "")
        )

    # Relative path (e.g. the TTS proxy) -- let Home Assistant's own
    # helper turn the signed path into a full absolute URL.
    return async_process_play_media_url(hass, signed_path)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the tts_media_resolver component and register its service."""

    async def async_resolve_media(call: ServiceCall) -> dict:
        media_content_id = call.data["media_content_id"]

        resolved = await media_source.async_resolve_media(hass, media_content_id, None)
        url = _sign_url(hass, resolved.url)

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
