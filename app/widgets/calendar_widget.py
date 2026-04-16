"""마감 캘린더 위젯"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QDialog, QScrollArea, QProgressBar,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from ..i18n import t, fmt_month, dow_labels
from ..utils import days_left, urgency, pill_text


class CalendarWidget(QFrame):
    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self._cal_year  = date.today().year
        self._cal_month = date.today().month
        self._build()

    def _build(self) -> None:
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame#card {{
                background: {self.T['card']};
                border-radius: 18px;
                border: 1px solid {self.T['accent_light']};
            }}
        """)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(20, 16, 20, 16)
        vbox.setSpacing(10)

        # ── 헤더 ─────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("◈ " + t("마감 캘린더"))
        title.setStyleSheet(
            f"font-size: 14px; font-weight: 800; color: {self.T['text']};"
            f" background: transparent;")
        hdr.addWidget(title)
        hdr.addStretch()

        nav = QHBoxLayout()
        nav.setSpacing(4)
        prev_btn = QPushButton("‹")
        prev_btn.setFixedSize(QSize(30, 30))
        prev_btn.setStyleSheet(self._nav_btn_style())
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.clicked.connect(lambda: self._change_month(-1))
        nav.addWidget(prev_btn)

        self._month_lbl = QLabel()
        self._month_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {self.T['text']};"
            f" background: transparent; min-width: 110px;")
        self._month_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self._month_lbl)

        next_btn = QPushButton("›")
        next_btn.setFixedSize(QSize(30, 30))
        next_btn.setStyleSheet(self._nav_btn_style())
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.clicked.connect(lambda: self._change_month(1))
        nav.addWidget(next_btn)

        hdr.addLayout(nav)
        vbox.addLayout(hdr)

        # ── 달력 그리드 컨테이너 ──────────────────────────
        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background: transparent;")
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(2)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self._grid_widget)

        # ── 범례 ─────────────────────────────────────────
        legend = QHBoxLayout()
        legend.setSpacing(14)
        for color, label in [
            (self.T["urgent"], t("D-3 이내")),
            (self.T["warn"],   t("D-10 이내")),
            (self.T["safe"],   t("여유")),
            (self.T["muted"],  t("완료")),
        ]:
            row = QHBoxLayout()
            row.setSpacing(4)
            dot = QFrame()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(
                f"background: {color}; border-radius: 5px; border: none;")
            row.addWidget(dot)
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"font-size: 10px; color: {self.T['muted']}; background: transparent;")
            row.addWidget(lbl)
            legend.addLayout(row)
        legend.addStretch()
        vbox.addLayout(legend)

        self._draw_grid()

    def _nav_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: {self.T['accent_light']};
                color: {self.T['accent']};
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {self.T['accent']};
                color: white;
            }}
        """

    # ── 달력 그리드 그리기 ────────────────────────────────
    def _draw_grid(self) -> None:
        # 기존 위젯 제거
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        y, m = self._cal_year, self._cal_month
        self._month_lbl.setText(fmt_month(y, m))

        # 요일 헤더
        dows = dow_labels()
        for col, d in enumerate(dows):
            lbl = QLabel(d)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedSize(40, 24)
            lbl.setStyleSheet(
                f"font-size: 11px; font-weight: 700;"
                f" color: {self.T['muted']}; background: transparent;")
            self._grid_layout.addWidget(lbl, 0, col)

        # 마감일 맵
        dl_map: dict[str, list] = {}
        for p in self.data.get("projects", []):
            dl = p.get("deadline", "")
            dl_map.setdefault(dl, []).append(p)

        today = date.today()
        first_day = date(y, m, 1)
        start_col = (first_day.weekday() + 1) % 7  # 일요일 = 0
        days_in_month = calendar.monthrange(y, m)[1]

        row, col = 1, start_col
        for day in range(1, days_in_month + 1):
            d_str = f"{y}-{m:02d}-{day:02d}"
            d_obj = date(y, m, day)
            is_today = (d_obj == today)
            has_dl   = d_str in dl_map

            cell = _CalCell(
                day, is_today, has_dl,
                dl_map.get(d_str, []),
                d_str, self.T
            )
            if has_dl:
                cell.clicked.connect(
                    lambda ds=d_str, ps=dl_map[d_str]:
                    self._show_day_deadlines(ds, ps)
                )
            self._grid_layout.addWidget(cell, row, col)

            col += 1
            if col > 6:
                col = 0
                row += 1

    def _change_month(self, delta: int) -> None:
        m = self._cal_month + delta
        y = self._cal_year
        if m > 12: m = 1; y += 1
        elif m < 1: m = 12; y -= 1
        self._cal_year, self._cal_month = y, m
        self._draw_grid()

    def _show_day_deadlines(self, d_str: str, projs: list) -> None:
        dlg = _DayDeadlineDialog(d_str, projs, self.T, parent=self)
        dlg.exec()

    def refresh(self) -> None:
        self._draw_grid()


class _CalCell(QWidget):
    from PySide6.QtCore import Signal as _Sig
    clicked = _Sig()

    def __init__(self, day: int, is_today: bool, has_dl: bool,
                 projs: list, d_str: str, T: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.setFixedSize(40, 44)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 2, 0, 2)
        vbox.setSpacing(1)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 날짜 숫자
        day_lbl = QLabel(str(day))
        day_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if is_today:
            day_lbl.setStyleSheet(f"""
                background: {T['accent']};
                color: white;
                border-radius: 13px;
                font-size: 12px;
                font-weight: 800;
                min-width: 26px;
                min-height: 26px;
                max-width: 26px;
                max-height: 26px;
            """)
        else:
            day_lbl.setStyleSheet(
                f"font-size: 12px; color: {T['text']}; background: transparent;")
        vbox.addWidget(day_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        # 마감 점들
        if has_dl:
            dot_row = QHBoxLayout()
            dot_row.setSpacing(2)
            dot_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dl_days = days_left(d_str)
            for p in projs[:3]:
                urg = urgency(dl_days, all(p.get("steps", [])))
                color_map = {
                    "done": T["muted"], "urgent": T["urgent"],
                    "warn": T["warn"],  "safe": T["safe"],
                }
                dot = QFrame()
                dot.setFixedSize(6, 6)
                dot.setStyleSheet(
                    f"background: {color_map.get(urg, T['accent'])};"
                    f" border-radius: 3px; border: none;")
                dot_row.addWidget(dot)
            dot_widget = QWidget()
            dot_widget.setStyleSheet("background: transparent;")
            dot_widget.setLayout(dot_row)
            vbox.addWidget(dot_widget, 0, Qt.AlignmentFlag.AlignHCenter)

        if has_dl:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()


class _DayDeadlineDialog(QDialog):
    def __init__(self, d_str: str, projs: list, T: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.setWindowTitle(f"{d_str} {t('마감')}")
        self.setMinimumWidth(320)
        self.resize(320, min(500, 120 + len(projs) * 110))

        vbox = QVBoxLayout(self)
        vbox.setSpacing(8)
        vbox.setContentsMargins(20, 20, 20, 16)

        # 날짜 헤더
        try:
            d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
            dows_list = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
            dow = t(dows_list[d_obj.weekday()])
            hdr_txt = f"{d_obj.month}월 {d_obj.day}일 ({dow})"
        except Exception:
            hdr_txt = d_str

        title_lbl = QLabel(hdr_txt)
        title_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: 800; color: {T['text']};")
        vbox.addWidget(title_lbl)

        sub_lbl = QLabel(f"{t('마감')} {len(projs)}{t('개')}")
        sub_lbl.setStyleSheet(f"font-size: 11px; color: {T['muted']};")
        vbox.addWidget(sub_lbl)

        pill_bg = {
            "urgent": "#fde8e8", "warn": "#fff0d0",
            "safe": "#d6f5ec",   "done": "#e8f5e9"
        }
        pill_tc = {
            "urgent": T["urgent"], "warn": T["warn"],
            "safe": T["safe"],     "done": "#388e3c"
        }

        for p in projs:
            dl_days = days_left(d_str)
            done    = all(p.get("steps", []))
            urg     = urgency(dl_days, done)
            steps   = p.get("steps", [])
            pct     = int(sum(steps) / len(steps) * 100) if steps else 0

            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {T['card']};
                    border-radius: 12px;
                    border: 1px solid {T['accent_light']};
                }}
            """)
            card_vbox = QVBoxLayout(card)
            card_vbox.setContentsMargins(12, 10, 12, 10)

            top = QHBoxLayout()
            name_lbl = QLabel(p.get("name", ""))
            name_lbl.setStyleSheet(
                f"font-size: 13px; font-weight: 700; color: {T['text']};"
                f" background: transparent;")
            top.addWidget(name_lbl)
            top.addStretch()

            pill = QLabel(pill_text(dl_days, done))
            pill.setStyleSheet(f"""
                background: {pill_bg.get(urg, '#eee')};
                color: {pill_tc.get(urg, '#333')};
                border-radius: 9px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 700;
            """)
            top.addWidget(pill)
            card_vbox.addLayout(top)

            bar = QProgressBar()
            bar.setMaximum(100)
            bar.setValue(pct)
            bar.setFixedHeight(7)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background: {T['accent_light']};
                    border-radius: 3px;
                    border: none;
                }}
                QProgressBar::chunk {{
                    background: {T.get(urg, T['accent'])};
                    border-radius: 3px;
                }}
            """)
            card_vbox.addWidget(bar)
            vbox.addWidget(card)

        close_btn = QPushButton(t("닫기"))
        close_btn.setObjectName("accent")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        vbox.addWidget(close_btn)
