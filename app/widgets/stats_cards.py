"""상단 통계 카드 4개"""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

from ..i18n import t
from ..utils import days_left


class StatsCards(QWidget):
    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self._build()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._cards: list[_StatCard] = []
        for label, key, color in [
            (t("전체 마감"),   "total",   self.T["accent"]),
            (t("완료"),       "done",    self.T["safe"]),
            (t("⚠ D-3 이내"), "urgent",  self.T["urgent"]),
            (t("이번 달 작업"), "month_h", self.T["warn"]),
        ]:
            card = _StatCard(self.T, label, "—", color)
            layout.addWidget(card)
            self._cards.append(card)

        self.refresh()

    def refresh(self) -> None:
        projs = self.data.get("projects", [])
        total  = len(projs)
        done   = sum(1 for p in projs if all(p.get("steps", [])))
        urgent = sum(1 for p in projs
                     if not all(p.get("steps", []))
                     and days_left(p.get("deadline", "9999-12-31")) <= 3)

        month_key = date.today().strftime("%Y-%m")
        month_h   = sum(
            v for k, v in self.data.get("daily_work", {}).items()
            if k.startswith(month_key)
        )

        values = [
            (str(total),         t("개")),
            (str(done),          t("개")),
            (str(urgent),        t("개")),
            (f"{month_h:.1f}",   t("시간")),
        ]
        for card, (val, unit) in zip(self._cards, values):
            card.set_value(val, unit)


class _StatCard(QFrame):
    def __init__(self, T: dict, label: str, value: str, color: str,
                 parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame#card {{
                background: {T['card']};
                border-radius: 16px;
                border: 1px solid {T['accent_light']};
            }}
        """)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(16, 14, 16, 14)
        vbox.setSpacing(4)

        self._label_lbl = QLabel(label)
        self._label_lbl.setStyleSheet(
            f"color: {T['muted']}; font-size: 11px; font-weight: 600; background: transparent;")
        self._label_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(self._label_lbl)

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(2)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._val_lbl = QLabel(value)
        self._val_lbl.setStyleSheet(
            f"color: {color}; font-size: 28px; font-weight: 800; background: transparent;")
        row_layout.addWidget(self._val_lbl)

        self._unit_lbl = QLabel("")
        self._unit_lbl.setStyleSheet(
            f"color: {T['muted']}; font-size: 12px; background: transparent;")
        row_layout.addWidget(self._unit_lbl)

        vbox.addWidget(row)

    def set_value(self, value: str, unit: str) -> None:
        self._val_lbl.setText(value)
        self._unit_lbl.setText(unit)
