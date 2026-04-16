"""상단 헤더 바"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor

from ..i18n import t, _translations


class HeaderBar(QWidget):
    add_clicked      = Signal()
    stats_clicked    = Signal()
    archive_clicked  = Signal()
    income_clicked   = Signal()
    settings_clicked = Signal()
    sticker_clicked  = Signal()

    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T    = T
        self.data = data
        self._build()

    # ── 빌드 ─────────────────────────────────────────────
    def _build(self) -> None:
        self.setFixedHeight(58)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 0, 16, 0)
        layout.setSpacing(8)

        # 앱 이름 (좌측)
        title = QLabel("0w0 Deadline Tracker")
        title.setStyleSheet(
            "color: white; font-size: 16px; font-weight: 800;"
            "background: transparent; letter-spacing: 0.5px;"
        )
        layout.addWidget(title)
        layout.addStretch()

        # 날짜 pill
        now = datetime.now()
        _dow_list = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        dow = t(_dow_list[now.weekday()])
        fmt = _translations.get("_cal_month_fmt", "")
        if fmt:
            date_str = f"{now.month}/{now.day}"
        else:
            date_str = f"{now.month}월 {now.day}일"
        date_lbl = QLabel(f" {date_str}  {dow}  {now.year} ")
        date_lbl.setStyleSheet(f"""
            background: rgba(255,255,255,0.9);
            color: {self.T['accent']};
            font-size: 12px;
            font-weight: 700;
            border-radius: 14px;
            padding: 4px 12px;
        """)
        layout.addWidget(date_lbl)

        # + 마감 추가
        add_btn = self._hbtn(t("+ 마감 추가"), accent=True)
        add_btn.clicked.connect(self.add_clicked)
        layout.addWidget(add_btn)

        # 통계
        stats_btn = self._hbtn("▲ " + t("통계"))
        stats_btn.clicked.connect(self.stats_clicked)
        layout.addWidget(stats_btn)

        # 완료 아카이브
        archive_btn = self._hbtn("✓ " + t("완료"))
        archive_btn.clicked.connect(self.archive_clicked)
        layout.addWidget(archive_btn)

        # 커미션 수입
        if self.data.get("commission_mode", False):
            income_btn = self._hbtn("$ " + t("수입"))
            income_btn.clicked.connect(self.income_clicked)
            layout.addWidget(income_btn)

        # 스티커
        sticker_btn = self._hbtn("✿")
        sticker_btn.setFixedWidth(38)
        sticker_btn.setToolTip(t("스티커 추가"))
        sticker_btn.clicked.connect(self.sticker_clicked)
        layout.addWidget(sticker_btn)

        # 설정
        set_btn = self._hbtn("≡")
        set_btn.setFixedWidth(38)
        set_btn.clicked.connect(self.settings_clicked)
        layout.addWidget(set_btn)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self.T["sidebar"]))
        painter.end()

    def _hbtn(self, text: str, accent: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if accent:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: white;
                    color: {self.T['accent']};
                    border: none;
                    border-radius: 14px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 800;
                }}
                QPushButton:hover {{
                    background: {self.T['accent']};
                    color: white;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255,255,255,0.25);
                    color: {self.T['sidebar_text']};
                    border: none;
                    border-radius: 14px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: rgba(255,255,255,0.50);
                }}
            """)
        return btn

    def refresh(self) -> None:
        pass
