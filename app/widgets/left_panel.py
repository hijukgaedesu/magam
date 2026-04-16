"""좌측 메인 패널 — 통계 카드 · 캘린더 · 프로젝트 목록 · 작업량"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

from .stats_cards import StatsCards
from .calendar_widget import CalendarWidget
from .project_list import ProjectList
from .work_log_panel import WorkLogPanel
from .hero_banner import HeroBanner


class LeftPanel(QWidget):
    data_changed = Signal()

    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: {self.T['bg']};")

        content = QWidget()
        content.setObjectName("leftScrollContent")
        content.setStyleSheet(f"background: {self.T['bg']};")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(0, 0, 0, 32)
        vbox.setSpacing(0)

        # ── 히어로 배너 ────────────────────────────────────
        self.hero_banner = HeroBanner(self.T, self.data)
        vbox.addWidget(self.hero_banner)

        # ── 나머지 콘텐츠 ──────────────────────────────────
        inner = QWidget()
        inner.setStyleSheet(f"background: {self.T['bg']};")
        inner_vbox = QVBoxLayout(inner)
        inner_vbox.setContentsMargins(24, 16, 24, 0)
        inner_vbox.setSpacing(16)

        # ── 통계 카드 4개 ──────────────────────────────────
        self.stats_cards = StatsCards(self.T, self.data)
        inner_vbox.addWidget(self.stats_cards)

        # ── 캘린더 (좌) + 프로젝트 목록 (우) ──────────────
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        self.calendar_widget = CalendarWidget(self.T, self.data)
        self.calendar_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        mid_row.addWidget(self.calendar_widget, 55)

        self.project_list = ProjectList(self.T, self.data)
        self.project_list.data_changed.connect(self.data_changed)
        self.project_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mid_row.addWidget(self.project_list, 45)

        inner_vbox.addLayout(mid_row)

        # ── 작업량 패널 ───────────────────────────────────
        self.work_log = WorkLogPanel(self.T, self.data)
        self.work_log.data_changed.connect(self.data_changed)
        inner_vbox.addWidget(self.work_log)

        inner_vbox.addStretch()
        vbox.addWidget(inner)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def refresh(self) -> None:
        self.stats_cards.refresh()
        self.calendar_widget.refresh()
        self.project_list.refresh()
        self.work_log.refresh()
