"""히어로 배너 — 좌측 패널 최상단 이미지 배너"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QWidget, QPushButton, QFileDialog
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont

from ..i18n import t
from ..data import save_data


class HeroBanner(QWidget):
    """클릭하면 이미지 선택, 이미지 있으면 배너로 표시. ×로 제거."""

    HEIGHT = 90

    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T    = T
        self.data = data
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pix: QPixmap | None = None
        self._load()

        # × 버튼
        self._del_btn = QPushButton("×", self)
        self._del_btn.setFixedSize(22, 22)
        self._del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._del_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0,0,0,0.45);
                color: white;
                border: none;
                border-radius: 11px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover { background: rgba(0,0,0,0.7); }
        """)
        self._del_btn.clicked.connect(self._clear)
        self._del_btn.setVisible(self._pix is not None)

    def resizeEvent(self, event) -> None:
        self._del_btn.move(self.width() - 28, 6)

    def _load(self) -> None:
        path = self.data.get("header_image", "")
        if path and Path(path).exists():
            pix = QPixmap(path)
            self._pix = pix if not pix.isNull() else None
        else:
            self._pix = None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pick()

    def _pick(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("헤더 이미지 선택"), "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self.data["header_image"] = path
            save_data(self.data)
            self._load()
            self._del_btn.setVisible(self._pix is not None)
            self.update()

    def _clear(self) -> None:
        self.data.pop("header_image", None)
        save_data(self.data)
        self._pix = None
        self._del_btn.setVisible(False)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._pix:
            scaled = self._pix.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            ox = (scaled.width()  - self.width())  // 2
            oy = (scaled.height() - self.height()) // 2
            painter.drawPixmap(-ox, -oy, scaled)
            # 하단 그라데이션 페이드
            from PySide6.QtGui import QLinearGradient
            grad = QLinearGradient(0, self.height() * 0.5, 0, self.height())
            grad.setColorAt(0, QColor(0, 0, 0, 0))
            grad.setColorAt(1, QColor(0, 0, 0, 60))
            painter.fillRect(self.rect(), grad)
        else:
            # 플레이스홀더
            painter.fillRect(self.rect(), QColor(self.T["accent_light"]))
            painter.setPen(QColor(self.T["muted"]))
            font = QFont()
            font.setPixelSize(13)
            painter.setFont(font)
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter,
                t("🖼  클릭하여 헤더 이미지 추가"),
            )

        painter.end()
