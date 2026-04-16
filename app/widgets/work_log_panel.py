"""작업량 패널 — 일별/주간/월간 바 차트 + 히트맵"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QDialog, QLineEdit, QTextEdit,
    QInputDialog, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt, QSize, QRect, QTimer, Signal
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPainterPath, QFontMetrics,
)

from ..i18n import t, _translations, fmt_month, dow_labels
from ..data import save_data
from ..utils import hex_to_hsl, hsl_to_hex


class WorkLogPanel(QFrame):
    data_changed = Signal()

    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self._view = "daily"
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
        vbox.setSpacing(12)

        # ── 헤더 ─────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel(t("📊 작업량"))
        title.setStyleSheet(
            f"font-size: 14px; font-weight: 800; color: {self.T['text']};"
            f" background: transparent;")
        hdr.addWidget(title)
        hdr.addStretch()

        # 뷰 토글 버튼
        toggle_w = QWidget()
        toggle_w.setStyleSheet("background: transparent;")
        toggle_l = QHBoxLayout(toggle_w)
        toggle_l.setContentsMargins(0, 0, 0, 0)
        toggle_l.setSpacing(4)
        for label, key in [
            (t("일별"), "daily"), (t("주간"), "weekly"),
            (t("월간"), "monthly"), (t("히트맵"), "heatmap"),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._style_toggle(btn, key == self._view)
            btn.clicked.connect(lambda checked=False, k=key: self._switch(k))
            toggle_l.addWidget(btn)
        hdr.addWidget(toggle_w)

        # + 오늘 기록
        log_btn = QPushButton(t("+ 오늘 기록"))
        log_btn.setFixedHeight(28)
        log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        log_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent_light']};
                color: {self.T['text']};
                border: none; border-radius: 10px;
                padding: 0 12px; font-size: 11px; font-weight: 700;
            }}
            QPushButton:hover {{ background: {self.T['accent']}; color: white; }}
        """)
        log_btn.clicked.connect(self._log_today)
        hdr.addWidget(log_btn)
        vbox.addLayout(hdr)

        # ── 컨텐츠 영역 ───────────────────────────────────
        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        vbox.addWidget(self._content)

        self._render_content()

    def _style_toggle(self, btn: QPushButton, active: bool) -> None:
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent'] if active else self.T['accent_light']};
                color: {'white' if active else self.T['text']};
                border: none; border-radius: 8px;
                padding: 0 10px; font-size: 11px; font-weight: 700;
            }}
            QPushButton:hover {{
                background: {self.T['accent']}; color: white;
            }}
        """)

    def _switch(self, view: str) -> None:
        self._view = view
        # 토글 버튼 스타일 갱신
        hdr_w = self.layout().itemAt(0).layout()
        toggle_l = hdr_w.itemAt(2).widget().layout()
        views = ["daily", "weekly", "monthly", "heatmap"]
        for i, k in enumerate(views):
            btn = toggle_l.itemAt(i).widget()
            if btn:
                self._style_toggle(btn, k == view)
        self._render_content()

    def _render_content(self) -> None:
        old = self._content.layout()
        if old:
            while old.count():
                item = old.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            QWidget().setLayout(old)

        new_layout = QVBoxLayout(self._content)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.setSpacing(8)

        if self._view == "daily":
            self._render_daily(new_layout)
        elif self._view == "weekly":
            chart = BarChartWidget(self.T, self.data, mode="weekly")
            new_layout.addWidget(chart)
        elif self._view == "monthly":
            chart = BarChartWidget(self.T, self.data, mode="monthly")
            new_layout.addWidget(chart)
        else:
            hm = HeatmapWidget(self.T, self.data)
            new_layout.addWidget(hm)

    # ── 일별 테이블 ───────────────────────────────────────
    def _render_daily(self, layout: QVBoxLayout) -> None:
        today = date.today()
        work_data = self.data.get("daily_work", {})
        memos     = self.data.get("daily_memos", {})
        _dows     = dow_labels()
        dow_kr    = [_dows[(i + 1) % 7] for i in range(7)]

        # 헤더 행
        hdr_w = QWidget()
        hdr_w.setStyleSheet(
            f"background: {self.T['accent_light']}; border-radius: 8px;")
        hdr_l = QHBoxLayout(hdr_w)
        hdr_l.setContentsMargins(12, 6, 12, 6)
        hdr_l.setSpacing(0)
        for txt, w in [
            (t("날짜"), 90), (t("요일"), 50), (t("작업시간"), 70), (t("메모"), 0)
        ]:
            lbl = QLabel(txt)
            lbl.setStyleSheet(
                f"font-size: 11px; font-weight: 700; color: {self.T['text']};"
                f" background: transparent;")
            if w:
                lbl.setFixedWidth(w)
            else:
                lbl.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            hdr_l.addWidget(lbl)
        layout.addWidget(hdr_w)

        # 데이터 행 (최근 14일)
        for i in range(13, -1, -1):
            d = today - timedelta(days=i)
            d_str   = d.strftime("%Y-%m-%d")
            hours   = work_data.get(d_str, 0)
            memo    = memos.get(d_str, "")
            is_today = (d == today)

            row_w = QWidget()
            row_w.setStyleSheet(
                f"background: {self.T['accent_light'] if is_today else 'transparent'};"
                f"border-radius: 6px;")
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(12, 4, 12, 4)
            row_l.setSpacing(0)

            date_txt = f"{t('오늘')} ({d.strftime('%m/%d')})" if is_today \
                else d.strftime("%m/%d")
            fw = "700" if is_today else "400"

            for txt, width in [
                (date_txt, 90), (dow_kr[d.weekday()], 50),
                (f"{hours:.1f}h" if hours > 0 else "—", 70),
                (memo[:30] + ("…" if len(memo) > 30 else ""), 0),
            ]:
                lbl = QLabel(txt)
                lbl.setStyleSheet(
                    f"font-size: 12px; font-weight: {fw};"
                    f" color: {self.T['text']}; background: transparent;")
                if width:
                    lbl.setFixedWidth(width)
                else:
                    lbl.setSizePolicy(
                        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                row_l.addWidget(lbl)

            # 수정 버튼
            edit_btn = QPushButton("✏")
            edit_btn.setFixedSize(22, 22)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {self.T['muted']};
                    border: none; border-radius: 11px; font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {self.T['accent_light']}; color: {self.T['accent']};
                }}
            """)
            edit_btn.clicked.connect(
                lambda checked=False, ds=d_str: self._open_day_edit(ds))
            row_l.addWidget(edit_btn)

            layout.addWidget(row_w)

        # 오늘 메모 영역
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {self.T['accent_light']}; background: {self.T['accent_light']};")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        memo_lbl = QLabel(t("📝 오늘의 메모"))
        memo_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {self.T['muted']};"
            f" background: transparent;")
        layout.addWidget(memo_lbl)

        today_str = today.strftime("%Y-%m-%d")
        self._memo_edit = QTextEdit()
        self._memo_edit.setFixedHeight(64)
        self._memo_edit.setPlaceholderText("오늘 작업 메모...")
        saved_memo = self.data.get("daily_memos", {}).get(today_str, "")
        if saved_memo:
            self._memo_edit.setPlainText(saved_memo)

        save_memo_btn = QPushButton(t("메모 저장"))
        save_memo_btn.setFixedHeight(28)
        save_memo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_memo_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent_light']}; color: {self.T['text']};
                border: none; border-radius: 10px;
                font-size: 11px; font-weight: 700;
            }}
            QPushButton:hover {{ background: {self.T['accent']}; color: white; }}
        """)
        save_memo_btn.clicked.connect(self._save_memo)
        layout.addWidget(self._memo_edit)
        layout.addWidget(save_memo_btn)

    def _open_day_edit(self, d_str: str) -> None:
        dlg = _DayEditDialog(d_str, self.T, self.data, parent=self)
        if dlg.exec():
            save_data(self.data)
            self.data_changed.emit()
            self.refresh()

    def _save_memo(self) -> None:
        today_str = date.today().strftime("%Y-%m-%d")
        text = self._memo_edit.toPlainText().strip()
        self.data.setdefault("daily_memos", {})[today_str] = text
        save_data(self.data)

    def _log_today(self) -> None:
        val, ok = QInputDialog.getText(
            self,
            t("작업 시간 기록"),
            t("오늘 작업한 시간을 입력하세요 (예: 3.5)"),
        )
        if ok and val:
            try:
                hours = float(val)
                today_str = date.today().strftime("%Y-%m-%d")
                self.data["daily_work"][today_str] = hours
                save_data(self.data)
                self.data_changed.emit()
                self.refresh()
            except ValueError:
                QMessageBox.warning(self, t("오류"), t("숫자를 입력해주세요 (예: 3.5)"))

    def refresh(self) -> None:
        self._render_content()


# ── 하루 수정 다이얼로그 ───────────────────────────────
class _DayEditDialog(QDialog):
    def __init__(self, d_str: str, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self.d_str = d_str
        self.setWindowTitle(d_str)
        self.resize(300, 220)
        self._build()

    def _build(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setSpacing(10)
        vbox.setContentsMargins(20, 20, 20, 16)

        vbox.addWidget(QLabel(f"{t('날짜')}: {self.d_str}"))

        h_row = QHBoxLayout()
        h_row.addWidget(QLabel(f"{t('작업시간')} (h):"))
        self.h_edit = QLineEdit()
        cur = self.data.get("daily_work", {}).get(self.d_str, 0)
        self.h_edit.setText(str(round(cur, 2)) if cur else "")
        h_row.addWidget(self.h_edit)
        vbox.addLayout(h_row)

        vbox.addWidget(QLabel(f"{t('메모')}:"))
        self.memo_edit = QTextEdit()
        self.memo_edit.setFixedHeight(70)
        cur_memo = self.data.get("daily_memos", {}).get(self.d_str, "")
        self.memo_edit.setPlainText(cur_memo)
        vbox.addWidget(self.memo_edit)

        save_btn = QPushButton(t("저장"))
        save_btn.setObjectName("accent")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        vbox.addWidget(save_btn)

    def _save(self) -> None:
        try:
            h = float(self.h_edit.text().strip()) if self.h_edit.text().strip() else 0.0
        except ValueError:
            h = 0.0
        if h > 0:
            self.data.setdefault("daily_work", {})[self.d_str] = round(h, 3)
        elif self.d_str in self.data.get("daily_work", {}):
            del self.data["daily_work"][self.d_str]

        memo = self.memo_edit.toPlainText().strip()
        if memo:
            self.data.setdefault("daily_memos", {})[self.d_str] = memo
        elif self.d_str in self.data.get("daily_memos", {}):
            del self.data["daily_memos"][self.d_str]

        self.accept()


# ── 바 차트 (QPainter) ───────────────────────────────
class BarChartWidget(QWidget):
    def __init__(self, T: dict, data: dict, mode: str = "weekly",
                 parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self.mode = mode
        self.setMinimumHeight(200)
        self._prepare_data()

    def _prepare_data(self) -> None:
        work_data = self.data.get("daily_work", {})
        today = date.today()

        if self.mode == "weekly":
            self._title = t("최근 8주 작업량 (시간)")
            self._labels: list[str] = []
            self._values: list[float] = []
            for w in range(7, -1, -1):
                ws = today - timedelta(days=today.weekday() + 7 * w)
                total = sum(
                    work_data.get(
                        (ws + timedelta(days=d)).strftime("%Y-%m-%d"), 0)
                    for d in range(7))
                self._labels.append(ws.strftime("%m/%d"))
                self._values.append(total)
        else:
            self._title = t("최근 6개월 작업량 (시간)")
            self._labels = []
            self._values = []
            for mo_off in range(5, -1, -1):
                y  = today.year
                mo = today.month - mo_off
                while mo <= 0:
                    mo += 12; y -= 1
                total = sum(
                    v for k, v in work_data.items()
                    if k.startswith(f"{y}-{mo:02d}"))
                lbl = (calendar.month_abbr[mo]
                       if _translations.get("_cal_month_fmt")
                       else f"{mo}월")
                self._labels.append(lbl)
                self._values.append(total)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        PAD_L, PAD_R, PAD_T, PAD_B = 44, 12, 30, 36
        bar_area_h = h - PAD_T - PAD_B
        bar_area_w = w - PAD_L - PAD_R

        n   = len(self._values)
        max_v = max(self._values) if any(self._values) else 1
        font = QFont()
        font.setPointSize(8)
        p.setFont(font)
        fm = QFontMetrics(font)

        accent = QColor(self.T["accent"])
        accent_light = QColor(self.T["accent_light"])
        muted = QColor(self.T["muted"])
        text_c = QColor(self.T["text"])

        # 제목
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setWeight(QFont.Weight.Bold)
        p.setFont(title_font)
        p.setPen(QPen(muted))
        p.drawText(PAD_L, PAD_T - 6, self._title)
        p.setFont(font)

        # Y 격자선
        for frac, lbl_v in [(0, "0"), (0.5, f"{max_v/2:.0f}"), (1.0, f"{max_v:.0f}")]:
            y = PAD_T + bar_area_h - int(frac * bar_area_h)
            p.setPen(QPen(accent_light, 1, Qt.PenStyle.DashLine))
            p.drawLine(PAD_L, y, w - PAD_R, y)
            p.setPen(QPen(muted))
            p.drawText(QRect(0, y - 10, PAD_L - 4, 20),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       lbl_v)

        spacing = bar_area_w / max(n, 1)
        bar_w   = max(4, int(spacing * 0.55))

        for i, (lbl, val) in enumerate(zip(self._labels, self._values)):
            cx = int(PAD_L + spacing * i + spacing / 2)
            bh = int((val / max_v) * bar_area_h) if max_v > 0 else 0
            x0, y0 = cx - bar_w // 2, PAD_T + bar_area_h - bh
            x1, y1 = cx + bar_w // 2, PAD_T + bar_area_h

            is_current = (i == n - 1)
            color = accent if is_current else accent_light
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(color))

            if bh > 0:
                path = QPainterPath()
                r = min(4, bar_w // 2)
                path.addRoundedRect(x0, y0, bar_w, bh, r, r)
                p.drawPath(path)
                # 값 레이블
                val_str = f"{val:.1f}h"
                p.setPen(QPen(accent if is_current else muted))
                p.drawText(
                    QRect(cx - 30, y0 - 18, 60, 16),
                    Qt.AlignmentFlag.AlignHCenter,
                    val_str)
            else:
                p.setPen(QPen(muted))
                p.drawText(QRect(cx - 15, y0 - 16, 30, 14),
                           Qt.AlignmentFlag.AlignHCenter, "—")

            # X 레이블
            p.setPen(QPen(text_c if is_current else muted))
            p.drawText(
                QRect(cx - 30, PAD_T + bar_area_h + 4, 60, 20),
                Qt.AlignmentFlag.AlignHCenter, lbl)

        p.end()


# ── 히트맵 (QPainter) ────────────────────────────────
class HeatmapWidget(QWidget):
    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        CELL, GAP = 13, 2
        STEP = CELL + GAP
        PAD_L, PAD_T, PAD_B = 26, 20, 30
        WEEKS = 53
        self.CELL   = CELL
        self.GAP    = GAP
        self.STEP   = STEP
        self.PAD_L  = PAD_L
        self.PAD_T  = PAD_T
        self.PAD_B  = PAD_B
        self.WEEKS  = WEEKS
        self.setMinimumHeight(PAD_T + 7 * STEP + PAD_B + 20)

    def _intensity_color(self, hours: float) -> QColor:
        if hours <= 0:
            return QColor(self.T["accent_light"])
        try:
            h, s, _ = hex_to_hsl(self.T["accent"])
            s = max(s, 40)
            if hours < 1:   return QColor(hsl_to_hex(h, s * 0.40, 90))
            elif hours < 3: return QColor(hsl_to_hex(h, s * 0.60, 78))
            elif hours < 5: return QColor(hsl_to_hex(h, s * 0.80, 66))
            else:           return QColor(hsl_to_hex(h, s,         53))
        except Exception:
            return QColor(self.T["accent"])

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        CELL, GAP, STEP = self.CELL, self.GAP, self.STEP
        PAD_L, PAD_T, PAD_B = self.PAD_L, self.PAD_T, self.PAD_B
        WEEKS = self.WEEKS

        work_data = self.data.get("daily_work", {})
        today = date.today()
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        start_monday = this_monday - timedelta(weeks=WEEKS - 1)

        font = QFont()
        font.setPointSize(8)
        p.setFont(font)
        muted = QColor(self.T["muted"])
        accent = QColor(self.T["accent"])
        text_c = QColor(self.T["text"])

        # 제목
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setWeight(QFont.Weight.Bold)
        p.setFont(title_font)
        p.setPen(QPen(muted))
        p.drawText(PAD_L, PAD_T - 6, t("최근 1년 작업 히트맵"))
        p.setFont(font)

        avail_w = W - PAD_L - 8
        max_weeks = min(WEEKS, max(1, avail_w // STEP))
        actual_start = start_monday + timedelta(weeks=WEEKS - max_weeks)

        _dows = dow_labels()
        day_names = [_dows[(i + 1) % 7] for i in range(7)]

        # 월 레이블
        prev_month = -1
        for wi in range(max_weeks):
            col_mon = actual_start + timedelta(weeks=wi)
            if col_mon.month != prev_month:
                x = PAD_L + wi * STEP
                mlbl = (calendar.month_abbr[col_mon.month]
                        if _translations.get("_cal_month_fmt")
                        else f"{col_mon.month}월")
                p.setPen(QPen(muted))
                p.drawText(x, PAD_T - 4, mlbl)
                prev_month = col_mon.month

        # 요일 레이블 (월/수/금)
        for di in [0, 2, 4]:
            y_pos = PAD_T + di * STEP + CELL // 2
            p.setPen(QPen(muted))
            p.drawText(QRect(0, y_pos - 7, PAD_L - 4, 14),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       day_names[di])

        # 셀 그리기
        p.setPen(Qt.PenStyle.NoPen)
        for wi in range(max_weeks):
            for di in range(7):
                d = actual_start + timedelta(weeks=wi, days=di)
                if d > today:
                    continue
                d_str = d.strftime("%Y-%m-%d")
                hours = work_data.get(d_str, 0)
                color = self._intensity_color(hours)

                x0 = PAD_L + wi * STEP
                y0 = PAD_T + di * STEP

                p.setBrush(QBrush(color))
                p.drawRoundedRect(x0, y0, CELL, CELL, 2, 2)

                # 오늘 강조 테두리
                if d == today:
                    p.setPen(QPen(accent, 2))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawRoundedRect(x0, y0, CELL, CELL, 2, 2)
                    p.setPen(Qt.PenStyle.NoPen)

        # 하단 범례
        legend_y = PAD_T + 7 * STEP + 10
        p.setPen(QPen(muted))
        p.drawText(PAD_L, legend_y + 8, t("적음"))
        for li, h_v in enumerate([0, 0.5, 2, 4, 7]):
            x0 = PAD_L + 30 + li * (CELL + 3)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(self._intensity_color(h_v)))
            p.drawRoundedRect(x0, legend_y, CELL, CELL, 2, 2)
        end_x = PAD_L + 30 + 5 * (CELL + 3) + 4
        p.setPen(QPen(muted))
        p.drawText(end_x, legend_y + 8, t("많음"))

        # 통계 요약
        days_worked = sum(1 for v in work_data.values() if v > 0)
        total_h = sum(work_data.values())
        unit = _translations.get("_unit_days", "일").strip()
        summary = f"{days_worked}{unit} / {total_h:.0f}h"
        p.setPen(QPen(muted))
        p.drawText(
            QRect(0, legend_y, W - 8, 14),
            Qt.AlignmentFlag.AlignRight,
            summary)

        p.end()
