from PySide6 import QtWidgets
from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QDoubleSpinBox, QSpinBox, QColorDialog, QPushButton, QComboBox, QTextEdit
from graphics.node_item import NodeItem
from typing import Dict, List, Optional

class Inspector(QtWidgets.QWidget):
    def __init__(self, scene: 'PowerScene') -> None:
        super().__init__()
        self.scene = scene
        self.current_node: Optional[NodeItem] = None
        self._suppress_signals = False

        layout = QFormLayout(self)

        self.stage_type = QComboBox(); self.stage_type.addItems(["INPUT", "LDO", "DCDC", "LOAD"])
        self.name_edit = QLineEdit()
        self.ic_edit = QLineEdit()
        self.vin_min_spin = QDoubleSpinBox(); self.vin_min_spin.setRange(-1000, 1000); self.vin_min_spin.setDecimals(4)
        self.vin_max_spin = QDoubleSpinBox(); self.vin_max_spin.setRange(-1000, 1000); self.vin_max_spin.setDecimals(4)
        self.vin_nom_spin = QDoubleSpinBox(); self.vin_nom_spin.setRange(-1000, 1000); self.vin_nom_spin.setDecimals(4)
        self.vout_spin = QDoubleSpinBox(); self.vout_spin.setRange(-1000, 1000); self.vout_spin.setDecimals(4)
        self.load_current_spin = QDoubleSpinBox(); self.load_current_spin.setRange(0, 1000); self.load_current_spin.setDecimals(6)
        self.iout_max_spin = QDoubleSpinBox(); self.iout_max_spin.setRange(0, 1000); self.iout_max_spin.setDecimals(6)
        self.eff_spin = QDoubleSpinBox(); self.eff_spin.setRange(0, 1.0); self.eff_spin.setSingleStep(0.01); self.eff_spin.setDecimals(4)
        self.iq_spin = QDoubleSpinBox(); self.iq_spin.setRange(0, 10e5); self.iq_spin.setDecimals(9)
        self.notes_edit = QTextEdit()

        layout.addRow("Type", self.stage_type)
        layout.addRow("Name", self.name_edit)
        layout.addRow("IC", self.ic_edit)
        layout.addRow("Vin min (V)", self.vin_min_spin)
        layout.addRow("Vin max (V)", self.vin_max_spin)
        layout.addRow("Vin nominal (V)", self.vin_nom_spin)
        layout.addRow("Vout (V)", self.vout_spin)
        layout.addRow("Load current (A)", self.load_current_spin)
        layout.addRow("Imax (A) - IC or source", self.iout_max_spin)
        layout.addRow("Efficiency η (DCDC)", self.eff_spin)
        layout.addRow("Iq (uA)", self.iq_spin)
        layout.addRow("Notes", self.notes_edit)

        self._bind_signals()
        self.setDisabled(True)
        
        # color picker
        self.color_button = QPushButton("Block color...")
        layout.addRow("Color", self.color_button)
        self.color_button.clicked.connect(self._on_color_clicked)
        

    def _on_color_clicked(self) -> None:
        if not self.current_node:
            return
        # start color dialog with current color
        initial = QtGui.QColor(self.current_node.stage.color)
        col = QColorDialog.getColor(initial, self, "Choose block color")
        if col.isValid():
            # set hex string
            self.current_node.stage.color = col.name()  # e.g. "#aabbcc"
            # update visuals immediately
            self.current_node.update()    # triggers repaint
            self.current_node.refresh_text()
            # notify recompute if needed
            self.current_node.scene().recompute_all()



    def _bind_signals(self) -> None:
        self.stage_type.currentTextChanged.connect(self._on_change)
        self.name_edit.textEdited.connect(self._on_change)
        self.ic_edit.textEdited.connect(self._on_change)

        for widget in [self.vin_min_spin, self.vin_max_spin, self.vin_nom_spin, self.vout_spin,
                       self.load_current_spin, self.iout_max_spin, self.eff_spin, self.iq_spin]:
            widget.setKeyboardTracking(True)
            widget.valueChanged.connect(self._on_change)

        self.notes_edit.textChanged.connect(self._on_change)

    def _on_change(self, *args) -> None:
        if self._suppress_signals or not self.current_node:
            return

        stage = self.current_node.stage
        stage.stage_type = self.stage_type.currentText()
        stage.name = self.name_edit.text()
        stage.ic_name = self.ic_edit.text()
        stage.vin_min = self.vin_min_spin.value()
        stage.vin_max = self.vin_max_spin.value()
        stage.vin_nom = self.vin_nom_spin.value()
        stage.vout = self.vout_spin.value()
        stage.load_current = self.load_current_spin.value()
        stage.iout_max_ic = self.iout_max_spin.value()
        stage.efficiency_user = self.eff_spin.value()
        stage.iq = self.iq_spin.value()
        stage.notes = self.notes_edit.toPlainText()

        # notify scene to recompute
        self.current_node.scene().recompute_all()

    def set_node(self, node: Optional[NodeItem]) -> None:
        """Populate the inspector with the selected node's values. Disable signals while updating."""
        self.current_node = node
        if node is None:
            self.setDisabled(True)
            return
        self.setDisabled(False)

        s = node.stage
        self._suppress_signals = True
        try:
            self.stage_type.setCurrentText(s.stage_type)
            self.name_edit.setText(s.name)
            self.ic_edit.setText(s.ic_name)
            self.vin_min_spin.setValue(s.vin_min)
            self.vin_max_spin.setValue(s.vin_max)
            self.vin_nom_spin.setValue(s.vin_nom)
            self.vout_spin.setValue(s.vout)
            self.load_current_spin.setValue(s.load_current)
            self.iout_max_spin.setValue(s.iout_max_ic)
            self.eff_spin.setValue(s.efficiency_user)
            self.iq_spin.setValue(s.iq)
            self.notes_edit.setPlainText(s.notes)

            stype = s.stage_type.upper()
            self.ic_edit.setEnabled(stype in ("LDO", "DCDC"))
            self.vin_min_spin.setEnabled(stype in ("LDO", "DCDC", "INPUT"))
            self.vin_max_spin.setEnabled(stype in ("LDO", "DCDC", "INPUT"))
            # vin nominal is internal and not editable
            self.vin_nom_spin.setEnabled(False)
            self.vout_spin.setEnabled(stype in ("LDO", "DCDC", "INPUT"))
            self.load_current_spin.setEnabled(stype == "LOAD")
            self.iout_max_spin.setEnabled(stype in ("LDO", "DCDC", "INPUT"))
            self.eff_spin.setEnabled(stype in ("DCDC"))
            self.iq_spin.setEnabled(stype in ("LDO", "DCDC"))

        finally:
            self._suppress_signals = False
