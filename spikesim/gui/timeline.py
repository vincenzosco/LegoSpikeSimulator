"""Comandi di riproduzione della simulazione."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QWidget,
)

SPEEDS = (0.25, 0.5, 1.0, 2.0, 5.0, 10.0)
_TICK_MS = 33


class Timeline(QWidget):
    """Play/pausa, barra del tempo e velocità di riproduzione."""

    timeChanged = pyqtSignal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._duration = 0.0
        self._time = 0.0
        self._speed = 1.0
        self._dragging = False

        self.play_button = QPushButton("▶  Riproduci")
        self.play_button.setObjectName("primary")
        self.play_button.clicked.connect(self.toggle)
        self.play_button.setEnabled(False)

        self.restart_button = QPushButton("⟲")
        self.restart_button.setToolTip("Torna all'inizio")
        self.restart_button.clicked.connect(self.restart)
        self.restart_button.setEnabled(False)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setEnabled(False)
        self.slider.sliderPressed.connect(self._on_slider_pressed)
        self.slider.sliderReleased.connect(self._on_slider_released)
        self.slider.valueChanged.connect(self._on_slider_moved)

        self.time_label = QLabel("0.00 s / 0.00 s")
        self.time_label.setMinimumWidth(140)

        self.speed_combo = QComboBox()
        for speed in SPEEDS:
            self.speed_combo.addItem(f"{speed:g}x", speed)
        self.speed_combo.setCurrentIndex(SPEEDS.index(1.0))
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        layout.addWidget(self.play_button)
        layout.addWidget(self.restart_button)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.time_label)
        layout.addWidget(QLabel("velocità"))
        layout.addWidget(self.speed_combo)

        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)

    # -- API ----------------------------------------------------------------

    def set_duration(self, duration_ms: float) -> None:
        self._duration = max(0.0, float(duration_ms))
        self._time = 0.0
        self._timer.stop()
        self.play_button.setText("▶  Riproduci")
        enabled = self._duration > 0
        self.play_button.setEnabled(enabled)
        self.restart_button.setEnabled(enabled)
        self.slider.setEnabled(enabled)
        self._update_label()
        self.timeChanged.emit(0.0)

    def set_time(self, t_ms: float) -> None:
        """Posiziona la riproduzione (usato anche dai pulsanti)."""
        self._time = max(0.0, min(self._duration, float(t_ms)))
        self._sync_slider()
        self._update_label()
        self.timeChanged.emit(self._time)

    @property
    def time_ms(self) -> float:
        return self._time

    def is_playing(self) -> bool:
        return self._timer.isActive()

    def play(self) -> None:
        if self._duration <= 0:
            return
        if self._time >= self._duration:
            self._time = 0.0
        self._timer.start()
        self.play_button.setText("⏸  Pausa")

    def pause(self) -> None:
        self._timer.stop()
        self.play_button.setText("▶  Riproduci")

    def toggle(self) -> None:
        if self.is_playing():
            self.pause()
        else:
            self.play()

    def restart(self) -> None:
        self.pause()
        self.set_time(0.0)

    # -- interni -------------------------------------------------------------

    def _tick(self) -> None:
        self._time += _TICK_MS * self._speed
        if self._time >= self._duration:
            self._time = self._duration
            self.pause()
        self._sync_slider()
        self._update_label()
        self.timeChanged.emit(self._time)

    def _sync_slider(self) -> None:
        if self._duration <= 0:
            return
        self._dragging = True
        self.slider.setValue(int(self._time / self._duration * 1000))
        self._dragging = False

    def _update_label(self) -> None:
        self.time_label.setText(f"{self._time / 1000:.2f} s / {self._duration / 1000:.2f} s")

    def _on_slider_pressed(self) -> None:
        self._dragging = True

    def _on_slider_released(self) -> None:
        self._dragging = False
        self._apply_slider()

    def _on_slider_moved(self, _value: int) -> None:
        if self._dragging:
            self._apply_slider()

    def _apply_slider(self) -> None:
        if self._duration <= 0:
            return
        self.pause()
        self.set_time(self.slider.value() / 1000.0 * self._duration)

    def _on_speed_changed(self, _index: int) -> None:
        self._speed = float(self.speed_combo.currentData())
