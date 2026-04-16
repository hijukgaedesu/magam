"""진행 중인 마감 목록 패널"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QButtonGroup, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

from ..i18n import t
from ..utils import days_left
from .project_card import ProjectCard


CATEGORIES = ["전체", "개인작", "커미션", "웹툰", "일러스트", "기타"]


class ProjectList(QWidget):
    data_changed = Signal()

    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self._cat_filter = t("전체")
        self._build()

    def _build(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(8)

        # ── 헤더 ─────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("■ " + t("진행 중인 마감"))
        title.setStyleSheet(
            f"font-size: 14px; font-weight: 800; color: {self.T['text']};"
            f" background: transparent;")
        hdr.addWidget(title)
        sub = QLabel(t("임박순"))
        sub.setStyleSheet(
            f"font-size: 11px; color: {self.T['muted']}; background: transparent;")
        hdr.addWidget(sub)
        hdr.addStretch()
        vbox.addLayout(hdr)

        # ── 카테고리 필터 버튼 ─────────────────────────────
        self._cat_bar_widget = QWidget()
        self._cat_bar_widget.setStyleSheet("background: transparent;")
        self._cat_bar = QHBoxLayout(self._cat_bar_widget)
        self._cat_bar.setContentsMargins(0, 0, 0, 0)
        self._cat_bar.setSpacing(4)
        vbox.addWidget(self._cat_bar_widget)
        self._rebuild_cat_buttons()

        # ── 스크롤 가능한 카드 목록 ───────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background: transparent; border: none;")
        scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._cards_widget = QWidget()
        self._cards_widget.setStyleSheet("background: transparent;")
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()

        scroll.setWidget(self._cards_widget)
        vbox.addWidget(scroll)

        self._populate_cards()

    def _rebuild_cat_buttons(self) -> None:
        while self._cat_bar.count():
            item = self._cat_bar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        used_cats = {p.get("category", "") for p in
                     self.data.get("projects", [])} - {""}
        show_cats = [t("전체")] + [
            t(c) for c in CATEGORIES[1:] if c in used_cats
        ] + [c for c in used_cats if c not in CATEGORIES]

        for cat in show_cats:
            is_active = (self._cat_filter == cat)
            btn = QPushButton(cat)
            btn.setFixedHeight(24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.T['accent'] if is_active else self.T['accent_light']};
                    color: {'white' if is_active else self.T['text']};
                    border: none;
                    border-radius: 12px;
                    padding: 0 10px;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {self.T['accent']};
                    color: white;
                }}
            """)
            btn.clicked.connect(lambda checked=False, c=cat: self._set_filter(c))
            self._cat_bar.addWidget(btn)
        self._cat_bar.addStretch()

    def _set_filter(self, cat: str) -> None:
        self._cat_filter = cat
        self._rebuild_cat_buttons()
        self._populate_cards()

    def _populate_cards(self) -> None:
        # 기존 카드 제거 (stretch는 유지)
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_projs = self.data.get("projects", [])

        # 카테고리 필터
        if self._cat_filter == t("전체"):
            filtered = list(enumerate(all_projs))
        else:
            filtered = [
                (i, p) for i, p in enumerate(all_projs)
                if p.get("category", "") == self._cat_filter
            ]

        # 활성(진행 중) 프로젝트만
        active = [
            (i, p) for i, p in filtered
            if not all(p.get("steps", []))
        ]

        if not filtered:
            lbl = self._empty_label(
                "—",
                t("아직 마감이 없어요\n상단 [+ 마감 추가]를 눌러봐요 🌸")
            )
            self._cards_layout.insertWidget(0, lbl)
            return

        if not active:
            lbl = self._empty_label(
                "✓",
                t("진행 중인 마감이 없어요!\n완료 마감은 📈 통계에서 확인하세요.")
            )
            self._cards_layout.insertWidget(0, lbl)
            return

        # 임박순 정렬
        sorted_active = sorted(active,
                               key=lambda x: days_left(x[1].get("deadline", "9999-12-31")))

        for insert_pos, (orig_idx, _) in enumerate(sorted_active):
            card = ProjectCard(self.T, self.data, orig_idx)
            card.data_changed.connect(self._on_card_changed)
            self._cards_layout.insertWidget(insert_pos, card)

    def _empty_label(self, icon: str, msg: str) -> QWidget:
        w = QFrame()
        w.setObjectName("card")
        w.setStyleSheet(f"""
            QFrame#card {{
                background: {self.T['card']};
                border-radius: 18px;
                border: 1px solid {self.T['accent_light']};
            }}
        """)
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(24, 24, 24, 24)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 36px; background: transparent;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(icon_lbl)

        msg_lbl = QLabel(msg)
        msg_lbl.setStyleSheet(
            f"font-size: 13px; color: {self.T['muted']}; background: transparent;")
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(msg_lbl)
        return w

    def _on_card_changed(self) -> None:
        self.data_changed.emit()
        self.refresh()

    def refresh(self) -> None:
        self._rebuild_cat_buttons()
        self._populate_cards()
