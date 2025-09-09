from PySide6.QtWidgets import QListWidget
from graphics.node_item import NodeItem

class ErrorPanel(QListWidget):
    def __init__(self, scene: 'PowerScene') -> None:
        super().__init__()
        self.scene = scene
        self.setStyleSheet("color: red;")

    def refresh(self) -> None:
        self.clear()
        seen = set()
        for node_item in self.scene.nodes.values():
            for err in node_item.stage.errors:
                if err not in seen:
                    self.addItem(err)
                    seen.add(err)
