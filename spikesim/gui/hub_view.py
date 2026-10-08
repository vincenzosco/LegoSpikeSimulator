"""Vista del hub: la matrice 5x5 e lo stato dei motori."""

from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QSizePolicy, QWidget

from ..config import DEVICE_LABELS, PORT_NAMES, Config
from ..trace import Trace
from . import theme


class HubView(QWidget):
    """Disegna ciò che il hub mostrerebbe e ciò che i motori stanno facendo."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._trace: Trace | None = None
        self._config = Config()
        self._time_ms = 0.0
        self._pixels = [0] * 25
        self._lights = {0: 0, 1: 0}
        self._matrix_event_index = 0

    # -- API ----------------------------------------------------------------

    def set_trace(self, trace: Trace | None, config: Config) -> None:
        self._trace = trace
        self._config = config
        self._time_ms = 0.0
        self._pixels = [0] * 25
        self._lights = {0: 0, 1: 0}
        self._matrix_event_index = 0
        self.update()

    def set_time(self, t_ms: float) -> None:
        if self._trace is None:
            return
        if t_ms < self._time_ms:
            self._pixels = [0] * 25
            self._matrix_event_index = 0
            self._lights = {0: 0, 1: 0}
        self._time_ms = t_ms
        events = self._trace.events
        while self._matrix_event_index < len(events):
            event = events[self._matrix_event_index]
            if event.t > t_ms:
                break
            if event.type == "light_matrix":
                self._pixels = list(event.data.get("pixels", self._pixels))
            elif event.type == "hub_light":
                self._lights[int(event.data.get("light", 0))] = int(
                    event.data.get("color", 0)
                )
            self._matrix_event_index += 1
        self.update()

    # -- disegno -------------------------------------------------------------

    def paintEvent(self, _event) -> None:  # noqa: N802 - nome imposto da Qt
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(theme.SURFACE))
        painter.setPen(QColor(theme.TEXT_MUTED))
        painter.setFont(QFont("Helvetica", 9, QFont.Bold))
        painter.drawText(12, 18, "MATRICE LED")

        self._draw_matrix(painter, QRectF(12, 26, 130, 130))
        self._draw_lights(painter)
        self._draw_motors(painter, 160)
        self._draw_sensors(painter, 160)

    def _draw_matrix(self, painter: QPainter, area: QRectF) -> None:
        cell = area.width() / 5.0
        for y in range(5):
            for x in range(5):
                intensity = self._pixels[y * 5 + x] if len(self._pixels) >= 25 else 0
                alpha = max(0.08, min(1.0, intensity / 100.0))
                color = QColor(theme.MATRIX_ON)
                color.setAlphaF(alpha if intensity else 0.06)
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(
                    QRectF(
                        area.left() + x * cell + 2,
                        area.top() + y * cell + 2,
                        cell - 4,
                        cell - 4,
                    ),
                    4,
                    4,
                )

    def _draw_lights(self, painter: QPainter) -> None:
        painter.setPen(QColor(theme.TEXT_MUTED))
        painter.setFont(QFont("Helvetica", 9))
        labels = ("POWER", "CONNECT")
        for index, label in enumerate(labels):
            color_index = self._lights.get(index, 0)
            painter.drawText(12, 180 + index * 20, label)
            color = QColor("#333333")
            if 0 <= color_index < len(theme.SPIKE_COLORS):
                color = QColor(theme.SPIKE_COLORS[color_index])
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor(theme.BORDER), 1))
            painter.drawEllipse(QRectF(70, 170 + index * 20, 10, 10))

    def _draw_motors(self, painter: QPainter, left: int) -> None:
        painter.setPen(QColor(theme.TEXT_MUTED))
        painter.setFont(QFont("Helvetica", 9, QFont.Bold))
        painter.drawText(left, 18, "MOTORI")

        painter.setFont(QFont("Menlo", 9))
        row = 38
        for port in sorted(self._config.ports):
            kind = self._config.device(port)
            if kind not in ("motor_small", "motor_medium", "motor_large"):
                continue
            velocity = 0.0
            if self._trace is not None:
                for event in self._trace.events_until(self._time_ms, ("motor",)):
                    if int(event.data.get("port", -1)) == port:
                        velocity = float(event.data.get("velocity", 0.0))
            limit = max(1.0, float(self._config.velocity_limit(port)))

            painter.setPen(QColor(theme.TEXT))
            painter.drawText(left, row, f"{PORT_NAMES[port]}")
            bar_x = left + 20
            bar_w = max(60, self.width() - bar_x - 70)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(theme.SURFACE_ALT)))
            painter.drawRoundedRect(QRectF(bar_x, row - 9, bar_w, 10), 5, 5)
            fraction = max(-1.0, min(1.0, velocity / limit))
            width = abs(fraction) * bar_w / 2.0
            start = bar_x + bar_w / 2.0 + (0 if fraction >= 0 else -width)
            painter.setBrush(QBrush(QColor(theme.ACCENT if fraction >= 0 else theme.WARNING)))
            painter.drawRoundedRect(QRectF(start, row - 9, max(2.0, width), 10), 5, 5)

            painter.setPen(QColor(theme.TEXT_MUTED))
            painter.drawText(int(bar_x + bar_w + 6), row, f"{velocity:6.0f}°/s")
            row += 20

    def _draw_sensors(self, painter: QPainter, left: int) -> None:
        if self._trace is None:
            return
        row = 150
        painter.setFont(QFont("Menlo", 9))
        for port in sorted(self._config.ports):
            kind = self._config.device(port)
            if kind not in (
                "color_sensor",
                "distance_sensor",
                "force_sensor",
                "color_matrix",
            ):
                continue
            painter.setPen(QColor(theme.TEXT_MUTED))
            painter.drawText(left, row, f"{PORT_NAMES[port]}: {DEVICE_LABELS[kind]}")
            row += 16
        if self._trace is not None:
            yaw = self._trace.pose_at(self._time_ms)[2]
            painter.setPen(QColor(theme.TEXT_MUTED))
            painter.drawText(left, row + 8, f"yaw: {yaw * 10:+.0f} d°")
