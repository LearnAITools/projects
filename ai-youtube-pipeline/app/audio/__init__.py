"""Audio generation package for Phase 4."""

from app.audio.narration_generator import NarrationGenerator
from app.audio.voice_provider import LocalPlaceholderVoiceProvider, VoiceProvider

__all__ = ["NarrationGenerator", "VoiceProvider", "LocalPlaceholderVoiceProvider"]
