from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem

class EdgeItem(QGraphicsPathItem):
    """Graphical curved edge between an output port of a source node and an input port of a destination node."""
    def __init__(self, src_node: 'NodeItem', dst_node: 'NodeItem'):
        super().__init__()
        self.setZValue(-1)
        self.src_node = src_node
        self.dst_node = dst_node
        pen = QPen(Qt.black)
        pen.setWidth(2)
        self.setPen(pen)
        self.update_path()

    def update_path(self):
        start = self.src_node.output_port_pos()
        end = self.dst_node.input_port_pos()
        path = QPainterPath(start)
        dx = (end.x() - start.x()) * 0.5
        c1 = QPointF(start.x() + dx, start.y())
        c2 = QPointF(end.x() - dx, end.y())
        path.cubicTo(c1, c2, end)
        self.setPath(path)
