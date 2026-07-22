from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # GPU-friendly defaults for the user's WSL + Docker Desktop setup.
    whisper_model: str = "small"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"
    whisper_language: str | None = "pt"

    # Accuracy-oriented decoding defaults that remain fast on CUDA.
    whisper_beam_size: int = 5
    whisper_patience: float = 1.0
    whisper_temperature: float = 0.0
    whisper_repetition_penalty: float = 1.05
    whisper_no_speech_threshold: float = 0.55
    whisper_initial_prompt: str | None = (
        "Transcrição em português do Brasil. Preserve termos técnicos, nomes próprios, "
        "siglas, gírias e palavras coloquiais exatamente como foram pronunciadas."
    )
    whisper_hotwords: str | None = None
    whisper_hotwords_file: Path | None = Path("/config/whisper-hotwords.txt")

    # A slightly larger window gives the small model more phonetic context.
    whisper_window_seconds: float = 3.2
    whisper_overlap_seconds: float = 0.8
    whisper_min_audio_seconds: float = 0.8
    whisper_vad_min_silence_ms: int = 350

    # Removes duplicate microphone transcripts caused by loudspeaker bleed.
    # This is transcript-level suppression, not native acoustic echo cancellation.
    echo_suppression_enabled: bool = True
    echo_suppression_window_seconds: float = 5.0
    echo_suppression_similarity: float = 0.82
    echo_suppression_min_chars: int = 5
    echo_suppression_mic_delay_ms: int = 450

    # Retenção das métricas de latência em memória (SF-016).
    metrics_max_samples_per_channel: int = 512
    metrics_max_channels: int = 64

    # Consolidação de texto por canal em memória (SF-017).
    transcript_max_segments_per_channel: int = 256
    transcript_max_channels: int = 64
    transcript_overlap_tail_words: int = 12

    # Janela adaptativa por métricas de latência (SF-022). Desabilitada por padrão —
    # com a flag desligada o comportamento é idêntico ao whisper_window_seconds estático.
    adaptive_window_enabled: bool = False
    adaptive_window_min_seconds: float = 1.6
    adaptive_window_latency_high_ms: int = 1600
    adaptive_window_latency_low_ms: int = 600
    adaptive_window_step_seconds: float = 0.4
    adaptive_window_stable_evaluations: int = 3
    adaptive_window_min_samples: int = 5

    model_cache_dir: Path = Path("/models")
    sample_rate: int = 16_000
    log_level: str = "INFO"

    @field_validator("whisper_language", mode="before")
    @classmethod
    def normalize_whisper_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        aliases = {
            "pt-br": "pt",
            "pt_br": "pt",
            "portuguese": "pt",
            "português": "pt",
        }
        return aliases.get(normalized.lower(), normalized)

    def resolved_hotwords(self) -> str | None:
        values: list[str] = []
        if self.whisper_hotwords:
            values.append(self.whisper_hotwords.strip())
        path = self.whisper_hotwords_file
        if path is not None and path.is_file():
            entries = [
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
            if entries:
                values.append(", ".join(entries))
        combined = ", ".join(value for value in values if value)
        return combined or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
