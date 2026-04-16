"""우측 패널 — 포커스 타이머 · 오늘 통계 · TODO"""
from __future__ import annotations

import os
import sys
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QFrame, QPushButton, QProgressBar, QLineEdit, QCheckBox,
    QSizePolicy, QInputDialog,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from ..i18n import t
from ..data import save_data
from ..utils import days_left


# ──────────────────────────────────────────────────────────────────────────────
# 목표 작업량 계산 다이얼로그
# ──────────────────────────────────────────────────────────────────────────────
class _GoalCalcDialog:
    """권장 일일 작업량을 계산해서 보여주는 다이얼로그"""

    def __init__(self, T: dict, data: dict, parent=None) -> None:
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame
        from PySide6.QtCore import Qt

        self.chosen_goal: float | None = None
        self._dlg = QDialog(parent)
        self._dlg.setWindowTitle(t("목표 작업량 계산"))
        self._dlg.setMinimumWidth(340)
        self._dlg.setStyleSheet(f"background: {T['bg']};")

        vbox = QVBoxLayout(self._dlg)
        vbox.setContentsMargins(24, 20, 24, 20)
        vbox.setSpacing(10)

        title = QLabel(t("권장 일일 작업량"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"font-size: 15px; font-weight: 800; color: {T['text']}; background: transparent;")
        vbox.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {T['accent_light']}; max-height:1px;")
        vbox.addWidget(sep)

        # 프로젝트별 권장 계산
        projs = data.get("projects", [])
        active = [(p, days_left(p.get("deadline", "9999-12-31")))
                  for p in projs if not all(p.get("steps", []))]
        active = [(p, d) for p, d in active if d > 0]

        total_recommended = 0.0
        if active:
            for p, d in active:
                steps = p.get("steps", [])
                remaining = steps.count(False) if steps else 1
                daily_h = round(remaining * 1.0 / max(1, d), 1)
                total_recommended += daily_h
                row_lbl = QLabel(
                    f"• {p.get('name','')[:16]}  →  "
                    f"{t('하루')} {daily_h:.1f}h  (D-{d})"
                )
                row_lbl.setStyleSheet(
                    f"font-size: 11px; color: {T['text']}; background: transparent;")
                vbox.addWidget(row_lbl)
        else:
            empty = QLabel(t("진행 중인 마감이 없어요."))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"font-size: 12px; color: {T['muted']}; background: transparent;")
            vbox.addWidget(empty)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"background: {T['accent_light']}; max-height:1px;")
        vbox.addWidget(sep2)

        # 합산 권장
        sum_lbl = QLabel(f"{t('합산 권장')}: {total_recommended:.1f}h / {t('하루')}")
        sum_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {T['accent']}; background: transparent;")
        vbox.addWidget(sum_lbl)

        # 최근 7일 평균
        from datetime import date as _date, timedelta
        daily_work = data.get("daily_work", {})
        today = _date.today()
        week_vals = [daily_work.get((today - timedelta(days=i)).isoformat(), 0) for i in range(7)]
        avg7 = sum(week_vals) / 7
        avg_lbl = QLabel(f"{t('최근 7일 평균')}: {avg7:.1f}h / {t('하루')}")
        avg_lbl.setStyleSheet(
            f"font-size: 11px; color: {T['muted']}; background: transparent;")
        vbox.addWidget(avg_lbl)

        # 제안
        suggested = round(max(total_recommended, 0.5), 1)
        suggest_lbl = QLabel(f"→  {suggested:.1f}h  {t('을 목표로 설정할까요?')}")
        suggest_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        suggest_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {T['text']}; background: transparent;"
            f" padding: 6px 0;")
        vbox.addWidget(suggest_lbl)

        set_btn = QPushButton(t("이 값으로 설정"))
        set_btn.setFixedHeight(38)
        set_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T['accent']};
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 13px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: {T['safe']};
            }}
        """)
        set_btn.clicked.connect(lambda: self._set(suggested))
        vbox.addWidget(set_btn)

        self._suggested = suggested

    def _set(self, val: float) -> None:
        self.chosen_goal = val
        self._dlg.accept()

    def exec(self) -> bool:
        return self._dlg.exec() == 1


# ──────────────────────────────────────────────────────────────────────────────
# CS 트래커 — 포그라운드 창 감지 (Windows 전용)
# ──────────────────────────────────────────────────────────────────────────────
def _get_foreground_process_name() -> str:
    """현재 포그라운드 창의 프로세스 파일명 반환 (Windows 전용). 실패 시 빈 문자열."""
    if sys.platform != "win32":
        return ""
    try:
        import ctypes
        import ctypes.wintypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return ""
        pid = ctypes.wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h_proc = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
        if not h_proc:
            return ""
        buf = (ctypes.c_wchar * 512)()
        size = ctypes.wintypes.DWORD(512)
        ctypes.windll.kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size))
        ctypes.windll.kernel32.CloseHandle(h_proc)
        return os.path.basename(buf.value).lower()
    except Exception:
        return ""


# ──────────────────────────────────────────────────────────────────────────────
# 포커스 타이머 카드
# ──────────────────────────────────────────────────────────────────────────────
class _TimerCard(QFrame):
    """뽀모도로 스타일 포커스 타이머"""

    work_logged = Signal(float)   # 완료 시 작업 시간(시간) emit

    _MODES = [
        (t("5분"),  5 * 60),
        (t("25분"), 25 * 60),
        (t("50분"), 50 * 60),
    ]

    def __init__(self, T: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self._total   = 25 * 60
        self._remain  = self._total
        self._running = False
        self._mode_idx = 1          # 기본 25분

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

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
        vbox.setContentsMargins(16, 14, 16, 16)
        vbox.setSpacing(10)

        # 헤더
        hdr = QLabel(t("⏱ 포커스 타이머"))
        hdr.setStyleSheet(
            f"font-size: 13px; font-weight: 800; color: {self.T['text']};"
            f" background: transparent;")
        vbox.addWidget(hdr)

        # 모드 버튼 행
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        self._mode_btns: list[QPushButton] = []
        for i, (label, secs) in enumerate(self._MODES):
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._set_mode(idx))
            self._mode_btns.append(btn)
            mode_row.addWidget(btn)
        vbox.addLayout(mode_row)
        self._refresh_mode_btns()

        # 시간 표시
        self._time_lbl = QLabel(self._fmt_time(self._remain))
        self._time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_lbl.setStyleSheet(
            f"font-size: 42px; font-weight: 900; color: {self.T['accent']};"
            f" background: transparent; letter-spacing: 2px;")
        vbox.addWidget(self._time_lbl)

        # 프로그레스 바
        self._prog = QProgressBar()
        self._prog.setMaximum(self._total)
        self._prog.setValue(self._total)
        self._prog.setFixedHeight(6)
        self._prog.setTextVisible(False)
        self._prog.setStyleSheet(f"""
            QProgressBar {{
                background: {self.T['accent_light']};
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: {self.T['accent']};
                border-radius: 3px;
            }}
        """)
        vbox.addWidget(self._prog)

        # 버튼 행
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._start_btn = QPushButton(t("▶ 시작"))
        self._start_btn.setObjectName("accent")
        self._start_btn.setFixedHeight(34)
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.clicked.connect(self._toggle)
        btn_row.addWidget(self._start_btn)

        reset_btn = QPushButton(t("↺ 리셋"))
        reset_btn.setFixedHeight(34)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(reset_btn)

        vbox.addLayout(btn_row)

        # 완료 레이블 (숨김)
        self._done_lbl = QLabel(t("🎉 집중 완료!"))
        self._done_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {self.T['safe']};"
            f" background: transparent;")
        self._done_lbl.hide()
        vbox.addWidget(self._done_lbl)

    def _refresh_mode_btns(self) -> None:
        for i, btn in enumerate(self._mode_btns):
            active = (i == self._mode_idx)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.T['accent'] if active else self.T['accent_light']};
                    color: {'white' if active else self.T['text']};
                    border: none;
                    border-radius: 13px;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background: {self.T['accent']};
                    color: white;
                }}
            """)

    def _set_mode(self, idx: int) -> None:
        if self._running:
            return
        self._mode_idx = idx
        self._total  = self._MODES[idx][1]
        self._remain = self._total
        self._prog.setMaximum(self._total)
        self._update_display()
        self._refresh_mode_btns()
        self._done_lbl.hide()

    def _toggle(self) -> None:
        if self._running:
            self._timer.stop()
            self._running = False
            self._start_btn.setText(t("▶ 재개"))
        else:
            self._timer.start()
            self._running = True
            self._start_btn.setText(t("⏸ 일시정지"))
            self._done_lbl.hide()

    def _reset(self) -> None:
        self._timer.stop()
        self._running = False
        self._remain  = self._total
        self._start_btn.setText(t("▶ 시작"))
        self._update_display()
        self._done_lbl.hide()

    def _tick(self) -> None:
        self._remain -= 1
        self._update_display()
        if self._remain <= 0:
            self._timer.stop()
            self._running = False
            self._start_btn.setText(t("▶ 시작"))
            self._done_lbl.show()
            # 작업 시간 기록
            hours = self._total / 3600
            self.work_logged.emit(hours)

    def _update_display(self) -> None:
        self._time_lbl.setText(self._fmt_time(self._remain))
        self._prog.setValue(max(0, self._remain))

    @staticmethod
    def _fmt_time(secs: int) -> str:
        m, s = divmod(max(0, secs), 60)
        return f"{m:02d}:{s:02d}"


# ──────────────────────────────────────────────────────────────────────────────
# 오늘 통계 카드
# ──────────────────────────────────────────────────────────────────────────────
class _TodayCard(QFrame):
    """오늘 작업 시간 + 목표 진행률"""

    log_requested = Signal(float)   # 시간 기록 요청

    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
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
        vbox.setContentsMargins(16, 14, 16, 16)
        vbox.setSpacing(10)

        # 헤더
        hdr = QLabel(t("📊 오늘의 작업량"))
        hdr.setStyleSheet(
            f"font-size: 13px; font-weight: 800; color: {self.T['text']};"
            f" background: transparent;")
        vbox.addWidget(hdr)

        # 작업 시간
        time_row = QHBoxLayout()
        time_lbl = QLabel(t("오늘"))
        time_lbl.setStyleSheet(
            f"font-size: 11px; color: {self.T['muted']}; background: transparent;")
        time_row.addWidget(time_lbl)
        time_row.addStretch()

        self._hours_lbl = QLabel("0.0h")
        self._hours_lbl.setStyleSheet(
            f"font-size: 22px; font-weight: 800; color: {self.T['accent']};"
            f" background: transparent;")
        time_row.addWidget(self._hours_lbl)
        vbox.addLayout(time_row)

        # 목표 설정 행
        goal_row = QHBoxLayout()
        goal_lbl = QLabel(t("목표"))
        goal_lbl.setStyleSheet(
            f"font-size: 11px; color: {self.T['muted']}; background: transparent;")
        goal_row.addWidget(goal_lbl)

        self._goal_edit = QLineEdit(str(self.data.get("daily_goal", 4)))
        self._goal_edit.setFixedWidth(44)
        self._goal_edit.setFixedHeight(26)
        self._goal_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._goal_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {self.T['accent_light']};
                color: {self.T['text']};
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
            }}
        """)
        self._goal_edit.editingFinished.connect(self._save_goal)
        goal_row.addWidget(self._goal_edit)

        unit_lbl = QLabel(t("h"))
        unit_lbl.setStyleSheet(
            f"font-size: 11px; color: {self.T['muted']}; background: transparent;")
        goal_row.addWidget(unit_lbl)

        # 계산 버튼
        calc_btn = QPushButton(t("계산"))
        calc_btn.setFixedHeight(24)
        calc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        calc_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent_light']};
                color: {self.T['accent']};
                border: none;
                border-radius: 8px;
                padding: 0 8px;
                font-size: 10px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {self.T['accent']};
                color: white;
            }}
        """)
        calc_btn.clicked.connect(self._open_calc)
        goal_row.addWidget(calc_btn)

        # 저장 버튼
        save_goal_btn = QPushButton(t("저장"))
        save_goal_btn.setFixedHeight(24)
        save_goal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_goal_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 8px;
                font-size: 10px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """)
        save_goal_btn.clicked.connect(self._save_goal)
        goal_row.addWidget(save_goal_btn)

        goal_row.addStretch()
        vbox.addLayout(goal_row)

        # 목표 진행 바
        self._goal_bar = QProgressBar()
        self._goal_bar.setMaximum(100)
        self._goal_bar.setValue(0)
        self._goal_bar.setFixedHeight(8)
        self._goal_bar.setTextVisible(False)
        self._goal_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {self.T['accent_light']};
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: {self.T['safe']};
                border-radius: 4px;
            }}
        """)
        vbox.addWidget(self._goal_bar)

        # 기록하기 버튼
        log_btn = QPushButton(t("+ 작업 시간 기록"))
        log_btn.setObjectName("accent")
        log_btn.setFixedHeight(32)
        log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        log_btn.clicked.connect(self._request_log)
        vbox.addWidget(log_btn)

        # 프로그램 추적 중 실시간 표시 레이블
        self._tracker_lbl = QLabel("")
        self._tracker_lbl.setStyleSheet(
            f"font-size: 10px; color: {self.T['safe']}; background: transparent;"
            f" padding: 2px 0;")
        self._tracker_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tracker_lbl.hide()
        vbox.addWidget(self._tracker_lbl)

        self._refresh_display()

    def _open_calc(self) -> None:
        dlg = _GoalCalcDialog(self.T, self.data, self.window())
        if dlg.exec():
            new_goal = dlg.chosen_goal
            if new_goal and new_goal > 0:
                self.data["daily_goal"] = new_goal
                save_data(self.data)
                self._goal_edit.setText(f"{new_goal:.1f}")
                self._refresh_display()

    def _save_goal(self) -> None:
        try:
            val = float(self._goal_edit.text())
            if val > 0:
                self.data["daily_goal"] = val
                save_data(self.data)
                self._refresh_display()
        except ValueError:
            self._goal_edit.setText(str(self.data.get("daily_goal", 4)))

    def _request_log(self) -> None:
        parent_widget = self.window()
        val, ok = QInputDialog.getDouble(
            parent_widget,
            t("작업 시간 기록"),
            t("오늘 작업한 시간을 입력하세요 (예: 3.5)"),  # 번역 키 일치
            0.5, 0.0, 24.0, 1,
        )
        if ok and val > 0:
            today_key = date.today().isoformat()
            current = self.data.get("daily_work", {}).get(today_key, 0)
            self.data.setdefault("daily_work", {})[today_key] = current + val
            save_data(self.data)
            self.log_requested.emit(val)
            self._refresh_display()

    def _refresh_display(self) -> None:
        today_key = date.today().isoformat()
        hours = self.data.get("daily_work", {}).get(today_key, 0)
        self._hours_lbl.setText(f"{hours:.1f}h")

        goal = self.data.get("daily_goal", 4)
        pct  = min(100, int(hours / goal * 100)) if goal > 0 else 0
        self._goal_bar.setValue(pct)

        # 색상: 100% 이상이면 safe, 50% 이상이면 warn, 이하이면 accent
        if pct >= 100:
            color = self.T["safe"]
        elif pct >= 50:
            color = self.T["warn"]
        else:
            color = self.T["accent"]

        self._goal_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {self.T['accent_light']};
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: {color};
                border-radius: 4px;
            }}
        """)

    def show_tracker(self, active: bool, text: str) -> None:
        """프로그램 추적 중 실시간 표시"""
        if active and text:
            self._tracker_lbl.setText(text)
            self._tracker_lbl.show()
        else:
            self._tracker_lbl.hide()

    def refresh(self) -> None:
        goal = self.data.get("daily_goal", 4)
        self._goal_edit.setText(str(goal))
        self._refresh_display()


# ──────────────────────────────────────────────────────────────────────────────
# TODO 카드
# ──────────────────────────────────────────────────────────────────────────────
class _TodoCard(QFrame):
    """체크리스트 TODO"""

    data_changed = Signal()

    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
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

        self._vbox = QVBoxLayout(self)
        self._vbox.setContentsMargins(16, 14, 16, 16)
        self._vbox.setSpacing(8)

        # 헤더
        hdr_row = QHBoxLayout()
        hdr = QLabel(t("✅ 할 일"))
        hdr.setStyleSheet(
            f"font-size: 13px; font-weight: 800; color: {self.T['text']};"
            f" background: transparent;")
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()

        add_btn = QPushButton(t("+ 추가"))
        add_btn.setFixedHeight(24)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent_light']};
                color: {self.T['accent']};
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
        add_btn.clicked.connect(self._add_todo)
        hdr_row.addWidget(add_btn)
        self._vbox.addLayout(hdr_row)

        # 항목 컨테이너
        self._items_widget = QWidget()
        self._items_widget.setStyleSheet("background: transparent;")
        self._items_layout = QVBoxLayout(self._items_widget)
        self._items_layout.setContentsMargins(0, 0, 0, 0)
        self._items_layout.setSpacing(4)
        self._vbox.addWidget(self._items_widget)

        # 완료 항목 정리 버튼
        self._clean_btn = QPushButton(t("완료 항목 정리"))
        self._clean_btn.setFixedHeight(26)
        self._clean_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clean_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.T['muted']};
                border: none;
                font-size: 10px;
                text-decoration: underline;
            }}
            QPushButton:hover {{
                color: {self.T['text']};
            }}
        """)
        self._clean_btn.clicked.connect(self._clean_done)
        self._vbox.addWidget(self._clean_btn, 0, Qt.AlignmentFlag.AlignRight)

        self._refresh_items()

    def _refresh_items(self) -> None:
        # 기존 위젯 제거
        while self._items_layout.count():
            item = self._items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        todos = self.data.get("todos", [])

        if not todos:
            empty = QLabel(t("할 일을 추가해봐요 🌸"))
            empty.setStyleSheet(
                f"font-size: 11px; color: {self.T['muted']}; background: transparent;"
                f" padding: 8px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._items_layout.addWidget(empty)
            self._clean_btn.hide()
            return

        has_done = any(item.get("done") for item in todos)
        if has_done:
            self._clean_btn.show()
        else:
            self._clean_btn.hide()

        for i, todo in enumerate(todos):
            row = self._make_todo_row(i, todo)
            self._items_layout.addWidget(row)

    def _make_todo_row(self, idx: int, todo: dict) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        cb = QCheckBox()
        cb.setChecked(todo.get("done", False))
        cb.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 2px solid {self.T['accent']};
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {self.T['accent']};
                border: 2px solid {self.T['accent']};
                image: none;
            }}
        """)
        cb.stateChanged.connect(lambda state, i=idx: self._toggle_todo(i, state))
        layout.addWidget(cb)

        text_style = (
            f"font-size: 12px; color: {self.T['muted']}; background: transparent;"
            f" text-decoration: line-through;" if todo.get("done")
            else f"font-size: 12px; color: {self.T['text']}; background: transparent;"
        )
        lbl = QLabel(todo.get("text", ""))
        lbl.setStyleSheet(text_style)
        lbl.setWordWrap(True)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(lbl)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.T['muted']};
                border: none;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                color: {self.T['urgent']};
            }}
        """)
        del_btn.clicked.connect(lambda _, i=idx: self._delete_todo(i))
        layout.addWidget(del_btn)

        return row

    def _toggle_todo(self, idx: int, state: int) -> None:
        todos = self.data.setdefault("todos", [])
        if idx < len(todos):
            todos[idx]["done"] = bool(state)
            save_data(self.data)
            self.data_changed.emit()
            self._refresh_items()

    def _delete_todo(self, idx: int) -> None:
        todos = self.data.get("todos", [])
        if idx < len(todos):
            todos.pop(idx)
            save_data(self.data)
            self.data_changed.emit()
            self._refresh_items()

    def _add_todo(self) -> None:
        text, ok = QInputDialog.getText(
            self.window(), t("할 일 추가"), t("할 일을 입력하세요:")
        )
        if ok and text.strip():
            self.data.setdefault("todos", []).append(
                {"text": text.strip(), "done": False}
            )
            save_data(self.data)
            self.data_changed.emit()
            self._refresh_items()

    def _clean_done(self) -> None:
        todos = self.data.get("todos", [])
        self.data["todos"] = [t for t in todos if not t.get("done")]
        save_data(self.data)
        self.data_changed.emit()
        self._refresh_items()

    def refresh(self) -> None:
        self._refresh_items()


# ──────────────────────────────────────────────────────────────────────────────
# 작업 시작하기 카드 (프로그램 실행 버튼)
# ──────────────────────────────────────────────────────────────────────────────
class _LaunchCard(QFrame):
    """작업 프로그램 실행 버튼 카드"""

    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
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
        vbox.setContentsMargins(16, 14, 16, 16)
        vbox.setSpacing(8)

        # 헤더 행
        hdr_row = QHBoxLayout()
        hdr = QLabel(t("🎨 작업 시작하기"))
        hdr.setStyleSheet(
            f"font-size: 13px; font-weight: 800; color: {self.T['text']};"
            f" background: transparent;")
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()

        # 추적 상태 dot (cs_tracker_enabled 여부)
        self._dot = QFrame()
        self._dot.setFixedSize(8, 8)
        self._dot.setStyleSheet(
            f"background: {self.T['muted']}; border-radius: 4px; border: none;")
        hdr_row.addWidget(self._dot)
        vbox.addLayout(hdr_row)

        # 큰 실행 버튼
        self._launch_btn = QPushButton()
        self._launch_btn.setFixedHeight(70)
        self._launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._launch_btn.clicked.connect(self._launch)
        vbox.addWidget(self._launch_btn)

        # 경로 설정 버튼
        path_row = QHBoxLayout()
        self._path_lbl = QLabel()
        self._path_lbl.setStyleSheet(
            f"font-size: 9px; color: {self.T['muted']}; background: transparent;")
        self._path_lbl.setWordWrap(True)
        path_row.addWidget(self._path_lbl)
        path_row.addStretch()

        pick_btn = QPushButton(t("경로 설정"))
        pick_btn.setFixedHeight(22)
        pick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pick_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent_light']};
                color: {self.T['accent']};
                border: none;
                border-radius: 8px;
                padding: 0 8px;
                font-size: 10px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {self.T['accent']};
                color: white;
            }}
        """)
        pick_btn.clicked.connect(self._pick_path)
        path_row.addWidget(pick_btn)
        vbox.addLayout(path_row)

        self._refresh_btn()

    def _refresh_btn(self) -> None:
        path = self.data.get("cs_launch_path", "")
        cs_enabled = self.data.get("cs_tracker_enabled", False)

        dot_color = self.T["safe"] if cs_enabled else self.T["muted"]
        self._dot.setStyleSheet(
            f"background: {dot_color}; border-radius: 4px; border: none;")

        if path and os.path.exists(path):
            name = os.path.splitext(os.path.basename(path))[0]
            self._launch_btn.setText(f"▶  {t('작업 시작하기')}\n{name}")
            self._path_lbl.setText(path)
        else:
            self._launch_btn.setText(f"▶  {t('작업 시작하기')}")
            self._path_lbl.setText(t("경로를 설정해주세요"))

        cs_on = self.data.get("cs_tracker_enabled", False)
        dot_txt = "● " if cs_on else ""
        self._launch_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent']};
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 14px;
                font-weight: 900;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background: {self.T['safe']};
            }}
            QPushButton:pressed {{
                background: {self.T['sidebar_btn']};
            }}
        """)

    def _launch(self) -> None:
        path = self.data.get("cs_launch_path", "")
        if path and os.path.exists(path):
            import subprocess
            try:
                subprocess.Popen([path])
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, t("오류"), str(e))
        else:
            self._pick_path()

    def _pick_path(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, t("프로그램 실행 파일 선택"), "",
            "Executable (*.exe);;All Files (*)"
        )
        if path:
            self.data["cs_launch_path"] = path
            save_data(self.data)
            self._refresh_btn()

    def refresh(self) -> None:
        self._refresh_btn()


# ──────────────────────────────────────────────────────────────────────────────
# 우측 패널 메인
# ──────────────────────────────────────────────────────────────────────────────
class RightPanel(QWidget):
    data_changed = Signal()

    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self.setFixedWidth(290)
        self._build()

    def _build(self) -> None:
        self.setStyleSheet(f"background: {self.T['bg']};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(12, 14, 12, 40)
        vbox.setSpacing(12)

        # ── 포커스 타이머 ─────────────────────────────────
        self._timer_card = _TimerCard(self.T)
        self._timer_card.work_logged.connect(self._on_timer_done)
        vbox.addWidget(self._timer_card)

        # ── 오늘 작업 통계 ────────────────────────────────
        self._today_card = _TodayCard(self.T, self.data)
        self._today_card.log_requested.connect(self._on_log_requested)
        vbox.addWidget(self._today_card)

        # ── 작업 시작하기 ─────────────────────────────────
        self._launch_card = _LaunchCard(self.T, self.data)
        vbox.addWidget(self._launch_card)

        # ── TODO ─────────────────────────────────────────
        self._todo_card = _TodoCard(self.T, self.data)
        self._todo_card.data_changed.connect(self.data_changed)
        vbox.addWidget(self._todo_card)

        vbox.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

        # ── CS 트래커 폴링 타이머 (2초 간격) ─────────────
        self._cs_accumulated: dict[str, int] = {}   # prog -> seconds
        self._cs_tick_count = 0                      # 30틱(=60초)마다 저장
        self._cs_poll_timer = QTimer(self)
        self._cs_poll_timer.setInterval(2000)
        self._cs_poll_timer.timeout.connect(self._cs_poll)
        if self.data.get("cs_tracker_enabled", False):
            self._cs_poll_timer.start()

    # ── 시그널 핸들러 ──────────────────────────────────────
    def _on_timer_done(self, hours: float) -> None:
        """타이머 완료 시 작업 시간 자동 기록"""
        today_key = date.today().isoformat()
        current = self.data.get("daily_work", {}).get(today_key, 0)
        self.data.setdefault("daily_work", {})[today_key] = current + hours
        save_data(self.data)
        self._today_card.refresh()
        self.data_changed.emit()

    def _on_log_requested(self, hours: float) -> None:
        self.data_changed.emit()

    # ── CS 트래커 폴링 ────────────────────────────────────
    def _cs_poll(self) -> None:
        """2초마다 포그라운드 창 확인, 30틱(60초)마다 데이터 저장"""
        proc = _get_foreground_process_name()
        is_tracking = False
        if proc:
            # tracked_programs는 {"name": ..., "exe": ...} dict 리스트
            tracked_exes = [
                p["exe"].strip().lower()
                for p in self.data.get("tracked_programs", [])
                if isinstance(p, dict) and p.get("exe")
            ]
            if any(exe in proc for exe in tracked_exes):
                self._cs_accumulated[proc] = self._cs_accumulated.get(proc, 0) + 2
                is_tracking = True

        # 실시간 표시 업데이트
        self._update_tracker_display(is_tracking, proc if is_tracking else "")

        self._cs_tick_count += 1
        if self._cs_tick_count >= 30:
            self._cs_tick_count = 0
            self._cs_flush()

    def _update_tracker_display(self, is_tracking: bool, proc_name: str = "") -> None:
        """_TodayCard의 추적 레이블을 실시간 업데이트"""
        if not hasattr(self, "_today_card"):
            return
        today_key = date.today().isoformat()
        # 저장된 시간 + 현재 세션 누적 시간 합산
        saved_secs = 0
        cs_log = self.data.get("cs_log", {}).get(today_key, {})
        for secs in cs_log.values():
            saved_secs += secs
        session_secs = sum(self._cs_accumulated.values())
        total_secs = saved_secs + session_secs

        if is_tracking and proc_name:
            prog_name = proc_name.replace(".exe", "")
            h = total_secs // 3600
            m = (total_secs % 3600) // 60
            s = total_secs % 60
            self._today_card.show_tracker(True, f"● {t('작업 중')}  {prog_name}  {h:02d}:{m:02d}:{s:02d}")
        else:
            self._today_card.show_tracker(False, "")

    def _cs_flush(self) -> None:
        """누적된 CS 시간을 data에 기록하고 저장"""
        if not self._cs_accumulated:
            return
        today_key = date.today().isoformat()
        today_log = self.data.setdefault("cs_log", {}).setdefault(today_key, {})
        total_new_secs = 0
        for prog, secs in self._cs_accumulated.items():
            today_log[prog] = today_log.get(prog, 0) + secs
            total_new_secs += secs
        self._cs_accumulated.clear()

        if total_new_secs > 0:
            hours = total_new_secs / 3600
            current = self.data.get("daily_work", {}).get(today_key, 0)
            self.data.setdefault("daily_work", {})[today_key] = current + hours

        save_data(self.data)
        self._today_card.refresh()
        self.data_changed.emit()

    def refresh(self) -> None:
        # CS 트래커 활성화 상태 동기화
        enabled = self.data.get("cs_tracker_enabled", False)
        if enabled and not self._cs_poll_timer.isActive():
            self._cs_poll_timer.start()
        elif not enabled and self._cs_poll_timer.isActive():
            self._cs_poll_timer.stop()
            self._cs_flush()

        self._today_card.refresh()
        self._launch_card.refresh()
        self._todo_card.refresh()

    def stop_threads(self) -> None:
        """앱 종료 시 타이머 정지 및 누적 데이터 저장"""
        self._cs_poll_timer.stop()
        self._cs_flush()