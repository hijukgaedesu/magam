"""스티커 레이어 — 스크롤 콘텐츠에 붙는 PNG 스티커"""
from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QDialog, QFileDialog, QSlider,
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QPainter, QColor

from ..data import save_data
from ..i18n import t


# ──────────────────────────────────────────────────────────────────────────────
# 개별 스티커 아이템
# ──────────────────────────────────────────────────────────────────────────────
class _StickerItem(QWidget):
    """드래그·더블클릭(크기/회전)·우클릭(삭제) 가능한 PNG 스티커
    parent는 스크롤 콘텐츠 위젯 → 스크롤하면 함께 움직임"""

    def __init__(self, sid: str, img_path: str,
                 x: int, y: int, size: int, rotation: float,
                 manager: "StickerManager", parent: QWidget) -> None:
        super().__init__(parent)
        self.sid       = sid
        self.img_path  = img_path
        self._size     = size
        self._rotation = rotation   # 0 ~ 360 도
        self._manager  = manager
        self._drag_pos = QPoint()

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 회전 여백을 위해 위젯 크기를 대각선 길이로 확보
        self._widget_size = int(size * 1.5)
        self.setFixedSize(self._widget_size, self._widget_size)
        self.move(x, y)
        self.raise_()
        self.show()

        self._pix = self._load_pix(img_path, size)

    @staticmethod
    def _load_pix(path: str, size: int) -> QPixmap | None:
        if not path or not Path(path).exists():
            return None
        pix = QPixmap(path)
        if pix.isNull():
            return None
        return pix.scaled(size, size,
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)

    # ── 렌더링 ────────────────────────────────────────────
    def paintEvent(self, _) -> None:
        if not self._pix:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 위젯 중심 기준으로 회전
        cx = self.width()  / 2
        cy = self.height() / 2
        p.translate(cx, cy)
        p.rotate(self._rotation)
        p.translate(-self._pix.width() / 2, -self._pix.height() / 2)
        p.drawPixmap(0, 0, self._pix)
        p.end()

    # ── 마우스 이벤트 ─────────────────────────────────────
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.position().toPoint()
            self.raise_()
        elif event.button() == Qt.MouseButton.RightButton:
            self._manager.remove(self.sid)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.position().toPoint() - self._drag_pos
            new_pos = self.pos() + delta
            parent = self.parentWidget()
            if parent:
                new_pos.setX(max(0, min(new_pos.x(), parent.width()  - self.width())))
                new_pos.setY(max(0, min(new_pos.y(), parent.height() - self.height())))
            self.move(new_pos)

    def mouseDoubleClickEvent(self, _) -> None:
        self._open_adjust()

    # ── 크기·회전 조절 팝업 ──────────────────────────────
    def _open_adjust(self) -> None:
        dlg = _AdjustDialog(self._size, self._rotation, self.parentWidget())
        if dlg.exec():
            new_size, new_rotation = dlg.get_values()
            self._rotation = new_rotation
            if new_size != self._size:
                self._size = new_size
                self._pix  = self._load_pix(self.img_path, new_size)
                self._widget_size = int(new_size * 1.5)
                self.setFixedSize(self._widget_size, self._widget_size)
            self._manager.update_item(self.sid, new_size, new_rotation)
            self.update()

    def get_state(self) -> dict:
        return {
            "id": self.sid, "path": self.img_path,
            "x": self.x(), "y": self.y(),
            "size": self._size, "rotation": self._rotation,
        }


# ──────────────────────────────────────────────────────────────────────────────
# 크기·회전 조절 다이얼로그
# ──────────────────────────────────────────────────────────────────────────────
class _AdjustDialog(QDialog):
    def __init__(self, size: int, rotation: float, parent=None) -> None:
        super().__init__(parent,
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._size     = size
        self._rotation = rotation
        self._build()

    def _build(self) -> None:
        self.setFixedWidth(220)
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(8)

        self.setStyleSheet("""
            QDialog {
                background: white;
                border-radius: 12px;
                border: 1px solid #ddd;
            }
            QLabel { background: transparent; font-size: 11px; color: #555; }
            QSlider::groove:horizontal {
                height: 4px; background: #eee; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 14px; height: 14px; margin: -5px 0;
                border-radius: 7px; background: #9b7fe8;
            }
            QSlider::sub-page:horizontal { background: #9b7fe8; border-radius: 2px; }
        """)

        # 크기 슬라이더
        size_lbl = QLabel(f"크기: {self._size}px")
        vbox.addWidget(size_lbl)
        self._size_slider = QSlider(Qt.Orientation.Horizontal)
        self._size_slider.setRange(30, 200)
        self._size_slider.setValue(self._size)
        self._size_slider.valueChanged.connect(
            lambda v: size_lbl.setText(f"크기: {v}px"))
        vbox.addWidget(self._size_slider)

        # 회전 슬라이더
        rot_lbl = QLabel(f"회전: {int(self._rotation)}°")
        vbox.addWidget(rot_lbl)
        self._rot_slider = QSlider(Qt.Orientation.Horizontal)
        self._rot_slider.setRange(0, 360)
        self._rot_slider.setValue(int(self._rotation))
        self._rot_slider.valueChanged.connect(
            lambda v: rot_lbl.setText(f"회전: {v}°"))
        vbox.addWidget(self._rot_slider)

        # 버튼
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("✓ 적용")
        ok_btn.setFixedHeight(28)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #9b7fe8; color: white;
                border: none; border-radius: 8px;
                font-size: 11px; font-weight: 700;
            }
            QPushButton:hover { background: #7a5fc8; }
        """)
        ok_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("취소")
        cancel_btn.setFixedHeight(28)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #eee; color: #555;
                border: none; border-radius: 8px;
                font-size: 11px;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        vbox.addLayout(btn_row)

    def get_values(self) -> tuple[int, float]:
        return self._size_slider.value(), float(self._rot_slider.value())

    def paintEvent(self, _) -> None:
        from PySide6.QtGui import QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        p.fillPath(path, QColor("white"))
        p.end()


# ──────────────────────────────────────────────────────────────────────────────
# 스티커 매니저
# ──────────────────────────────────────────────────────────────────────────────
class StickerManager:
    """스티커를 스크롤 콘텐츠 위젯 위에 붙여 스크롤과 함께 움직이게 함"""

    def __init__(self, T: dict, data: dict, parent_window: QWidget) -> None:
        self.T       = T
        self.data    = data
        self._window = parent_window
        # 스크롤 콘텐츠 위젯을 찾아서 parent로 사용 → 스크롤 시 함께 이동
        self._parent = self._find_scroll_content(parent_window) or parent_window
        self._items: dict[str, _StickerItem] = {}
        self._load_saved()

    @staticmethod
    def _find_scroll_content(window: QWidget) -> QWidget | None:
        """LeftPanel의 스크롤 콘텐츠 위젯을 objectName으로 정확히 탐색"""
        for child in window.findChildren(QWidget):
            if child.objectName() == "leftScrollContent":
                return child
        return None

    def _load_saved(self) -> None:
        for s in self.data.get("stickers", []):
            self._create(s["id"], s["path"], s["x"], s["y"],
                         s.get("size", 80), s.get("rotation", 0.0))

    def _create(self, sid: str, path: str,
                x: int, y: int, size: int, rotation: float) -> None:
        item = _StickerItem(sid, path, x, y, size, rotation, self, self._parent)
        self._items[sid] = item

    def open_picker(self, parent=None) -> None:
        path, _ = QFileDialog.getOpenFileName(
            parent or self._window,
            t("스티커 이미지 선택 (PNG 권장)"), "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not path:
            return
        sid  = str(uuid.uuid4())[:8]
        # 스크롤 콘텐츠 기준 중앙에 배치
        x = max(0, self._parent.width()  // 2 - 40)
        y = max(0, self._parent.height() // 2 - 40)
        size, rotation = 80, 0.0
        self._create(sid, path, x, y, size, rotation)
        self.data.setdefault("stickers", []).append({
            "id": sid, "path": path,
            "x": x, "y": y, "size": size, "rotation": rotation,
        })
        save_data(self.data)

    def remove(self, sid: str) -> None:
        if sid in self._items:
            self._items[sid].close()
            self._items[sid].deleteLater()
            del self._items[sid]
        self.data["stickers"] = [
            s for s in self.data.get("stickers", []) if s["id"] != sid
        ]
        save_data(self.data)

    def update_item(self, sid: str, size: int, rotation: float) -> None:
        for s in self.data.get("stickers", []):
            if s["id"] == sid:
                s["size"]     = size
                s["rotation"] = rotation
                break
        save_data(self.data)

    def save_positions(self) -> None:
        stickers = self.data.get("stickers", [])
        for s in stickers:
            item = self._items.get(s["id"])
            if item:
                s["x"], s["y"] = item.x(), item.y()
        save_data(self.data)

    def close_all(self) -> None:
        self.save_positions()
        for item in list(self._items.values()):
            item.close()
            item.deleteLater()
        self._items.clear()
