"""
Neural Read Aloud (TTS) Engine for PyAcrobat
Integrates Microsoft edge-tts with offline Windows SAPI5 fallback,
providing natural speech synthesis and responsive playback controls.
"""

import os
import sys
import tempfile
import asyncio
import subprocess
import ctypes
from typing import Optional, List, Dict, Tuple
from PySide6.QtCore import QObject, Signal, QThread, QTimer

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

# Popular high-quality neural voices
SUPPORTED_VOICES = [
    ("en-US-AriaNeural", "English (US) - Aria (Female)"),
    ("en-US-GuyNeural", "English (US) - Guy (Male)"),
    ("en-US-JennyNeural", "English (US) - Jenny (Female)"),
    ("en-GB-SoniaNeural", "English (UK) - Sonia (Female)"),
    ("en-GB-RyanNeural", "English (UK) - Ryan (Male)"),
    ("es-ES-ElviraNeural", "Spanish - Elvira (Female)"),
    ("fr-FR-DeniseNeural", "French - Denise (Female)"),
    ("de-DE-KatjaNeural", "German - Katja (Female)"),
]


def get_short_path(long_path: str) -> str:
    """Converts a Windows path to 8.3 short format for 100% reliable MCI command parsing."""
    try:
        buf = ctypes.create_unicode_buffer(512)
        ret = ctypes.windll.kernel32.GetShortPathNameW(long_path, buf, 512)
        if ret > 0 and buf.value:
            return buf.value
    except Exception:
        pass
    return long_path


class MCIPlayer:
    """Low-overhead, zero-dependency Windows audio player using winmm.dll."""

    def __init__(self, alias: str = "pyacrobat_tts_player"):
        self.alias = alias
        self.winmm = ctypes.windll.winmm
        self.is_loaded = False
        self._current_file: Optional[str] = None

    def _send(self, cmd: str) -> Tuple[int, str]:
        buf = ctypes.create_unicode_buffer(256)
        ret = self.winmm.mciSendStringW(cmd, buf, 256, 0)
        return ret, buf.value

    def load(self, file_path: str) -> bool:
        self.stop()
        self.close()
        short_p = get_short_path(os.path.abspath(file_path))
        # Open mpegvideo for mp3 / waveaudio for wav
        file_type = "waveaudio" if file_path.lower().endswith(".wav") else "mpegvideo"
        ret, _ = self._send(f"open {short_p} type {file_type} alias {self.alias}")
        self.is_loaded = (ret == 0)
        self._current_file = file_path
        return self.is_loaded

    def play(self) -> bool:
        if not self.is_loaded:
            return False
        ret, _ = self._send(f"play {self.alias}")
        return ret == 0

    def pause(self) -> bool:
        if not self.is_loaded:
            return False
        ret, _ = self._send(f"pause {self.alias}")
        return ret == 0

    def resume(self) -> bool:
        if not self.is_loaded:
            return False
        ret, _ = self._send(f"resume {self.alias}")
        return ret == 0

    def stop(self) -> bool:
        if not self.is_loaded:
            return False
        ret, _ = self._send(f"stop {self.alias}")
        self._send(f"seek {self.alias} to start")
        return ret == 0

    def close(self):
        self._send(f"close {self.alias}")
        self.is_loaded = False

    def get_status(self) -> str:
        """Returns 'playing', 'paused', 'stopped', or 'unknown'."""
        if not self.is_loaded:
            return "stopped"
        _, status = self._send(f"status {self.alias} mode")
        return status.lower() or "stopped"

    def get_duration_ms(self) -> int:
        if not self.is_loaded:
            return 0
        _, val = self._send(f"status {self.alias} length")
        try:
            return int(val)
        except ValueError:
            return 0

    def get_position_ms(self) -> int:
        if not self.is_loaded:
            return 0
        _, val = self._send(f"status {self.alias} position")
        try:
            return int(val)
        except ValueError:
            return 0


class TTSSynthesisWorker(QThread):
    """Background worker for neural voice synthesis to avoid freezing GUI."""
    synthesis_done = Signal(str, int)  # file_path, page_number
    error = Signal(str)

    def __init__(self, text: str, page_number: int, voice: str = "en-US-AriaNeural", speed: float = 1.0):
        super().__init__()
        self.text = text
        self.page_number = page_number
        self.voice = voice
        self.speed = speed

    def run(self):
        try:
            temp_dir = tempfile.gettempdir()
            out_file = os.path.join(temp_dir, f"pyacrobat_speech_p{self.page_number}.mp3")

            # Calculate rate string
            rate_int = int(round((self.speed - 1.0) * 100))
            rate_str = f"{'+' if rate_int >= 0 else ''}{rate_int}%"

            success = False
            # 1. Try edge-tts neural voice
            if HAS_EDGE_TTS:
                try:
                    async def _synthesize():
                        communicate = edge_tts.Communicate(self.text, self.voice, rate=rate_str)
                        await communicate.save(out_file)

                    asyncio.run(_synthesize())
                    if os.path.exists(out_file) and os.path.getsize(out_file) > 100:
                        success = True
                except Exception as ex:
                    print(f"[TTS] edge-tts online synthesis failed, falling back to SAPI5: {ex}")

            # 2. Offline Fallback: Windows SAPI5 PowerShell Synthesis
            if not success:
                wav_file = os.path.join(temp_dir, f"pyacrobat_speech_p{self.page_number}.wav")
                ps_script = f"""
                Add-Type -AssemblyName System.Speech;
                $s = New-Object System.Speech.Synthesis.SpeechSynthesizer;
                $s.Rate = [Math]::Max(-10, [Math]::Min(10, [int](({self.speed} - 1.0) * 10)));
                $s.SetOutputToWaveFile('{wav_file}');
                $s.Speak('{self.text.replace("'", "''")}');
                $s.Dispose();
                """
                res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
                if os.path.exists(wav_file) and os.path.getsize(wav_file) > 100:
                    out_file = wav_file
                    success = True

            if success:
                self.synthesis_done.emit(out_file, self.page_number)
            else:
                self.error.emit("Failed to synthesize speech audio.")

        except Exception as e:
            self.error.emit(str(e))


class TTSController(QObject):
    """
    Main controller coordinating audio synthesis, playback state, and timers.
    """
    state_changed = Signal(str)          # 'idle', 'generating', 'playing', 'paused', 'finished'
    progress_updated = Signal(int, int)  # current_ms, total_ms
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = MCIPlayer()
        self.worker: Optional[TTSSynthesisWorker] = None
        self.current_page: int = 1
        self.is_paused: bool = False

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(250)
        self.poll_timer.timeout.connect(self._check_playback_status)

    def read_text(self, text: str, page_number: int, voice: str = "en-US-AriaNeural", speed: float = 1.0):
        """Initiates synthesis and playback for given page text."""
        clean_text = text.strip()
        if not clean_text:
            self.error_occurred.emit("Page contains no readable text.")
            return

        # Stop existing playback
        self.stop()
        self.current_page = page_number
        self.state_changed.emit("generating")

        self.worker = TTSSynthesisWorker(clean_text, page_number, voice, speed)
        self.worker.synthesis_done.connect(self._on_synthesis_ready)
        self.worker.error.connect(self._on_synthesis_error)
        self.worker.start()

    def _on_synthesis_ready(self, file_path: str, page_number: int):
        if self.player.load(file_path):
            self.player.play()
            self.is_paused = False
            self.state_changed.emit("playing")
            self.poll_timer.start()
        else:
            self.error_occurred.emit("Failed to initialize audio output.")
            self.state_changed.emit("idle")

    def _on_synthesis_error(self, err_msg: str):
        self.error_occurred.emit(err_msg)
        self.state_changed.emit("idle")

    def toggle_play_pause(self):
        """Toggles between play and pause."""
        status = self.player.get_status()
        if status == "playing":
            self.player.pause()
            self.is_paused = True
            self.state_changed.emit("paused")
        elif status == "paused" or self.is_paused:
            self.player.resume()
            self.is_paused = False
            self.state_changed.emit("playing")

    def stop(self):
        """Stops audio and resets to idle."""
        self.poll_timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(500)
        self.player.stop()
        self.is_paused = False
        self.state_changed.emit("stopped")

    def _check_playback_status(self):
        status = self.player.get_status()
        if status == "playing":
            pos = self.player.get_position_ms()
            dur = self.player.get_duration_ms()
            self.progress_updated.emit(pos, dur)
            if dur > 0 and pos >= dur:
                self.stop()
                self.state_changed.emit("finished")
        elif status == "stopped" and not self.is_paused:
            self.poll_timer.stop()
            self.state_changed.emit("finished")

    def cleanup(self):
        self.stop()
        self.player.close()
