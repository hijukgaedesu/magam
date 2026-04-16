"""통계 다이얼로그"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from collections import defaultdict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget, QScrollArea, QTabWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QFont

from ..i18n import t
from ..utils import days_left


class StatsDialog(QDialog):
    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self.setWindowTitle(t("📈 통계"))
        self.setMinimumSize(480, 560)
        self.resize(520, 620)
        self._build()

    def _build(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: {self.T['bg']};
            }}
            QTabBar::tab {{
                background: {self.T['accent_light']};
                color: {self.T['text']};
                border: none;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {self.T['accent']};
                color: white;
                font-weight: 700;
            }}
        """)

        tabs.addTab(self._make_summary_tab(), t("요약"))
        tabs.addTab(self._make_work_tab(), t("작업 시간"))
        tabs.addTab(self._make_step_tab(), t("단계 분석"))

        vbox.addWidget(tabs)

        close_btn = QPushButton(t("닫기"))
        close_btn.setObjectName("accent")
        close_btn.setFixedHeight(38)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 10, 20, 14)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        vbox.addLayout(btn_layout)

    # ── 요약 탭 ───────────────────────────────────────────
    def _make_summary_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {self.T['bg']};")
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(20, 16, 20, 16)
        vbox.setSpacing(12)

        projs = self.data.get("projects", [])
        total  = len(projs)
        done   = sum(1 for p in projs if all(p.get("steps", [])))
        active = total - done
        urgent = sum(1 for p in projs
                     if not all(p.get("steps", []))
                     and days_left(p.get("deadline", "9999-12-31")) <= 3)

        stats = [
            (t("전체 마감"), str(total), t("개"), self.T["accent"]),
            (t("진행 중"),   str(active), t("개"), self.T["warn"]),
            (t("완료"),      str(done),   t("개"), self.T["safe"]),
            (t("D-3 이내"), str(urgent),  t("개"), self.T["urgent"]),
        ]

        cards_row = QHBoxLayout()
        cards_row.setSpacing(8)
        for label, val, unit, color in stats:
            card = self._mini_stat_card(label, val, unit, color)
            cards_row.addWidget(card)
        vbox.addLayout(cards_row)

        # 이번 달 통계
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {self.T['accent_light']}; background: {self.T['accent_light']}; height: 1px;")
        vbox.addWidget(sep)

        month_key = date.today().strftime("%Y-%m")
        month_h = sum(
            v for k, v in self.data.get("daily_work", {}).items()
            if k.startswith(month_key)
        )
        month_lbl = QLabel(t(f"이번 달 총 작업: ") + f"{month_h:.1f}h")
        month_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {self.T['text']}; background: transparent;")
        vbox.addWidget(month_lbl)

        # 가장 가까운 마감
        active_projs = [p for p in projs if not all(p.get("steps", []))]
        if active_projs:
            nearest = min(active_projs, key=lambda p: days_left(p.get("deadline", "9999-12-31")))
            dl = days_left(nearest.get("deadline", "9999-12-31"))
            dl_str = f"D-{dl}" if dl > 0 else (t("오늘") if dl == 0 else t(f"{abs(dl)}일 초과"))
            nearest_lbl = QLabel(
                t("가장 가까운 마감: ") + f"{nearest.get('name', '')} ({dl_str})"
            )
            nearest_lbl.setStyleSheet(
                f"font-size: 12px; color: {self.T['muted']}; background: transparent;")
            nearest_lbl.setWordWrap(True)
            vbox.addWidget(nearest_lbl)

        vbox.addStretch()
        return w

    def _mini_stat_card(self, label: str, val: str, unit: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"""
            QFrame#card {{
                background: {self.T['card']};
                border-radius: 12px;
                border: 1px solid {self.T['accent_light']};
            }}
        """)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(2)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"font-size: 10px; color: {self.T['muted']}; background: transparent;")
        vbox.addWidget(lbl)

        val_row = QHBoxLayout()
        val_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_lbl = QLabel(val)
        val_lbl.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {color}; background: transparent;")
        val_row.addWidget(val_lbl)
        unit_lbl = QLabel(unit)
        unit_lbl.setStyleSheet(f"font-size: 11px; color: {self.T['muted']}; background: transparent;")
        val_row.addWidget(unit_lbl)
        vbox.addLayout(val_row)
        return card

    # ── 작업 시간 탭 ──────────────────────────────────────
    def _make_work_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {self.T['bg']};")
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(20, 16, 20, 16)
        vbox.setSpacing(12)

        daily_work = self.data.get("daily_work", {})

        # 최근 7일 바 차트
        hdr = QLabel(t("최근 7일 작업 시간"))
        hdr.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {self.T['text']}; background: transparent;")
        vbox.addWidget(hdr)

        today = date.today()
        week_data = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            key = d.isoformat()
            week_data.append((d.strftime("%m/%d"), daily_work.get(key, 0)))

        chart = _SimpleBarChart(week_data, self.T)
        chart.setFixedHeight(160)
        vbox.addWidget(chart)

        # 이번 달 통계
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {self.T['accent_light']}; max-height: 1px;")
        vbox.addWidget(sep)

        month_key = date.today().strftime("%Y-%m")
        month_days = [(k, v) for k, v in daily_work.items() if k.startswith(month_key)]
        if month_days:
            total_h = sum(v for _, v in month_days)
            avg_h   = total_h / len(month_days)
            max_day, max_h = max(month_days, key=lambda x: x[1])

            for text in [
                t("이번 달 총 작업: ") + f"{total_h:.1f}h",
                t("일 평균: ") + f"{avg_h:.1f}h",
                t("최다 작업일: ") + f"{max_day} ({max_h:.1f}h)",
            ]:
                lbl = QLabel(text)
                lbl.setStyleSheet(
                    f"font-size: 12px; color: {self.T['text']}; background: transparent;")
                vbox.addWidget(lbl)

        vbox.addStretch()
        return w

    # ── 단계 분석 탭 ──────────────────────────────────────
    def _make_step_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {self.T['bg']};")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(20, 16, 20, 16)
        vbox.setSpacing(10)

        projs = self.data.get("projects", [])
        if not projs:
            empty = QLabel(t("마감이 없어요."))
            empty.setStyleSheet(
                f"font-size: 13px; color: {self.T['muted']}; background: transparent;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vbox.addWidget(empty)
        else:
            for p in projs:
                steps = p.get("steps", [])
                if not steps:
                    continue
                pct  = int(sum(steps) / len(steps) * 100)
                done = all(steps)

                row = QFrame()
                row.setStyleSheet(f"""
                    QFrame {{
                        background: {self.T['card']};
                        border-radius: 10px;
                        border: 1px solid {self.T['accent_light']};
                    }}
                """)
                row_vbox = QVBoxLayout(row)
                row_vbox.setContentsMargins(12, 10, 12, 10)
                row_vbox.setSpacing(4)

                name_row = QHBoxLayout()
                name_lbl = QLabel(p.get("name", ""))
                name_lbl.setStyleSheet(
                    f"font-size: 12px; font-weight: 700; color: {self.T['text']}; background: transparent;")
                name_row.addWidget(name_lbl)
                name_row.addStretch()
                pct_lbl = QLabel(f"{pct}%")
                color = self.T["safe"] if done else self.T["accent"]
                pct_lbl.setStyleSheet(
                    f"font-size: 12px; font-weight: 700; color: {color}; background: transparent;")
                name_row.addWidget(pct_lbl)
                row_vbox.addLayout(name_row)

                from PySide6.QtWidgets import QProgressBar
                bar = QProgressBar()
                bar.setMaximum(100)
                bar.setValue(pct)
                bar.setFixedHeight(6)
                bar.setTextVisible(False)
                bar.setStyleSheet(f"""
                    QProgressBar {{
                        background: {self.T['accent_light']};
                        border-radius: 3px;
                        border: none;
                    }}
                    QProgressBar::chunk {{
                        background: {self.T['safe'] if done else self.T['accent']};
                        border-radius: 3px;
                    }}
                """)
                row_vbox.addWidget(bar)

                # 단계 이름들
                step_names = p.get("step_names", [f"단계{i+1}" for i in range(len(steps))])
                steps_text = "  ".join(
                    f"{'✅' if s else '○'} {n}"
                    for s, n in zip(steps, step_names)
                )
                steps_lbl = QLabel(steps_text)
                steps_lbl.setStyleSheet(
                    f"font-size: 10px; color: {self.T['muted']}; background: transparent;")
                steps_lbl.setWordWrap(True)
                row_vbox.addWidget(steps_lbl)

                vbox.addWidget(row)

        vbox.addStretch()
        scroll.setWidget(inner)

        outer_vbox = QVBoxLayout(w)
        outer_vbox.setContentsMargins(0, 0, 0, 0)
        outer_vbox.addWidget(scroll)
        return w


# ── 간단한 바 차트 (QPainter) ─────────────────────────────
class _SimpleBarChart(QWidget):
    def __init__(self, data: list[tuple[str, float]], T: dict, parent=None) -> None:
        super().__init__(parent)
        self._data = data
        self.T = T

    def paintEvent(self, event) -> None:
        if not self._data:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        pad_left = 10
        pad_right = 10
        pad_top = 10
        pad_bottom = 30

        max_val = max(v for _, v in self._data) or 1
        bar_area_h = H - pad_top - pad_bottom
        bar_area_w = W - pad_left - pad_right
        n = len(self._data)
        bar_w = max(4, (bar_area_w // n) - 6)
        gap   = (bar_area_w - bar_w * n) // (n + 1)

        accent = QColor(self.T["accent"])
        muted  = QColor(self.T["muted"])

        p.setFont(QFont("", 9))

        for i, (label, val) in enumerate(self._data):
            x = pad_left + gap + i * (bar_w + gap)
            bar_h = int(val / max_val * bar_area_h) if max_val > 0 else 0
            y = pad_top + bar_area_h - bar_h

            # 바
            p.setBrush(accent)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)

            # 값 레이블
            if val > 0:
                p.setPen(QPen(accent))
                p.drawText(x, y - 2, bar_w, 14,
                           Qt.AlignmentFlag.AlignCenter, f"{val:.1f}")

            # x축 레이블
            p.setPen(QPen(muted))
            p.drawText(x - 4, H - pad_bottom + 4, bar_w + 8, 20,
                       Qt.AlignmentFlag.AlignCenter, label)

        p.end()
