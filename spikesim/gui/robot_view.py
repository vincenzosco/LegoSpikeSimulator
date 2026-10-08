"""Vista 2D del campo: il robot che si muove lungo la traccia."""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import QSizePolicy, QWidget

from ..trace import Trace
from . import theme

#: Ingombro del robot (mm): il drive base SPIKE Prime è circa 16 x 14 cm.
ROBOT_LENGTH_MM = 160.0
ROBOT_WIDTH_MM = 140.0
#: Risoluzione del disegno (pixel per millimetro) usata per lo zoom automatico.
_MARGIN_PX = 40.0


class RobotView(QWidget):
    """Campo di gioco in scala 1:1 con il percorso e il robot."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._trace: Trace | None = None
        self._bounds: tuple[float, float, float, float] = (-400.0, -300.0, 400.0, 300.0)
        self._time_ms: float = 0.0
        self._scale = 1.0
        self._origin_px = QPointF(0, 0)

    # -- API ----------------------------------------------------------------

    def set_trace(self, trace: Trace | None) -> None:
        self._trace = trace
        self._time_ms = 0.0
        self._compute_bounds()
        self.update()

    def set_time(self, t_ms: float) -> None:
        self._time_ms = t_ms
        self.update()

    # -- geometria -----------------------------------------------------------

    def _compute_bounds(self) -> None:
        margin = ROBOT_LENGTH_MM
        if not self._trace or not self._trace.poses:
            self._bounds = (-margin * 2, -margin * 1.5, margin * 2, margin * 1.5)
            return
        xs = [pose[1] for pose in self._trace.poses]
        ys = [pose[2] for pose in self._trace.poses]
        self._bounds = (
            min(xs) - margin,
            min(ys) - margin,
            max(xs) + margin,
            max(ys) + margin,
        )

    def _update_transform(self) -> None:
        left, bottom, right, top = self._bounds
        width_mm = max(1.0, right - left)
        height_mm = max(1.0, top - bottom)
        available_w = max(1.0, self.width() - 2 * _MARGIN_PX)
        available_h = max(1.0, self.height() - 2 * _MARGIN_PX)
        self._scale = min(available_w / width_mm, available_h / height_mm)
        # Centro geometrico del campo -> centro del widget.
        center_world = QPointF((left + right) / 2.0, (bottom + top) / 2.0)
        center_px = QPointF(self.width() / 2.0, self.height() / 2.0)
        self._origin_px = center_px

    def _to_pixel(self, x_mm: float, y_mm: float) -> QPointF:
        left, bottom, right, top = self._bounds
        cx = (left + right) / 2.0
        cy = (bottom + top) / 2.0
        return QPointF(
            self._origin_px.x() + (x_mm - cx) * self._scale,
            # y cresce verso nord: sullo schermo va verso l'alto.
            self._origin_px.y() - (y_mm - cy) * self._scale,
        )

    # -- disegno -------------------------------------------------------------

    def paintEvent(self, _event) -> None:  # noqa: N802 - nome imposto da Qt
        self._update_transform()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(theme.FIELD))

        self._draw_grid(painter)
        self._draw_axes(painter)
        self._draw_path(painter)
        self._draw_robot(painter)
        self._draw_scale_bar(painter)

    def _draw_grid(self, painter: QPainter) -> None:
        left, bottom, right, top = self._bounds
        step = _nice_step(self._scale)
        painter.setPen(QPen(QColor(theme.GRID), 1))
        x = math.floor(left / step) * step
        while x <= right:
            painter.drawLine(
                self._to_pixel(x, bottom), self._to_pixel(x, top)
            )
            x += step
        y = math.floor(bottom / step) * step
        while y <= top:
            painter.drawLine(self._to_pixel(left, y), self._to_pixel(right, y))
            y += step

    def _draw_axes(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor(theme.GRID_MAJOR), 2))
        painter.drawLine(self._to_pixel(0, -100000), self._to_pixel(0, 100000))
        painter.drawLine(self._to_pixel(-100000, 0), self._to_pixel(100000, 0))
        painter.setPen(QColor(theme.TEXT_MUTED))
        painter.setFont(QFont("Helvetica", 9))
        painter.drawText(self._to_pixel(0, 0) + QPointF(4, -4), "0,0")

    def _draw_path(self, painter: QPainter) -> None:
        if not self._trace or len(self._trace.poses) < 2:
            return
        polygon = QPolygonF()
        for t, x, y, _heading in self._trace.poses:
            if t > self._time_ms:
                break
            polygon.append(self._to_pixel(x, y))
        if polygon.size() < 2:
            return
        painter.setPen(QPen(QColor(theme.PATH), 2))
        painter.drawPolyline(polygon)

    def _draw_robot(self, painter: QPainter) -> None:
        if self._trace is None:
            return
        x, y, heading = self._trace.pose_at(self._time_ms)
        center = self._to_pixel(x, y)
        length = ROBOT_LENGTH_MM * self._scale
        width = ROBOT_WIDTH_MM * self._scale

        painter.save()
        painter.translate(center)
        painter.rotate(-heading)  # schermo: y invertita -> rotazione opposta

        body = QRectF(-length / 2.0, -width / 2.0, length, width)
        painter.setPen(QPen(QColor(theme.ROBOT_DARK), 2))
        painter.setBrush(QBrush(QColor(theme.ROBOT)))
        painter.drawRoundedRect(body, 6, 6)

        # Le due ruote: aiutano a capire da che parte è "davanti".
        wheel_w = max(3.0, 14.0 * self._scale)
        wheel_h = max(3.0, 26.0 * self._scale)
        painter.setBrush(QBrush(QColor("#101820")))
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(-length / 3, -width / 2 - wheel_h / 2, wheel_w, wheel_h))
        painter.drawRect(QRectF(-length / 3, width / 2 - wheel_h / 2, wheel_w, wheel_h))

        # Matrice LED: un quadratino chiaro sulla parte anteriore.
        painter.setBrush(QBrush(QColor(theme.MATRIX_ON)))
        size = max(4.0, 30.0 * self._scale)
        painter.drawRect(QRectF(length / 2 - size - 4, -size / 2, size, size))

        # Direzione.
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(Qt.NoPen)
        nose = QPolygonF(
            [
                QPointF(length / 2 + 10, 0),
                QPointF(length / 2 + 1, -6),
                QPointF(length / 2 + 1, 6),
            ]
        )
        painter.drawPolygon(nose)
        painter.restore()

    def _draw_scale_bar(self, painter: QPainter) -> None:
        step = _nice_step(self._scale)
        length_px = step * self._scale
        y = self.height() - 16
        painter.setPen(QPen(QColor(theme.TEXT_MUTED), 2))
        painter.drawLine(QPointF(16, y), QPointF(16 + length_px, y))
        painter.drawLine(QPointF(16, y - 4), QPointF(16, y + 4))
        painter.drawLine(QPointF(16 + length_px, y - 4), QPointF(16 + length_px, y + 4))
        painter.drawText(QPointF(16, y - 8), f"{step:.0f} mm")


def _nice_step(scale: float) -> float:
    """Passo di griglia (mm) che occupa circa 60 pixel sullo schermo."""
    target_mm = 60.0 / max(scale, 1e-6)
    for step in (10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000):
        if step >= target_mm:
            return float(step)
    return 10000.0
