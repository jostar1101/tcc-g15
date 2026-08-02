import json
from typing import List, Optional, Tuple
from PySide6 import QtCore, QtGui, QtWidgets
from GUI.AppColors import Colors

CurvePoint = Tuple[float, float]

class FanCurveWidget(QtWidgets.QWidget):
    curveChanged = QtCore.Signal()

    MARGIN_L = 46
    MARGIN_R = 14
    MARGIN_T = 14
    MARGIN_B = 32

    TEMP_MIN = 35
    TEMP_MAX = 100
    RPM_MIN = 0
    RPM_MAX = 100

    DEFAULT_CURVE: List[CurvePoint] = [
        (35.0, 45.0), (37.5, 49.5), (40.0, 53.8), (42.5, 57.9), (45.0, 61.8),
        (47.5, 65.5), (50.0, 69.1), (52.5, 72.4), (55.0, 75.6), (57.5, 78.5),
        (60.0, 81.3), (62.5, 83.9), (65.0, 86.3), (67.5, 88.5), (70.0, 90.5),
        (72.5, 92.3), (75.0, 93.9), (77.5, 95.3), (80.0, 96.6), (82.5, 97.6),
        (85.0, 98.5), (87.5, 99.1), (90.0, 99.6), (92.5, 99.9), (95.0, 100.0)
    ]

    _DRAG_RADIUS = 12

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(440, 280)
        self.setMouseTracking(True)
        self._curve: List[List[float]] = [list(p) for p in self.DEFAULT_CURVE]
        self._dragIdx = -1
        self._hoverIdx = -1

    # ---- public API ----

    def setCurve(self, curve: List[CurvePoint]) -> None:
        pts = sorted((float(x), float(y)) for x, y in curve)
        self._curve = [list(p) for p in pts]
        self.update()

    def getCurve(self) -> List[CurvePoint]:
        return [(x, y) for x, y in self._curve]

    def lookup(self, temp: float) -> float:
        pts = self._curve
        if not pts:
            return 0.0
        if temp <= pts[0][0]:
            return pts[0][1]
        if temp >= pts[-1][0]:
            return pts[-1][1]
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            if temp <= x1:
                if x1 == x0:
                    return y1
                return y0 + (temp - x0) * (y1 - y0) / (x1 - x0)
        return pts[-1][1]

    # ---- geometry helpers ----

    def _plotRect(self) -> QtCore.QRectF:
        w = self.width() - self.MARGIN_L - self.MARGIN_R
        h = self.height() - self.MARGIN_T - self.MARGIN_B
        return QtCore.QRectF(self.MARGIN_L, self.MARGIN_T, w, h)

    def _toWidget(self, temp: float, rpm: float) -> QtCore.QPointF:
        r = self._plotRect()
        x = r.left() + (temp - self.TEMP_MIN) / (self.TEMP_MAX - self.TEMP_MIN) * r.width()
        y = r.bottom() - (rpm - self.RPM_MIN) / (self.RPM_MAX - self.RPM_MIN) * r.height()
        return QtCore.QPointF(x, y)

    def _toPlot(self, pt: QtCore.QPointF) -> Tuple[float, float]:
        r = self._plotRect()
        temp = self.TEMP_MIN + (pt.x() - r.left()) / r.width() * (self.TEMP_MAX - self.TEMP_MIN)
        rpm = self.RPM_MIN + (r.bottom() - pt.y()) / r.height() * (self.RPM_MAX - self.RPM_MIN)
        return (temp, rpm)

    # ---- events ----

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        p.fillRect(self.rect(), QtGui.QColor(Colors.DARK_GREY.value))

        r = self._plotRect()
        p.fillRect(r, QtGui.QColor(Colors.BLACK.value))
        p.setPen(QtGui.QPen(QtGui.QColor(Colors.GREY.value), 1))
        p.drawRect(r)

        # Grid lines and labels
        font = QtGui.QFont("Consolas", 7)
        p.setFont(font)
        for temp in range(self.TEMP_MIN, self.TEMP_MAX + 1, 5):
            x = self._toWidget(float(temp), 0).x()
            p.setPen(QtGui.QPen(QtGui.QColor(Colors.GREY.value), 1, QtCore.Qt.DashLine))
            p.drawLine(QtCore.QPointF(x, r.top()), QtCore.QPointF(x, r.bottom()))
            p.setPen(QtGui.QColor(Colors.WHITE.value))
            p.drawText(QtCore.QRectF(x - 20, r.bottom() + 6, 40, 14), QtCore.Qt.AlignHCenter, str(temp))
        for rpm in range(self.RPM_MIN, self.RPM_MAX + 1, 10):
            y = self._toWidget(0, float(rpm)).y()
            p.setPen(QtGui.QPen(QtGui.QColor(Colors.GREY.value), 1, QtCore.Qt.DashLine))
            p.drawLine(QtCore.QPointF(r.left(), y), QtCore.QPointF(r.right(), y))
            p.setPen(QtGui.QColor(Colors.WHITE.value))
            p.drawText(QtCore.QRectF(0, y - 7, self.MARGIN_L - 6, 14), QtCore.Qt.AlignRight, str(rpm))

        p.setPen(QtGui.QColor(Colors.WHITE.value))
        p.drawText(QtCore.QRectF(0, 0, self.width(), 12), QtCore.Qt.AlignHCenter, "Fan speed, %")
        p.drawText(QtCore.QRectF(0, self.height() - 14, self.width(), 12), QtCore.Qt.AlignHCenter, "Temperature, C")

        # Curve
        pts = [self._toWidget(x, y) for x, y in self._curve]
        if pts:
            path = QtGui.QPainterPath(pts[0])
            for pt in pts[1:]:
                path.lineTo(pt)
            p.setPen(QtGui.QPen(QtGui.QColor(Colors.GREEN.value), 3))
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawPath(path)

        # Control points
        for i, (x, y) in enumerate(self._curve):
            pt = self._toWidget(x, y)
            rPt = 6 if i == self._hoverIdx or i == self._dragIdx else 4
            p.setBrush(QtGui.QColor(Colors.BLUE.value))
            p.setPen(QtGui.QPen(QtGui.QColor(Colors.WHITE.value), 1))
            p.drawEllipse(pt, rPt, rPt)

        # Highlight point under cursor
        if self._hoverIdx >= 0:
            pt = self._toWidget(*self._curve[self._hoverIdx])
            p.setPen(QtGui.QPen(QtGui.QColor(Colors.YELLOW.value), 1, QtCore.Qt.DashLine))
            p.drawLine(QtCore.QPointF(pt.x(), self._plotRect().top()), QtCore.QPointF(pt.x(), self._plotRect().bottom()))
            p.drawLine(QtCore.QPointF(self._plotRect().left(), pt.y()), QtCore.QPointF(self._plotRect().right(), pt.y()))

        p.end()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            idx = self._nearestPointIndex(event.position())
            if idx >= 0:
                self._dragIdx = idx
                self.update()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        idx = self._nearestPointIndex(event.position())
        if idx != self._hoverIdx:
            self._hoverIdx = idx
            self.update()
        if self._dragIdx >= 0:
            temp, rpm = self._toPlot(event.position())
            temp = max(self.TEMP_MIN, min(self.TEMP_MAX, temp))
            rpm = max(self.RPM_MIN, min(self.RPM_MAX, rpm))
            # Keep X order: clamp temp between neighbors
            lo = self._curve[self._dragIdx - 1][0] + 0.5 if self._dragIdx > 0 else self.TEMP_MIN
            hi = self._curve[self._dragIdx + 1][0] - 0.5 if self._dragIdx < len(self._curve) - 1 else self.TEMP_MAX
            self._curve[self._dragIdx] = [max(lo, min(hi, temp)), rpm]
            self.update()
            self.curveChanged.emit()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self._dragIdx = -1
            self.update()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton and self._nearestPointIndex(event.position()) < 0:
            temp, rpm = self._toPlot(event.position())
            temp = max(self.TEMP_MIN, min(self.TEMP_MAX, temp))
            rpm = max(self.RPM_MIN, min(self.RPM_MAX, rpm))
            self._curve.append([temp, rpm])
            self._curve.sort(key=lambda p: p[0])
            self.update()
            self.curveChanged.emit()

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        if len(self._curve) <= 2:
            return
        idx = self._nearestPointIndex(event.pos())
        if idx < 0:
            return
        menu = QtWidgets.QMenu(self)
        act = menu.addAction("Remove point")
        if menu.exec(event.globalPos()) == act:
            del self._curve[idx]
            self.update()
            self.curveChanged.emit()

    # ---- helpers ----

    def _nearestPointIndex(self, pt: QtCore.QPointF) -> int:
        bestIdx = -1
        bestDist = self._DRAG_RADIUS
        for i, (x, y) in enumerate(self._curve):
            wpt = self._toWidget(x, y)
            d = (wpt - pt).manhattanLength()
            if d <= bestDist:
                bestDist = d
                bestIdx = i
        return bestIdx

class FanCurveDialog(QtWidgets.QDialog):
    def __init__(self, parent: Optional[QtWidgets.QWidget], curve: List[CurvePoint]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Fan curve editor")
        self.setModal(True)

        self._curveWidget = FanCurveWidget()
        self._curveWidget.setCurve(curve)
        hint = QtWidgets.QLabel("Drag points to shape the curve. Double-click to add, right-click to remove.")
        hint.setStyleSheet("color: gray;")

        resetBtn = QtWidgets.QPushButton("Reset default")
        resetBtn.clicked.connect(lambda: self._curveWidget.setCurve(FanCurveWidget.DEFAULT_CURVE))
        okBtn = QtWidgets.QPushButton("OK")
        okBtn.clicked.connect(self.accept)

        btnBox = QtWidgets.QHBoxLayout()
        btnBox.addWidget(resetBtn)
        btnBox.addStretch(1)
        btnBox.addWidget(okBtn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self._curveWidget)
        layout.addLayout(btnBox)

    def getCurve(self) -> List[CurvePoint]:
        return self._curveWidget.getCurve()
