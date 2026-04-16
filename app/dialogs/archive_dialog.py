"""완료된 마감 아카이브 다이얼로그"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget, QScrollArea, QMessageBox,
)
from PySide6.QtCore import Qt, Signal

from ..i18n import t
from ..data import save_data


class ArchiveDialog(QDialog):
    data_changed = Signal()

    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self.setWindowTitle(t("📦 완료 아카이브"))
        self.setMinimumSize(420, 480)
        self.resize(460, 540)
        self._build()

    def _build(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: {self.T['bg']}; border: none;")

        self._content = QWidget()
        self._content.setStyleSheet(f"background: {self.T['bg']};")
        self._vbox = QVBoxLayout(self._content)
        self._vbox.setContentsMargins(20, 16, 20, 16)
        self._vbox.setSpacing(10)

        scroll.setWidget(self._content)
        vbox.addWidget(scroll)

        # 하단 버튼
        btn_frame = QFrame()
        btn_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.T['card']};
                border-top: 1px solid {self.T['accent_light']};
            }}
        """)
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(20, 10, 20, 12)
        close_btn = QPushButton(t("닫기"))
        close_btn.setObjectName("accent")
        close_btn.setFixedHeight(36)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        vbox.addWidget(btn_frame)

        self._refresh()

    def _refresh(self) -> None:
        # 기존 위젯 제거
        while self._vbox.count():
            item = self._vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        projs = self.data.get("projects", [])
        done_projs = [(i, p) for i, p in enumerate(projs)
                      if p.get("steps") and all(p.get("steps", []))]

        if not done_projs:
            empty = QLabel(t("완료된 마감이 없어요.\n마감을 완료하면 여기에 쌓여요! 🎉"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"font-size: 13px; color: {self.T['muted']}; background: transparent;"
                f" padding: 40px;")
            self._vbox.addWidget(empty)
        else:
            count_lbl = QLabel(t(f"총 {len(done_projs)}개 완료"))
            count_lbl.setStyleSheet(
                f"font-size: 11px; color: {self.T['muted']}; background: transparent;")
            self._vbox.addWidget(count_lbl)

            for orig_idx, p in done_projs:
                card = self._make_card(orig_idx, p)
                self._vbox.addWidget(card)

        self._vbox.addStretch()

    def _make_card(self, orig_idx: int, p: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"""
            QFrame#card {{
                background: {self.T['card']};
                border-radius: 14px;
                border: 1px solid {self.T['accent_light']};
            }}
        """)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(14, 12, 14, 12)
        vbox.setSpacing(6)

        # 상단: 이름 + 버튼들
        top = QHBoxLayout()

        name_lbl = QLabel(p.get("name", ""))
        name_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {self.T['text']};"
            f" background: transparent;")
        top.addWidget(name_lbl)
        top.addStretch()

        # 복원 버튼
        restore_btn = QPushButton(t("↩ 복원"))
        restore_btn.setFixedHeight(26)
        restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restore_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent_light']};
                color: {self.T['accent']};
                border: none;
                border-radius: 13px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {self.T['accent']};
                color: white;
            }}
        """)
        restore_btn.clicked.connect(lambda _, i=orig_idx: self._restore(i))
        top.addWidget(restore_btn)

        # 삭제 버튼
        del_btn = QPushButton(t("🗑 삭제"))
        del_btn.setFixedHeight(26)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: #fde8e8;
                color: {self.T['urgent']};
                border: none;
                border-radius: 13px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {self.T['urgent']};
                color: white;
            }}
        """)
        del_btn.clicked.connect(lambda _, i=orig_idx, n=p.get("name", ""): self._delete(i, n))
        top.addWidget(del_btn)

        vbox.addLayout(top)

        # 세부 정보
        details = []
        if p.get("category"):
            details.append(t(p["category"]))
        if p.get("deadline"):
            details.append(f"📅 {p['deadline']}")
        steps = p.get("steps", [])
        if steps:
            details.append(f"✅ {len(steps)}{t('단계 완료')}")
        if p.get("price"):
            details.append(f"💰 {p['price']:,.0f}{t('원')}")

        if details:
            detail_lbl = QLabel("  ·  ".join(details))
            detail_lbl.setStyleSheet(
                f"font-size: 11px; color: {self.T['muted']}; background: transparent;")
            vbox.addWidget(detail_lbl)

        if p.get("memo"):
            memo_lbl = QLabel(p["memo"][:80] + ("..." if len(p.get("memo", "")) > 80 else ""))
            memo_lbl.setStyleSheet(
                f"font-size: 11px; color: {self.T['muted']}; background: transparent;")
            memo_lbl.setWordWrap(True)
            vbox.addWidget(memo_lbl)

        return card

    def _restore(self, orig_idx: int) -> None:
        """완료 단계를 모두 미완료로 되돌려 활성 목록으로 복원"""
        projs = self.data.get("projects", [])
        if orig_idx < len(projs):
            projs[orig_idx]["steps"] = [False] * len(projs[orig_idx].get("steps", []))
            save_data(self.data)
            self.data_changed.emit()
            self._refresh()

    def _delete(self, orig_idx: int, name: str) -> None:
        reply = QMessageBox.question(
            self,
            t("삭제 확인"),
            f"'{name}' {t('을(를) 완전히 삭제할까요?\n되돌릴 수 없어요.')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            projs = self.data.get("projects", [])
            if orig_idx < len(projs):
                projs.pop(orig_idx)
                save_data(self.data)
                self.data_changed.emit()
                self._refresh()
