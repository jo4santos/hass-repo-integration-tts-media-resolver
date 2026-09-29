# TTS Media Resolver

A tiny helper integration with a single job: turn a `media-source://` reference
(such as the identifier a `tts.speak` call produces) into a real, absolute,
directly-playable URL — using Home Assistant's own internal media-source
resolution, with no external credentials, tokens, or secrets involved.

## Why

Some media players / announcement services (e.g. Music Assistant's
`music_assistant.play_announcement`) need an actual playable `url`, not a
`media-source://tts/...` reference. This integration bridges that gap.

## Service

### `tts_media_resolver.resolve_media`

| Field | Required | Description |
| --- | --- | --- |
| `media_content_id` | yes | The `media-source://` URI to resolve. |

Returns a service response: `{"url": "...", "mime_type": "..."}`.

## Example usage

```yaml
- action: tts.speak
  target:
    entity_id: tts.your_tts_engine
  data:
    media_player_entity_id: media_player.placeholder
    message: "Olá, isto é um teste."
  response_variable: tts_result

- action: tts_media_resolver.resolve_media
  data:
    media_content_id: "{{ tts_result.url }}"
  response_variable: resolved

- action: music_assistant.play_announcement
  target:
    entity_id: media_player.your_speaker_group
  data:
    url: "{{ resolved.url }}"
    use_pre_announce: true
```

## Installation

1. Install via HACS → ⋮ → Custom repositories, category **Integration**, using
   this repository's URL.
2. Add `tts_media_resolver:` to `configuration.yaml` (this integration has no
   config flow — it only registers a service).
3. Restart Home Assistant.
