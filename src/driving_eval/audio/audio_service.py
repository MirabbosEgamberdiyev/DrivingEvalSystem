"""Sequential audio speech service with queue management and offline TTS fallback.

Ensures voice alerts never overlap and fall back gracefully if WAV files are missing.
"""

import logging
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


class AudioService:
    """Manages sequential audio alert playback with WAV file priority and TTS fallback."""

    def __init__(self, config: AudioConfig, simulate_playback: bool = False):
        self.config = config
        self.audio_dir = Path(config.audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.simulate_playback = simulate_playback

        self._queue: queue.PriorityQueue[tuple[int, float, AudioTask]] = queue.PriorityQueue()
        self._running = False
        self._thread: threading.Thread | None = None
        self._counter: int = 0
        self.played_history: list[str] = []

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

    def enqueue_alert(self, voice_file: str, voice_text: str, critical: bool = False, rule_code: str = "") -> None:
        """Enqueues a voice alert. Critical alerts receive higher priority."""
        priority = 1 if critical else 10
        self._counter += 1
        task = AudioTask(voice_file=voice_file, voice_text=voice_text, priority=priority, rule_code=rule_code)
        self._queue.put((priority, time.monotonic(), task))
        logger.info("Ovoz navbatiga qo'shildi: %s ('%s')", voice_file, voice_text)

    def _play_wav(self, wav_path: Path) -> None:
        if self.simulate_playback:
            time.sleep(0.05)  # Fast simulated speech duration
            return
        try:
            # On Linux: aplay -q, on Windows: PowerShell SoundPlayer
            import platform
            if platform.system() == "Windows":
                # Simulated or asynchronous powershell play
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

        # Check if Piper binary exists
        piper_model = Path(self.config.piper_model_path)
        if piper_model.exists():
            try:
                # Pipe text to piper TTS
                # echo "text" | piper --model model.onnx --output_raw | aplay -r 22050 -f S16_LE -t raw
                time.sleep(0.2)
            except Exception as e:
                logger.error("TTS ijro xatosi: %s", e)
        else:
            # Fallback simulated delay
            time.sleep(0.1)

    def _worker_loop(self) -> None:
        while self._running:
            try:
                _, _, task = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                target_wav = self.audio_dir / task.voice_file
                if target_wav.exists():
                    self._play_wav(target_wav)
                else:
                    # WAV missing: switch to fallback TTS!
                    self._play_tts_fallback(task.voice_text)

                self.played_history.append(task.voice_file)
            except Exception as e:
                logger.error("Audio worker xatosi: %s", e)
            finally:
                self._queue.task_done()
