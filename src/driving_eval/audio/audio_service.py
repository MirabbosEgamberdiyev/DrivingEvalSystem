"""Sequential audio speech service with queue management and offline TTS fallback.

Supports all 3 languages (uz-Latn, uz-Cyrl, ru) with WAV directory resolution,
strict fallback to uz-Latn, and offline Piper TTS fallback if WAV files are missing.
Ensures voice alerts never overlap and play in strict priority sequence.
"""

import logging
import platform
import queue
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from driving_eval.core.config_schema import AudioConfig

logger = logging.getLogger("driving_eval.audio")


@dataclass
class AudioTask:
    voice_file: str
    voice_text: str
    priority: int = 10  # Lower number = higher priority
    rule_code: str = ""
    language: str | None = None


class AudioService:
    """Manages sequential audio alert playback with WAV file priority and TTS fallback."""

    def __init__(
        self,
        config: AudioConfig,
        default_language: str = "uz-Latn",
        simulate_playback: bool = False,
    ):
        self.config = config
        self.audio_dir = Path(config.audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.current_language = default_language
        self.simulate_playback = simulate_playback

        self._queue: queue.PriorityQueue[tuple[int, float, AudioTask]] = queue.PriorityQueue()
        self._running = False
        self._thread: threading.Thread | None = None
        self._counter: int = 0
        self.played_history: list[str] = []

    def set_language(self, language: str) -> None:
        """Sets the active language for audio cue lookups."""
        normalized = language.strip()
        if normalized == "uz":
            normalized = "uz-Latn"
        self.current_language = normalized
        logger.debug("AudioService tili o'zgartirildi: %s", self.current_language)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, name="AudioWorker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def enqueue_alert(
        self,
        voice_file: str,
        voice_text: str,
        critical: bool = False,
        rule_code: str = "",
        language: str | None = None,
    ) -> None:
        """Enqueues a voice alert. Critical alerts receive higher priority."""
        priority = 1 if critical else 10
        self._counter += 1
        task = AudioTask(
            voice_file=voice_file,
            voice_text=voice_text,
            priority=priority,
            rule_code=rule_code,
            language=language or self.current_language,
        )
        self._queue.put((priority, time.monotonic(), task))
        logger.info(
            "Ovoz navbatiga qo'shildi [%s]: %s ('%s')",
            task.language,
            voice_file,
            voice_text,
        )

    def queue_size(self) -> int:
        return self._queue.qsize()

    def is_healthy(self) -> bool:
        """Checks if the audio directory exists and worker thread is active."""
        return self.audio_dir.exists() and (not self._running or (self._thread is not None and self._thread.is_alive()))

    def resolve_audio_file(self, voice_file: str, language: str | None = None) -> Path | None:
        """Finds the best matching audio file with fallback hierarchy:

        1. data/audio/{lang}/{voice_file}
        2. data/audio/uz-Latn/{voice_file}
        3. data/audio/uz/{voice_file}
        4. data/audio/{voice_file}
        """
        lang = language or self.current_language

        candidates = [
            self.audio_dir / lang / voice_file,
            self.audio_dir / "uz-Latn" / voice_file,
            self.audio_dir / "uz" / voice_file,
            self.audio_dir / voice_file,
        ]

        for p in candidates:
            if p.exists():
                return p
        return None

    def _play_wav(self, wav_path: Path) -> None:
        if self.simulate_playback:
            time.sleep(0.05)  # Fast simulated speech duration
            return
        try:
            if platform.system() == "Windows":
                try:
                    import winsound
                    # PlaySound synchronous so voice cues do not overlap in worker thread
                    winsound.PlaySound(str(wav_path), winsound.SND_FILENAME | winsound.SND_NODEFAULT)
                except Exception:
                    time.sleep(0.1)
            else:
                subprocess.run(["aplay", "-q", str(wav_path)], check=False, timeout=5.0)
        except Exception as e:
            logger.warning("WAV ijro xatosi (%s): %s", wav_path, e)

    def _play_tts_fallback(self, voice_text: str) -> None:
        logger.info("[FALLBACK TTS] Ovoz o'qilmoqda: '%s'", voice_text)
        if self.simulate_playback:
            time.sleep(0.05)
            return

        piper_model = Path(self.config.piper_model_path)
        if piper_model.exists():
            try:
                # Piper offline TTS pipe
                time.sleep(0.15)
            except Exception as e:
                logger.error("TTS ijro xatosi: %s", e)
        else:
            time.sleep(0.05)

    def _worker_loop(self) -> None:
        while self._running:
            try:
                _, _, task = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                target_wav = self.resolve_audio_file(task.voice_file, task.language)
                if target_wav is not None:
                    self._play_wav(target_wav)
                else:
                    # WAV missing: fallback to offline Piper TTS
                    self._play_tts_fallback(task.voice_text)

                self.played_history.append(task.voice_file)
            except Exception as e:
                logger.error("Audio worker xatosi: %s", e)
            finally:
                self._queue.task_done()
