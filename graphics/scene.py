import json
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsPathItem
from PySide6.QtGui import QPainterPath, QPen, QBrush, QAction, QFont, QColor
from model.stage import PowerStage
from graphics.node_item import NodeItem
from graphics.edge_item import EdgeItem
from typing import Dict, List, Optional

PORT_RADIUS = 6

class PowerScene(QGraphicsScene):
    def __init__(self, mainwindow: 'MainWindow') -> None:
        super().__init__()
        self.mainwindow = mainwindow
        self.nodes: Dict[str, NodeItem] = {}
        self.edges: List[EdgeItem] = []

        # connection state while user is dragging connections
        self.is_connecting = False
        self.connect_source: Optional[NodeItem] = None
        self.temp_edge: Optional[QGraphicsPathItem] = None

        # selection change -> update inspector
        self.selectionChanged.connect(self.on_selection_changed)

    # ---------- topology helper: compute requested currents ----------
    def compute_requested_currents(self) -> None:
        """Compute iout_user for every node by summing children's input currents.

        We perform a topological traversal so children currents are known when
        parents are computed.
        """
        # Build incoming edge counts (number of upstream references per node)
        incoming_count: Dict[str, int] = {node_id: 0 for node_id in self.nodes}
        for node_item in self.nodes.values():
            if node_item.stage.upstream:
                incoming_count[node_item.stage.id] += 1

        # Kahn's algorithm seed: nodes with no incoming edges
        work_stack = [n for n in self.nodes.values() if incoming_count[n.stage.id] == 0]
        topo_order: List[NodeItem] = []
        visited = set()
        while work_stack:
            current = work_stack.pop()
            topo_order.append(current)
            visited.add(current.stage.id)
            # push neighbors (those that have upstream == current)
            for neighbor in self.nodes.values():
                if neighbor.stage.upstream == current.stage.id:
                    incoming_count[neighbor.stage.id] -= 1
                    if incoming_count[neighbor.stage.id] == 0 and neighbor.stage.id not in visited:
                        work_stack.append(neighbor)

        # compute requested currents bottom-up (leaves first)
        for node_item in reversed(topo_order):
            if node_item.stage.stage_type.upper() == "LOAD":
                node_item.stage.iout_user = node_item.stage.load_current
            else:
                total_child_iin = 0.0
                for child in self.nodes.values():
                    if child.stage.upstream == node_item.stage.id:
                        total_child_iin += child.stage.i_in
                node_item.stage.iout_user = total_child_iin

    # ---------- node / edge management ----------
    def add_stage(self, stage_type: str, pos: Optional[QPointF] = None) -> NodeItem:
        #default color map
        color_map = {
            "INPUT": "#cfefff",   # light blue
            "LDO":   "#d4f7d4",   # light green
            "DCDC":  "#fff2c2",   # light yellow
            "LOAD":  "#e8e8e8",   # light gray
        }
        new_stage = PowerStage(stage_type=stage_type, name=f"{stage_type}_{len(self.nodes)+1}")
        # set default color according to type
        new_stage.color = color_map.get(stage_type.upper(), "#ffffff")
        if stage_type.upper() == "INPUT":
            new_stage.vin_nom = 12.0
            new_stage.vin_min = 11.0
            new_stage.vin_max = 13.0
            new_stage.iout_max_ic = 2.0
        node_item = NodeItem(new_stage)
        if pos is None:
            node_item.setPos(50 + len(self.nodes), 50 + len(self.nodes))
        else:
            node_item.setPos(pos)
        self.addItem(node_item)
        self.nodes[new_stage.id] = node_item
        self.recompute_all()
        return node_item

    def remove_node(self, node_item: NodeItem) -> None:
        # remove edges touching this node
        to_remove = [edge for edge in self.edges if edge.src_node is node_item or edge.dst_node is node_item]
        for edge in to_remove:
            if edge in self.edges:
                self.removeItem(edge)
                self.edges.remove(edge)
        # detach children upstream references
        for n in self.nodes.values():
            if n.stage.upstream == node_item.stage.id:
                n.stage.upstream = None
        # remove node itself
        if node_item.stage.id in self.nodes:
            del self.nodes[node_item.stage.id]
        self.removeItem(node_item)
        self.recompute_all()

    def delete_selected(self) -> None:
        for item in list(self.selectedItems()):
            nd = self._find_node_from_item(item)
            if nd:
                self.remove_node(nd)
        self.recompute_all()

    def add_edge(self, src: NodeItem, dst: NodeItem) -> Optional[EdgeItem]:
        # validate
        if dst.stage.upstream is not None:
            QMessageBox.warning(None, "Connection", "Destination node already has an upstream connection.")
            return None
        if src is dst:
            QMessageBox.warning(None, "Connection", "Cannot connect a node to itself.")
            return None
        if self._creates_cycle(src, dst):
            QMessageBox.warning(None, "Connection", "Connection would create a cycle.")
            return None
        dst.stage.upstream = src.stage.id
        edge = EdgeItem(src, dst)
        self.addItem(edge)
        self.edges.append(edge)
        self.recompute_all()
        return edge

    def _creates_cycle(self, src: NodeItem, dst: NodeItem) -> bool:
        # follow upstream chain from src; if we reach dst, a cycle would be formed
        current = src
        visited = set()
        while current and current.stage.upstream:
            upid = current.stage.upstream
            if upid in visited:
                break
            visited.add(upid)
            upnode = self.nodes.get(upid)
            if upnode is None:
                break
            if upnode.stage.id == dst.stage.id:
                return True
            current = upnode
        return False

    def update_edges(self) -> None:
        for edge in self.edges:
            edge.update_path()
        if self.temp_edge:
            self.temp_edge.update()

    # ---------- selection handling ----------
    def on_selection_changed(self) -> None:
        items = self.selectedItems()
        node_item: Optional[NodeItem] = None
        if items:
            node_item = self._find_node_from_item(items[0])
        self.mainwindow.inspector.set_node(node_item)

    def _find_node_from_item(self, item) -> Optional[NodeItem]:
        it = item
        while it is not None and not isinstance(it, NodeItem):
            it = it.parentItem()
        return it if isinstance(it, NodeItem) else None

    # ---------- event handling for connect-by-drag ----------
    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        clicked_output = None
        clicked_input = None
        for node_item in self.nodes.values():
            if (pos - node_item.output_port_pos()).manhattanLength() <= PORT_RADIUS * 1.5:
                clicked_output = node_item
                break
            if (pos - node_item.input_port_pos()).manhattanLength() <= PORT_RADIUS * 1.5:
                clicked_input = node_item
                break
        if clicked_output:
            # start connecting
            self.is_connecting = True
            self.connect_source = clicked_output
            self.temp_edge = QGraphicsPathItem()
            pen = QPen(Qt.DashLine)
            pen.setWidth(2)
            self.temp_edge.setPen(pen)
            self.addItem(self.temp_edge)
            self._update_temp_edge(pos)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if self.is_connecting and self.temp_edge and self.connect_source:
            pos = event.scenePos()
            self._update_temp_edge(pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        if self.is_connecting and self.connect_source:
            destination = None
            for node_item in self.nodes.values():
                if (pos - node_item.input_port_pos()).manhattanLength() <= PORT_RADIUS * 1.5:
                    destination = node_item
                    break
            if destination:
                self.add_edge(self.connect_source, destination)
            # cleanup temporary edge
            if self.temp_edge:
                try:
                    self.removeItem(self.temp_edge)
                except Exception:
                    pass
                self.temp_edge = None
            self.is_connecting = False
            self.connect_source = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _update_temp_edge(self, pos: QPointF) -> None:
        if not (self.temp_edge and self.connect_source):
            return
        p1 = self.connect_source.output_port_pos()
        p2 = pos
        path = QPainterPath(p1)
        dx = (p2.x() - p1.x()) * 0.5
        c1 = QPointF(p1.x() + dx, p1.y())
        c2 = QPointF(p2.x() - dx, p2.y())
        path.cubicTo(c1, c2, p2)
        self.temp_edge.setPath(path)

    # compute depth (maximum series stages starting from node)
    def depth(self, node_item: NodeItem) -> int:
        children = [n for n in self.nodes.values() if n.stage.upstream == node_item.stage.id]
        if not children:
            return 1
        return 1 + max(self.depth(child) for child in children)

    # ---------- recompute / topology ----------
    def recompute_all(self) -> None:
        """Main recompute loop: evaluate topology depth and run several compute passes."""
        # compute maximum chain length (depth) starting from every INPUT (source)
        max_depth = 0
        for node_item in self.nodes.values():
            if node_item.stage.stage_type.upper() == "INPUT":
                max_depth = max(max_depth, self.depth(node_item))

        # perform a number of passes proportional to depth
        for _pass in range(max(1, max_depth)):
            # first compute requested currents (dependent on children's i_in)
            self.compute_requested_currents()

            # topological compute order using Kahn's algorithm
            incoming_count: Dict[str, int] = {nid: 0 for nid in self.nodes}
            for n_item in self.nodes.values():
                if n_item.stage.upstream:
                    incoming_count[n_item.stage.id] += 1

            work_stack = [n for n in self.nodes.values() if incoming_count[n.stage.id] == 0]
            order: List[NodeItem] = []
            visited = set()
            while work_stack:
                current = work_stack.pop()
                order.append(current)
                visited.add(current.stage.id)
                for neighbor in self.nodes.values():
                    if neighbor.stage.upstream == current.stage.id:
                        incoming_count[neighbor.stage.id] -= 1
                        if incoming_count[neighbor.stage.id] == 0 and neighbor.stage.id not in visited:
                            work_stack.append(neighbor)

            # append any nodes not in order (disconnected)
            ordered_ids = {x.stage.id for x in order}
            for n_item in self.nodes.values():
                if n_item.stage.id not in ordered_ids:
                    order.append(n_item)

            # compute each node using upstream vout if available
            for node_item in order:
                upstream_vout = None
                if node_item.stage.upstream:
                    upstream_node = self.nodes.get(node_item.stage.upstream)
                    if upstream_node:
                        upstream_vout = upstream_node.stage.vout
                node_item.stage.compute(upstream_vout)
                node_item.refresh_text()

            # check INPUT nodes for supply current limits (sum of direct children requests)
            for node_item in self.nodes.values():
                if node_item.stage.stage_type.upper() == 'INPUT':
                    total_request = 0.0
                    for child in self.nodes.values():
                        if child.stage.upstream == node_item.stage.id:
                            total_request += child.stage.iout_user
                    if total_request > node_item.stage.iout_max_ic:
                        node_item.stage.errors.append(f"[{node_item.stage.name}] Total load {total_request:.3g} A > source Imax {node_item.stage.iout_max_ic:.3g} A")
                        node_item.refresh_text()
                    else : 
                        if total_request > node_item.stage.iout_max_ic*0.9:
                            node_item.stage.errors.append(f"[{node_item.stage.name}] Total load {total_request:.3g} A is close to source Imax {node_item.stage.iout_max_ic:.3g} A")
                            node_item.refresh_text()

            # update visuals
            self.update_edges()
            self.mainwindow.refresh_errors()

    # ---------- persistence (save / load) ----------
    def serialize(self) -> Dict:
        return {
            "nodes": [
                {"stage": node_item.stage.to_dict(), "pos": [float(node_item.pos().x()), float(node_item.pos().y())]} for node_item in self.nodes.values()
            ],
            "edges": [{"src": e.src_node.stage.id, "dst": e.dst_node.stage.id} for e in self.edges]
        }

    def deserialize(self, data: Dict) -> None:
        # clear existing items
        for item in list(self.items()):
            self.removeItem(item)
        self.nodes.clear()
        self.edges.clear()
        # recreate nodes
        for nd in data.get("nodes", []):
            st = PowerStage.from_dict(nd["stage"])
            node_item = NodeItem(st)
            node_item.setPos(QtCore.QPointF(*nd.get("pos", [0, 0])))
            self.addItem(node_item)
            self.nodes[st.id] = node_item
        # recreate edges
        for ed in data.get("edges", []):
            src = self.nodes.get(ed["src"])
            dst = self.nodes.get(ed["dst"])
            if src and dst:
                dst.stage.upstream = src.stage.id
                edge = EdgeItem(src, dst)
                self.addItem(edge)
                self.edges.append(edge)
        self.recompute_all()