"""Il pannello «Tappeto e luce»: template, sorteggio e luce ambientale.

È il pannello che rende la richiesta utilizzabile a mano: si sceglie un
percorso (per esempio *Seguilinea*), si può risorteggiare il tappeto e si
regola la luce ambientale per vedere come reagisce il robot.
"""

from __future__ import annotations

import random

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import templates
from ..mat import Mat, TrackTemplate, generate_track


class MatPanel(QWidget):
    """Sceglie il template, sorteggia il tappeto e regola la luce."""

    #: Il tappeto o la luce sono cambiati: la simulazione precedente non vale più.
    matChanged = pyqtSignal()
    #: L'utente ha scelto un template: qualcuno deve caricarne il programma.
    templateChosen = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._templates = list(templates.all_templates())
        self._index = 0
        self._mat: Mat = Mat()

        body = QVBoxLayout(self)
        body.setContentsMargins(8, 6, 8, 8)
        body.setSpacing(10)

        title = QLabel("Tappeto e luce")
        title.setProperty("role", "section")
        body.addWidget(title)

        body.addWidget(self._build_template_group())
        body.addWidget(self._build_light_group())
        body.addStretch(1)

        self._regenerate(emit=False)

    # -- costruzione ---------------------------------------------------------

    def _build_template_group(self) -> QGroupBox:
        group = QGroupBox("Percorso")
        form = QFormLayout(group)

        self.template_combo = QComboBox()
        for template in self._templates:
            self.template_combo.addItem(template.name, template.key)
        self.template_combo.setCurrentIndex(0)
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        form.addRow("Template", self.template_combo)

        self.description = QLabel(self._templates[0].description)
        self.description.setWordWrap(True)
        self.description.setStyleSheet("color:#93a0b8;")
        form.addRow(self.description)

        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 999_999)
        self.seed_spin.setToolTip("Con lo stesso seme si sorteggia sempre la stessa pista.")
        self.seed_spin.valueChanged.connect(self._on_seed_changed)

        self.reroll_button = QPushButton("🎲 Nuovo percorso")
        self.reroll_button.clicked.connect(self.reroll)

        seed_row = QWidget()
        seed_layout = QHBoxLayout(seed_row)
        seed_layout.setContentsMargins(0, 0, 0, 0)
        seed_layout.addWidget(self.seed_spin)
        seed_layout.addWidget(self.reroll_button)
        form.addRow("Seme", seed_row)

        self.info = QLabel()
        self.info.setStyleSheet("color:#93a0b8;")
        form.addRow(self.info)
        return group

    def _build_light_group(self) -> QGroupBox:
        group = QGroupBox("Luce ambientale")
        form = QFormLayout(group)

        self.light_slider = QSlider(Qt.Horizontal)
        self.light_slider.setRange(0, 100)
        self.light_slider.setValue(100)
        self.light_slider.setToolTip(
            "Sotto il 25 % il sensore di colore non distingue più i colori: "
            "il robot non vede più la pista."
        )
        self.light_slider.valueChanged.connect(self._on_light_changed)

        self.light_value = QLabel("100 %")
        self.light_value.setMinimumWidth(48)

        light_row = QWidget()
        light_layout = QHBoxLayout(light_row)
        light_layout.setContentsMargins(0, 0, 0, 0)
        light_layout.addWidget(self.light_slider, 1)
        light_layout.addWidget(self.light_value)
        form.addRow("Luce", light_row)

        hint = QLabel(
            "Abbassa la luce e premi Simula: al buio il segui-linea non "
            "riconosce più le mattonelle e si ferma."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#93a0b8;")
        form.addRow(hint)
        return group

    # -- API -----------------------------------------------------------------

    def template(self) -> TrackTemplate:
        """Il template scelto."""
        return self._templates[self._index]

    def mat(self) -> Mat:
        """Il tappeto attualmente sorteggiato."""
        return self._mat

    def seed(self) -> int:
        """Il seme del sorteggio corrente."""
        return int(self.seed_spin.value())

    def ambient_light(self) -> int:
        """Luce ambientale in percentuale (0-100)."""
        return int(self.light_slider.value())

    def set_template_by_key(self, key: str) -> bool:
        """Seleziona il template con questa chiave; ``False`` se non esiste."""
        for index, template in enumerate(self._templates):
            if template.key == key:
                self.template_combo.setCurrentIndex(index)
                return True
        return False

    def reroll(self) -> None:
        """Sorteggia una pista nuova (un seme diverso)."""
        new_seed = random.randrange(0, 1_000_000)
        if new_seed == self.seed_spin.value():
            new_seed = (new_seed + 1) % 1_000_000
        self.seed_spin.setValue(new_seed)

    def set_ambient_light(self, value: int) -> None:
        """Imposta la luce ambientale (comodo per gli script e i test)."""
        self.light_slider.setValue(int(value))

    # -- interni -------------------------------------------------------------

    def _regenerate(self, *, emit: bool = True) -> None:
        template = self.template()
        self._mat = generate_track(
            self.seed(),
            straights=template.straights,
            turns=template.turns,
            tile_size_mm=template.tile_size_mm,
        )
        self.info.setText(f"{len(self._mat.tiles)} mattonelle, lato {template.tile_size_mm:.0f} mm")
        if emit:
            self.matChanged.emit()

    def _on_template_changed(self, index: int) -> None:
        self._index = index
        self.description.setText(self.template().description)
        self.seed_spin.blockSignals(True)
        self.seed_spin.setValue(0)
        self.seed_spin.blockSignals(False)
        self._regenerate()
        self.templateChosen.emit(self.template())

    def _on_seed_changed(self, _value: int) -> None:
        self._regenerate()

    def _on_light_changed(self, value: int) -> None:
        self.light_value.setText(f"{value} %")
        self.matChanged.emit()
