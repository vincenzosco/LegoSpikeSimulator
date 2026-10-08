"""Configurazione dell'hardware: cosa è collegato a ogni porta del hub.

È il pannello che rende utile la simulazione: senza sapere quali porte hanno
motori e sensori, il checker non può dire "su questa porta non c'è niente" e
il robot simulato non saprebbe quali ruote far girare.
"""

from __future__ import annotations

from dataclasses import replace

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    DEVICE_LABELS,
    PORT_A,
    PORT_B,
    PORT_NAMES,
    PORTS,
    Config,
    PortConfig,
    default_config,
)
from ..spike import _consts as K


class PortConfigPanel(QScrollArea):
    """Un selettore per porta, più i parametri fisici e i sensori."""

    configChanged = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self._config = default_config()

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(10)

        self.title = QLabel("Hardware")
        self.title.setProperty("role", "section")
        layout.addWidget(self.title)

        self._device_boxes: dict[int, QComboBox] = {}
        self._reversed_boxes: dict[int, QCheckBox] = {}
        layout.addWidget(self._build_ports_group())

        self._left_combo = self._port_combo()
        self._right_combo = self._port_combo()
        layout.addWidget(self._build_drive_group())

        self._wheel = QDoubleSpinBox()
        self._wheel.setRange(20.0, 200.0)
        self._wheel.setSuffix(" mm")
        self._wheel.setValue(self._config.wheel_diameter_mm)
        self._wheel.valueChanged.connect(self._emit)

        self._track = QDoubleSpinBox()
        self._track.setRange(20.0, 400.0)
        self._track.setSuffix(" mm")
        self._track.setValue(self._config.track_width_mm)
        self._track.valueChanged.connect(self._emit)

        layout.addWidget(self._build_geometry_group())
        layout.addWidget(self._build_sensors_group())
        layout.addStretch(1)

        self.setWidget(body)

    # -- costruzione ---------------------------------------------------------

    def _port_combo(self) -> QComboBox:
        combo = QComboBox()
        for port in PORTS:
            combo.addItem(PORT_NAMES[port], port)
        combo.currentIndexChanged.connect(self._emit)
        return combo

    def _build_ports_group(self) -> QGroupBox:
        group = QGroupBox("Porte")
        form = QFormLayout(group)
        for port in PORTS:
            combo = QComboBox()
            for kind, label in DEVICE_LABELS.items():
                combo.addItem(label, kind)
            current = self._config.device(port)
            combo.setCurrentIndex(max(0, combo.findData(current)))
            combo.currentIndexChanged.connect(self._emit)
            self._device_boxes[port] = combo

            reversed_box = QCheckBox("invertito")
            reversed_box.toggled.connect(self._emit)
            self._reversed_boxes[port] = reversed_box

            row = QWidget()
            row_layout = QFormLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addRow(combo, reversed_box)
            form.addRow(f"Porta {PORT_NAMES[port]}", row)
        return group

    def _build_drive_group(self) -> QGroupBox:
        group = QGroupBox("Drive base")
        form = QFormLayout(group)
        self._left_combo.setCurrentIndex(PORT_A)
        self._right_combo.setCurrentIndex(PORT_B)
        form.addRow("Ruota sinistra", self._left_combo)
        form.addRow("Ruota destra", self._right_combo)
        hint = QLabel(
            "Solo i motori di queste due porte fanno muovere il robot; "
            "gli altri motori girano senza spostarlo."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#93a0b8;")
        form.addRow(hint)
        return group

    def _build_geometry_group(self) -> QGroupBox:
        group = QGroupBox("Geometria")
        form = QFormLayout(group)
        form.addRow("Diametro ruota", self._wheel)
        form.addRow("Distanza fra le ruote", self._track)
        return group

    def _build_sensors_group(self) -> QGroupBox:
        group = QGroupBox("Valori dei sensori")
        form = QFormLayout(group)

        self._color_combo = QComboBox()
        for index, name in enumerate(K.COLOR_NAMES):
            self._color_combo.addItem(name.lower(), index)
        self._color_combo.addItem("unknown", K.COLOR_UNKNOWN)
        self._color_combo.setCurrentIndex(
            max(0, self._color_combo.findData(self._config.sensors.color))
        )
        self._color_combo.currentIndexChanged.connect(self._emit)

        self._reflection = QSpinBox()
        self._reflection.setRange(0, 100)
        self._reflection.setSuffix(" %")
        self._reflection.setValue(self._config.sensors.reflection)
        self._reflection.valueChanged.connect(self._emit)

        self._distance = QSpinBox()
        self._distance.setRange(-1, 2000)
        self._distance.setSuffix(" mm")
        self._distance.setValue(self._config.sensors.distance)
        self._distance.valueChanged.connect(self._emit)

        self._force = QSpinBox()
        self._force.setRange(0, 100)
        self._force.setValue(self._config.sensors.force)
        self._force.valueChanged.connect(self._emit)

        self._pressed = QCheckBox("premuto")
        self._pressed.setChecked(self._config.sensors.pressed)
        self._pressed.toggled.connect(self._emit)

        form.addRow("Colore", self._color_combo)
        form.addRow("Riflessione", self._reflection)
        form.addRow("Distanza", self._distance)
        form.addRow("Forza", self._force)
        form.addRow("Pulsante forza", self._pressed)
        return group

    # -- API ----------------------------------------------------------------

    def config(self) -> Config:
        """Configurazione corrente, pronta per il runner."""
        ports = {
            port: PortConfig(
                self._device_boxes[port].currentData(),
                self._reversed_boxes[port].isChecked(),
            )
            for port in PORTS
        }
        return replace(
            self._config,
            ports=ports,
            drive_left_port=self._left_combo.currentData(),
            drive_right_port=self._right_combo.currentData(),
            wheel_diameter_mm=float(self._wheel.value()),
            track_width_mm=float(self._track.value()),
            sensors=replace(
                self._config.sensors,
                color=int(self._color_combo.currentData()),
                reflection=int(self._reflection.value()),
                distance=int(self._distance.value()),
                force=int(self._force.value()),
                pressed=bool(self._pressed.isChecked()),
            ),
        )

    def _emit(self, *_args) -> None:
        self.configChanged.emit()
