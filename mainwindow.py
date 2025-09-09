import json
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QMainWindow, QGraphicsView, QDockWidget, QToolBar, QVBoxLayout, QWidget, QFileDialog, QMessageBox
from PySide6.QtGui import QAction, QBrush
from graphics.scene import PowerScene
from ui.inspector import Inspector
from ui.error_panel import ErrorPanel

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Power Tree Editor")
        self.resize(1400, 900)

        self.scene = PowerScene(self)
        self.scene.setBackgroundBrush(QBrush(Qt.white))
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.view.setDragMode(QGraphicsView.RubberBandDrag)
        self.setCentralWidget(self.view)

        # Toolbar
        toolbar = self.addToolBar("Tools")
        action_add_input = QAction("Add Source", self)
        action_add_input.triggered.connect(lambda: self.scene.add_stage("INPUT"))
        toolbar.addAction(action_add_input)
        action_add_ldo = QAction("Add LDO", self)
        action_add_ldo.triggered.connect(lambda: self.scene.add_stage("LDO"))
        toolbar.addAction(action_add_ldo)
        action_add_dcdc = QAction("Add DCDC", self)
        action_add_dcdc.triggered.connect(lambda: self.scene.add_stage("DCDC"))
        toolbar.addAction(action_add_dcdc)
        toolbar.addSeparator()
        action_add_load = QAction("Add Load", self)
        action_add_load.triggered.connect(lambda: self.scene.add_stage("LOAD"))
        toolbar.addAction(action_add_load)
        action_update = QAction("Recompute", self)
        action_update.triggered.connect(lambda: self.scene.recompute_all())
        toolbar.addAction(action_update)
        toolbar.addSeparator()
        action_save = QAction("Save (.json)", self)
        action_save.triggered.connect(self.do_save)
        toolbar.addAction(action_save)
        action_load = QAction("Open (.json)", self)
        action_load.triggered.connect(self.do_load)
        toolbar.addAction(action_load)
                
        self.view.setFocus()  # for keyPressEvent

        # Inspector dock
        self.inspector = Inspector(self.scene)
        dock = QDockWidget("Properties", self)
        dock.setWidget(self.inspector)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        # Error dock
        self.error_panel = ErrorPanel(self.scene)
        dock_err = QDockWidget("Errors", self)
        dock_err.setWidget(self.error_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock_err)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.scene.delete_selected()
        else:
            super().keyPressEvent(event)
                
    def refresh_errors(self) -> None:
        self.error_panel.refresh()

    # basic save/load
    def do_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save project", filter="PowerTree (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.scene.serialize(), f, indent=2)
        QMessageBox.information(self, "Save", f"Project saved: {path}")

    def do_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open project", filter="PowerTree (*.json)")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.scene.deserialize(data)
        QMessageBox.information(self, "Open", f"Project loaded: {path}")
