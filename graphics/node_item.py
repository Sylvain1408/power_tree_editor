from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QFont, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem
from model.stage import PowerStage

# Visual constants
PORT_RADIUS = 6
NODE_WIDTH = 130
NODE_HEIGHT = 100
TITLE_SIZE = 12
IC_NAME_SIZE = 10
BODY_SIZE = 6
ERROR_SIZE = 10

class NodeItem(QGraphicsRectItem):
    def __init__(self, stage: PowerStage):
        super().__init__(0, 0, NODE_WIDTH, NODE_HEIGHT)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setBrush(QBrush(Qt.white))
        self.setPen(QPen(Qt.black))

        self.stage = stage
        self.title = QtWidgets.QGraphicsTextItem(self)
        self.metrics = QtWidgets.QGraphicsTextItem(self)
        self.icName = QtWidgets.QGraphicsTextItem(self)
        self.errors_text = QtWidgets.QGraphicsTextItem(self)
        self.title.setDefaultTextColor(Qt.black)
        self.icName.setDefaultTextColor(Qt.black)
        self.metrics.setDefaultTextColor(Qt.darkGray)
        self.errors_text.setDefaultTextColor(Qt.red)
        self.refresh_text()
        
        font_title = QFont("Arial", TITLE_SIZE, QFont.Bold)
        self.title.setFont(font_title)
        
        font_icName = QFont("Arial", IC_NAME_SIZE, QFont.Bold)
        self.icName.setFont(font_icName)

        font_metrics = QFont("Arial", BODY_SIZE)
        self.metrics.setFont(font_metrics)

        font_errors = QFont("Arial", ERROR_SIZE)
        self.errors_text.setFont(font_errors)



    def refresh_text(self):
        s = self.stage
        header = f"{s.stage_type}"
        self.title.setPlainText(header)
        #self.title.setPos(6, 4)

        icName = f"{s.ic_name}"
        self.icName.setPlainText(icName)
        self.icName.setPos(2,15)


        info_lines: List[str] = []
        info_lines.append("__________________")
        if s.stage_type.upper() == "INPUT":
            info_lines.append(f"Vout_nom = {s.vout:.3g} V")
            info_lines.append(f"Source range: {s.vin_min:.3g} ; {s.vin_max:.3g} V")
            info_lines.append(f"Imax_source = {s.iout_max_ic:.3g} A")
            if s.notes:
                info_lines.append(f"Notes: {s.notes}")

        elif s.stage_type.upper() == "LOAD":
            info_lines.append(f"Vload = {s.vout:.3g} V")
            info_lines.append(f"Load current = {s.load_current:.3g} A")
            info_lines.append(f"Dissipated power = {s.p_in:.3g} W") 
            if s.notes:
                info_lines.append(f"Notes: {s.notes}")

        else:  # LDO / DCDC
            info_lines.extend([
                f"Vin = {s.vin_effective:.3g} V (range {s.vin_min:.3g} ; {s.vin_max:.3g})",
                f"Vout = {s.vout:.3g} V",
                f"Imax_IC = {s.iout_max_ic:.3g} A",
                f"η = {s.eff_effective*100:.1f}%, Iq = {s.iq:.3g} uA",
                f"Pin = {s.p_in:.3g} W, Pout = {s.p_out:.3g} W",
                f"Iin = {s.i_in:.3g} A, Pdiss = {s.p_diss:.3g} W",
                f"Ptot ≈ {s.p_tot:.3g} W",
            ])

        self.metrics.setPlainText('\n'.join(info_lines))
        self.metrics.setPos(4, 20)
        self.errors_text.setPlainText('\n'.join(s.errors))
        self.errors_text.setDefaultTextColor(Qt.red)
        self.errors_text.setPos(6, NODE_HEIGHT)

    def input_port_pos(self) -> QPointF:
        rect = self.rect()
        return self.mapToScene(QPointF(rect.left(), rect.center().y()))

    def output_port_pos(self) -> QPointF:
        rect = self.rect()
        return self.mapToScene(QPointF(rect.right(), rect.center().y()))

    def paint(self, painter, option, widget=None):
        # background from stage color (fallback to white)
        col = QtGui.QColor(self.stage.color) if hasattr(self.stage, "color") else QtGui.QColor("#ffffff")
        painter.setBrush(QBrush(col))
        painter.setPen(QPen(Qt.black))
        painter.drawRect(self.rect())

        rect = self.rect()
        # draw ports (same logic as before)
        painter.setBrush(QBrush(Qt.black))
        # draw input port except for INPUT stage (source has no input)
        if self.stage.stage_type.upper() != "INPUT":
            painter.drawEllipse(rect.left() - PORT_RADIUS, rect.center().y() - PORT_RADIUS, PORT_RADIUS*2, PORT_RADIUS*2)
        # draw output port except for LOAD stage (load has no output)
        if self.stage.stage_type.upper() != "LOAD":
            painter.drawEllipse(rect.right() - PORT_RADIUS, rect.center().y() - PORT_RADIUS, PORT_RADIUS*2, PORT_RADIUS*2)


    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            sc = self.scene()
            if sc and hasattr(sc, 'update_edges'):
                sc.update_edges()
        return super().itemChange(change, value)

