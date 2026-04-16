"""커미션 수입 다이얼로그"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QFont

from ..i18n import t


class CommissionDialog(QDialog):
    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self.setWindowTitle(t("💰 커미션 수입"))
        self.setMinimumSize(440, 500)
        self.resize(480, 560)
        self._build()

    def _build(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: {self.T['bg']}; border: none;")

        content = QWidget()
        content.setStyleSheet(f"background: {self.T['bg']};")
        content_vbox = QVBoxLayout(content)
        content_vbox.setContentsMargins(20, 16, 20, 16)
        content_vbox.setSpacing(14)

        # 커미션 수입 집계
        projs = self.data.get("projects", [])
        commission_projs = [p for p in projs
                            if p.get("category") == "커미션" and p.get("price", 0) > 0]

        if not commission_projs:
            empty = QLabel(t("커미션 수입 기록이 없어요.\n마감 추가 시 가격을 입력하면 여기에 나타나요."))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"font-size: 13px; color: {self.T['muted']}; background: transparent;"
                f" padding: 40px;")
            content_vbox.addWidget(empty)
        else:
            # 전체 합계 카드
            total_income = sum(p.get("price", 0) for p in commission_projs)
            done_income  = sum(p.get("price", 0) for p in commission_projs
                               if all(p.get("steps", [])))

            summary_frame = QFrame()
            summary_frame.setObjectName("card")
            summary_frame.setStyleSheet(f"""
                QFrame#card {{
                    background: {self.T['card']};
                    border-radius: 14px;
                    border: 1px solid {self.T['accent_light']};
                }}
            """)
            sf_layout = QHBoxLayout(summary_frame)
            sf_layout.setContentsMargins(16, 14, 16, 14)
            sf_layout.setSpacing(20)

            for label, val, color in [
                (t("전체 커미션"), f"{total_income:,.0f}원", self.T["accent"]),
                (t("완료 수입"),   f"{done_income:,.0f}원",  self.T["safe"]),
                (t("진행 중"),     f"{total_income - done_income:,.0f}원", self.T["warn"]),
            ]:
                col = QVBoxLayout()
                col.setSpacing(2)
                col.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl = QLabel(label)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet(
                    f"font-size: 10px; color: {self.T['muted']}; background: transparent;")
                col.addWidget(lbl)
                val_lbl = QLabel(val)
                val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                val_lbl.setStyleSheet(
                    f"font-size: 16px; font-weight: 800; color: {color}; background: transparent;")
                col.addWidget(val_lbl)
                sf_layout.addLayout(col)

            content_vbox.addWidget(summary_frame)

            # 월별 집계
            monthly: dict[str, float] = defaultdict(float)
            for p in commission_projs:
                dl = p.get("deadline", "")
                if len(dl) >= 7:
                    monthly[dl[:7]] += p.get("price", 0)

            if monthly:
                content_vbox.addWidget(self._sec_lbl(t("월별 수입")))

                # 바 차트
                months_sorted = sorted(monthly.items())[-6:]  # 최근 6개월
                chart = _MonthlyBarChart(months_sorted, self.T)
                chart.setFixedHeight(150)
                content_vbox.addWidget(chart)

                # 목록
                for month_key, amount in sorted(monthly.items(), reverse=True):
                    row = QFrame()
                    row.setStyleSheet(f"""
                        QFrame {{
                            background: {self.T['card']};
                            border-radius: 10px;
                            border: 1px solid {self.T['accent_light']};
                        }}
                    """)
                    row_layout = QHBoxLayout(row)
                    row_layout.setContentsMargins(14, 10, 14, 10)

                    month_lbl = QLabel(month_key)
                    month_lbl.setStyleSheet(
                        f"font-size: 12px; font-weight: 700; color: {self.T['text']};"
                        f" background: transparent;")
                    row_layout.addWidget(month_lbl)
                    row_layout.addStretch()

                    amount_lbl = QLabel(f"{amount:,.0f}{t('원')}")
                    amount_lbl.setStyleSheet(
                        f"font-size: 14px; font-weight: 800; color: {self.T['safe']};"
                        f" background: transparent;")
                    row_layout.addWidget(amount_lbl)
                    content_vbox.addWidget(row)

        content_vbox.addStretch()
        scroll.setWidget(content)
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

    def _sec_lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {self.T['muted']};"
            f" background: transparent;")
        return lbl


class _MonthlyBarChart(QWidget):
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
        pad_top = 14
        pad_bottom = 30

        max_val = max(v for _, v in self._data) or 1
        bar_area_h = H - pad_top - pad_bottom
        bar_area_w = W - pad_left - pad_right
        n = len(self._data)
        bar_w = max(4, (bar_area_w // n) - 8)
        gap   = (bar_area_w - bar_w * n) // (n + 1)

        accent = QColor(self.T["safe"])
        muted  = QColor(self.T["muted"])

        p.setFont(QFont("", 9))

        for i, (label, val) in enumerate(self._data):
            x = pad_left + gap + i * (bar_w + gap)
            bar_h = int(val / max_val * bar_area_h) if max_val > 0 else 0
            y = pad_top + bar_area_h - bar_h

            p.setBrush(accent)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)

            if val > 0:
                p.setPen(QPen(accent))
                short_val = f"{val/10000:.0f}만" if val >= 10000 else str(int(val))
                p.drawText(x - 4, y - 2, bar_w + 8, 14,
                           Qt.AlignmentFlag.AlignCenter, short_val)

            # x축: 월만 표시 (YYYY-MM → MM월)
            month_str = label[5:7].lstrip("0") + t("월")
            p.setPen(QPen(muted))
            p.drawText(x - 4, H - pad_bottom + 4, bar_w + 8, 20,
                       Qt.AlignmentFlag.AlignCenter, month_str)

        p.end()
