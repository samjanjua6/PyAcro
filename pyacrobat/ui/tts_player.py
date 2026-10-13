"""
Neural Read Aloud (TTS) Viewport Mini-Player Component
Sleek, collapsible audio player bar embedded directly below PageControlsBar.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QToolButton, QComboBox, QProgressBar, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from pyacrobat.core.tts_engine import SUPPORTED_VOICES
from pyacrobat.ui.styles import ThemeManager


class TTSMiniPlayer(QFrame):
    """
    Ergonomic horizontal audio playback bar for Neural Read Aloud.
    Collapsible directly under the PageControlsBar.
    """

    play_requested = Signal(str, float)  # voice_id, speed
    pause_requested = Signal()
    stop_requested = Signal()
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ttsMiniPlayerFrame")
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.is_playing = False
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 4, 14, 4)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignVCenter)

        # 1. Title & Status
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.setAlignment(Qt.AlignVCenter)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        lbl_icon = QLabel("🔊")
        title_row.addWidget(lbl_icon)

        self.lbl_title = QLabel("Read Aloud")
        self.lbl_title.setObjectName("ttsPlayerTitle")
        title_row.addWidget(self.lbl_title)
        info_col.addLayout(title_row)

        self.lbl_status = QLabel("Idle")
        self.lbl_status.setObjectName("subtleLabel")
        info_col.addWidget(self.lbl_status)
        layout.addLayout(info_col)

        # Micro Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("ttsProgressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setFixedWidth(120)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

        # 2. Voice Selector
        lbl_v = QLabel("Voice:")
        lbl_v.setObjectName("subtleLabel")
        layout.addWidget(lbl_v)

        self.combo_voices = QComboBox()
        self.combo_voices.setFixedHeight(26)
        self.combo_voices.setMinimumWidth(150)
        for voice_id, label in SUPPORTED_VOICES:
            self.combo_voices.addItem(label, voice_id)
        layout.addWidget(self.combo_voices)

        # 3. Speed Selector
        lbl_s = QLabel("Speed:")
        lbl_s.setObjectName("subtleLabel")
        layout.addWidget(lbl_s)

        self.combo_speed = QComboBox()
        self.combo_speed.setFixedHeight(26)
        self.combo_speed.setFixedWidth(78)
        self.combo_speed.addItem("0.75x", 0.75)
        self.combo_speed.addItem("1.0x", 1.0)
        self.combo_speed.addItem("1.25x", 1.25)
        self.combo_speed.addItem("1.5x", 1.5)
        self.combo_speed.addItem("2.0x", 2.0)
        self.combo_speed.setCurrentIndex(1)
        layout.addWidget(self.combo_speed)

        # 4. Controls: Play / Stop
        self.btn_play = QPushButton("▶ Play Page")
        self.btn_play.setObjectName("accentButton")
        self.btn_play.setFixedHeight(28)
        self.btn_play.setCursor(Qt.PointingHandCursor)
        self.btn_play.clicked.connect(self._on_play_pause_clicked)
        layout.addWidget(self.btn_play)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setFixedHeight(28)
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        layout.addWidget(self.btn_stop)

        # 5. Dismiss / Close Button
        btn_close = QToolButton()
        btn_close.setText("✕")
        btn_close.setToolTip("Close Read Aloud bar")
        btn_close.setFixedSize(22, 22)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setObjectName("ghostToolButton")
        btn_close.clicked.connect(self._on_close)
        layout.addWidget(btn_close)

        self.update_theme()

    def _on_play_pause_clicked(self):
        text = self.btn_play.text()
        if "Play" in text or "Resume" in text:
            voice = self.combo_voices.currentData()
            speed = float(self.combo_speed.currentData())
            self.play_requested.emit(voice, speed)
        elif "Pause" in text:
            self.pause_requested.emit()

    def _on_close(self):
        self.stop_requested.emit()
        self.setVisible(False)
        self.closed.emit()

    def set_state(self, state: str, detail: str = ""):
        if state == "generating":
            self.lbl_status.setText("Generating neural voice...")
            self.btn_play.setText("⏳ Generating...")
            self.btn_play.setEnabled(False)
        elif state == "playing":
            self.lbl_status.setText("Playing audio" + (f" ({detail})" if detail else ""))
            self.btn_play.setText("⏸ Pause")
            self.btn_play.setEnabled(True)
            self.is_playing = True
        elif state == "paused":
            self.lbl_status.setText("Paused")
            self.btn_play.setText("▶ Resume")
            self.btn_play.setEnabled(True)
            self.is_playing = False
        elif state in ("stopped", "finished", "idle"):
            self.lbl_status.setText("Idle")
            self.btn_play.setText("▶ Play Page")
            self.btn_play.setEnabled(True)
            self.progress_bar.setValue(0)
            self.is_playing = False

    def set_progress(self, current_ms: int, total_ms: int):
        if total_ms > 0:
            pct = int((current_ms / total_ms) * 100)
            self.progress_bar.setValue(pct)
            cur_s = current_ms // 1000
            tot_s = total_ms // 1000
            self.lbl_status.setText(f"Playing: {cur_s // 60}:{cur_s % 60:02d} / {tot_s // 60}:{tot_s % 60:02d}")

    def update_theme(self):
        is_dark = ThemeManager.is_dark()
        bg = "#202024" if is_dark else "#F0F4F9"
        border = "#333338" if is_dark else "#D2D9E4"
        title_color = "#F0F0F0" if is_dark else "#1A1A1A"

        self.setStyleSheet(f"""
            QFrame#ttsMiniPlayerFrame {{
                background-color: {bg};
                border-bottom: 1px solid {border};
            }}
            QLabel#ttsPlayerTitle {{
                font-size: 12px;
                font-weight: 600;
                color: {title_color};
            }}
            QProgressBar#ttsProgressBar {{
                background-color: {'#3A3A40' if is_dark else '#D8DEE8'};
                border-radius: 2px;
            }}
            QProgressBar#ttsProgressBar::chunk {{
                background-color: {'#3B82F6' if is_dark else '#1473E6'};
                border-radius: 2px;
            }}
        """)
