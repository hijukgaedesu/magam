"""개별 프로젝트 카드"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QScrollArea, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

from ..i18n import t, _translations
from ..utils import days_left, urgency, pill_text, motive_text


class ProjectCard(QFrame):
    """진행 중인 프로젝트 한 장"""
    data_changed = Signal()

    PILL_BG = {"urgent": "#fde8e8", "warn": "#fff0d0",
               "safe": "#d6f5ec",   "done": "#e8f5e9"}
    PILL_TC = {"urgent": "#e53935", "warn": "#e8943a",
               "safe": "#3ab89a",   "done": "#388e3c"}

    def __init__(self, T: dict, data: dict,
                 proj_idx: int, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self.proj_idx = proj_idx
        self._collapsed = False
        self._build()

    def _p(self) -> dict:
        return self.data["projects"][self.proj_idx]

    def _build(self) -> None:
        p = self._p()
        days   = days_left(p.get("deadline", "9999-12-31"))
        steps  = p.get("steps", [])
        snames = p.get("step_names", p.get("steps_names", ["완성"]))
        done   = all(steps)
        urg    = urgency(days, done)
        pct    = int(sum(steps) / len(steps) * 100) if steps else 0
        active = next((i for i, s in enumerate(steps) if not s), -1)
        is_overdue = days < 0 and not done

        # ── 기간 경과 계산 ──
        try:
            dl   = datetime.strptime(p["deadline"], "%Y-%m-%d").date()
            crt  = datetime.strptime(
                p.get("created", p["deadline"]), "%Y-%m-%d").date()
            total_days   = max(1, (dl - crt).days)
            elapsed_days = max(0, (date.today() - crt).days)
            time_pct     = min(1.0, elapsed_days / total_days)
            remain_days  = max(0, (dl - date.today()).days)
        except Exception:
            time_pct, remain_days = 0.0, max(0, days)

        unit = _translations.get("_unit_days", "일").strip()

        # ── 카드 스타일 ──
        bar_color = self.T[urg] if urg in self.T else self.T["accent"]
        card_bg   = {
            "urgent": "#fff5f5", "warn": "#fffbf0",
            "safe":   "#f4fdf9", "done": "#f8f8f8",
        }.get(urg, self.T["card"])

        if is_overdue:
            self.setStyleSheet(f"""
                QFrame {{
                    background: #f2f2f2;
                    border-radius: 18px;
                    border: 2px solid #c0c0c0;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {self.T['card']};
                    border-radius: 18px;
                    border: 2px solid {bar_color};
                }}
            """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(2, 2, 2, 2)
        outer.setSpacing(0)

        inner = QFrame()
        inner.setStyleSheet(f"""
            QFrame {{
                background: {('#f0f0f0' if is_overdue else card_bg)};
                border-radius: 16px;
                border: none;
            }}
        """)
        inner_vbox = QVBoxLayout(inner)
        inner_vbox.setContentsMargins(14, 12, 14, 12)
        inner_vbox.setSpacing(8)

        # ── 헤더 ─────────────────────────────────────────
        head = QHBoxLayout()

        # 왼쪽: 색 bar + 제목
        left = QHBoxLayout()
        left.setSpacing(10)
        color_bar = QFrame()
        color_bar.setFixedSize(4, 40)
        color_bar.setStyleSheet(
            f"background: {bar_color if not is_overdue else '#a0a0a0'};"
            f" border-radius: 2px; border: none;")
        left.addWidget(color_bar)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        name_lbl = QLabel(p.get("name", ""))
        name_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 800;"
            f" color: {'#666' if is_overdue else self.T['text']};"
            f" background: transparent;")
        title_vbox.addWidget(name_lbl)

        # 카테고리 + 마감일 행
        dl_row = QHBoxLayout()
        dl_row.setSpacing(6)
        cat = p.get("category", "")
        if cat:
            cat_lbl = QLabel(t(cat))
            cat_lbl.setStyleSheet(f"""
                background: {bar_color if not is_overdue else '#999'};
                color: white;
                border-radius: 7px;
                padding: 1px 6px;
                font-size: 9px;
                font-weight: 700;
            """)
            dl_row.addWidget(cat_lbl)

        if is_overdue:
            dl_txt = f"{t('마감')} {p['deadline']}  •  {abs(days)}{unit} {t('초과')}"
        else:
            dl_txt = f"{t('마감')} {p['deadline']}  •  {days}{unit} {t('남음')}"
        dl_lbl = QLabel(dl_txt)
        dl_lbl.setStyleSheet(
            f"font-size: 10px; color: {self.T['muted']}; background: transparent;")
        dl_row.addWidget(dl_lbl)
        dl_row.addStretch()
        title_vbox.addLayout(dl_row)
        left.addLayout(title_vbox)
        head.addLayout(left)
        head.addStretch()

        # 오른쪽: pill + 버튼들
        right = QHBoxLayout()
        right.setSpacing(4)

        if not is_overdue:
            pill = QLabel(pill_text(days, done))
            pill.setStyleSheet(f"""
                background: {self.PILL_BG.get(urg, '#eee')};
                color: {self.PILL_TC.get(urg, '#333')};
                border-radius: 10px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 700;
            """)
            right.addWidget(pill)
        else:
            ov_lbl = QLabel(t("마감 초과"))
            ov_lbl.setStyleSheet("""
                background: #e0e0e0; color: #888;
                border-radius: 10px; padding: 3px 8px;
                font-size: 11px; font-weight: 700;
            """)
            right.addWidget(ov_lbl)

        # 수정 버튼
        edit_btn = self._icon_btn("✏")
        edit_btn.clicked.connect(self._on_edit)
        right.addWidget(edit_btn)

        if not is_overdue:
            # 접기/펼치기
            self._toggle_btn = self._icon_btn("▲")
            self._toggle_btn.clicked.connect(self._toggle_collapse)
            right.addWidget(self._toggle_btn)

        # 삭제
        del_btn = self._icon_btn("×")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._on_delete)
        right.addWidget(del_btn)

        head.addLayout(right)
        inner_vbox.addLayout(head)

        # ── 본문 (접힘 제어) ──────────────────────────────
        self._body_widget = QWidget()
        self._body_widget.setStyleSheet("background: transparent;")
        body_vbox = QVBoxLayout(self._body_widget)
        body_vbox.setContentsMargins(0, 0, 0, 0)
        body_vbox.setSpacing(6)

        if is_overdue:
            # 초과 카드: 조정/삭제 버튼만
            btn_row = QHBoxLayout()
            reschedule_btn = QPushButton(t("📅 기간 조정하기"))
            reschedule_btn.setObjectName("ghost")
            reschedule_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            reschedule_btn.clicked.connect(self._on_edit)
            btn_row.addWidget(reschedule_btn)

            del2_btn = QPushButton(t("🗑 삭제하기"))
            del2_btn.setObjectName("ghost")
            del2_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del2_btn.clicked.connect(self._on_delete)
            btn_row.addWidget(del2_btn)
            body_vbox.addLayout(btn_row)
        else:
            # ── 기간 경과 바 ──
            tf = QVBoxLayout()
            time_bar = QProgressBar()
            time_bar.setMaximum(100)
            time_bar.setValue(int(time_pct * 100))
            time_bar.setFixedHeight(7)
            time_color = self.T["urgent"] if time_pct >= 0.9 else self.T["muted"]
            time_bar.setStyleSheet(f"""
                QProgressBar {{
                    background: {self.T['accent_light']};
                    border-radius: 3px; border: none;
                }}
                QProgressBar::chunk {{
                    background: {time_color}; border-radius: 3px;
                }}
            """)
            tf.addWidget(time_bar)
            time_lbl = QLabel(
                f"{t('기간')} {int(time_pct*100)}% {t('경과')}  •  "
                f"{remain_days}{unit} {t('남음')}")
            time_lbl.setStyleSheet(
                f"font-size: 10px; color: {time_color if time_pct >= 0.9 else self.T['muted']};"
                f" background: transparent;")
            time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            tf.addWidget(time_lbl)
            body_vbox.addLayout(tf)

            # ── 동기부여 문구 ──
            motive = motive_text(urg)
            mt_lbl = QLabel(motive)
            mt_lbl.setStyleSheet(f"""
                background: {self.PILL_BG.get(urg, '#eee')};
                color: {self.PILL_TC.get(urg, '#555')};
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            """)
            body_vbox.addWidget(mt_lbl)

            # ── 단계 진행 바 ──
            bf = QVBoxLayout()
            prog = QProgressBar()
            prog.setMaximum(100)
            prog.setValue(pct)
            prog.setFixedHeight(9)
            prog.setStyleSheet(f"""
                QProgressBar {{
                    background: {self.T['accent_light']};
                    border-radius: 4px; border: none;
                }}
                QProgressBar::chunk {{
                    background: {bar_color}; border-radius: 4px;
                }}
            """)
            bf.addWidget(prog)
            prog_lbl = QLabel(
                f"{sum(steps)}/{len(steps)} {t('단계')}  {pct}%")
            prog_lbl.setStyleSheet(
                f"font-size: 10px; color: {self.T['muted']}; background: transparent;")
            prog_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            bf.addWidget(prog_lbl)
            body_vbox.addLayout(bf)

            # ── 단계 버튼 (가로 스크롤) ──
            step_scroll = QScrollArea()
            step_scroll.setFixedHeight(44)
            step_scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            step_scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            step_scroll.setFrameShape(QFrame.Shape.NoFrame)
            step_scroll.setStyleSheet("background: transparent; border: none;")

            step_widget = QWidget()
            step_widget.setStyleSheet("background: transparent;")
            step_layout = QHBoxLayout(step_widget)
            step_layout.setContentsMargins(0, 4, 0, 4)
            step_layout.setSpacing(6)

            step_times = p.get("step_times", {})

            for si, sname in enumerate(snames):
                is_done   = steps[si] if si < len(steps) else False
                is_active = (si == active)

                day_lbl_txt = ""
                if is_done and str(si) in step_times:
                    try:
                        end_dt = datetime.fromisoformat(step_times[str(si)])
                        if si == 0:
                            start_dt = datetime.strptime(
                                p.get("created", p["deadline"]), "%Y-%m-%d")
                        elif str(si - 1) in step_times:
                            start_dt = datetime.fromisoformat(
                                step_times[str(si - 1)])
                        else:
                            start_dt = None
                        if start_dt:
                            diff = max(1, (end_dt - start_dt).days + 1)
                            day_lbl_txt = f" {diff}{unit}"
                    except Exception:
                        pass

                if is_done:
                    bg, tc, icon = self.T["accent"], "white", "✓"
                elif is_active:
                    bg, tc, icon = self.T["accent_light"], self.T["accent"], "▶"
                else:
                    bg, tc, icon = self.T["accent_light"], self.T["muted"], "·"

                step_btn = QPushButton(f"{icon} {t(sname)}{day_lbl_txt}")
                step_btn.setFixedHeight(30)
                step_btn.setCursor(
                    Qt.CursorShape.PointingHandCursor if is_active
                    else Qt.CursorShape.ArrowCursor)
                step_btn.setEnabled(is_done or is_active)
                step_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {bg};
                        color: {tc};
                        border: none;
                        border-radius: 14px;
                        padding: 0 12px;
                        font-size: 11px;
                        font-weight: {'800' if is_active else '600'};
                    }}
                    QPushButton:hover {{
                        background: {self.T['accent'] if is_active else bg};
                        color: {'white' if is_active else tc};
                    }}
                """)
                if is_active:
                    step_btn.clicked.connect(
                        lambda checked=False, si=si: self._advance_step(si))
                step_layout.addWidget(step_btn)

            step_layout.addStretch()
            step_scroll.setWidget(step_widget)
            body_vbox.addWidget(step_scroll)

            # ── 다음 단계 힌트 ──
            if not done and active >= 0:
                next_lbl = QLabel(
                    f"{t('▶ 지금 할 단계:')} {t(snames[active])}")
                next_lbl.setStyleSheet(
                    f"font-size: 11px; font-weight: 700;"
                    f" color: {self.T['accent']}; background: transparent;")
                body_vbox.addWidget(next_lbl)

        inner_vbox.addWidget(self._body_widget)
        outer.addWidget(inner)

    # ── 액션 ─────────────────────────────────────────────
    def _icon_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent_light']};
                color: {self.T['muted']};
                border: none; border-radius: 14px;
                font-size: 13px; font-weight: 700;
            }}
            QPushButton:hover {{
                background: {self.T['accent']};
                color: white;
            }}
            QPushButton[objectName="danger"]:hover {{
                background: {self.T['urgent']};
                color: white;
            }}
        """)
        return btn

    def _toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        self._body_widget.setVisible(not self._collapsed)
        self._toggle_btn.setText("▼" if self._collapsed else "▲")

    def _advance_step(self, step_idx: int) -> None:
        p = self._p()
        steps = p.get("steps", [])
        first_unchecked = next((i for i, s in enumerate(steps) if not s), -1)
        if step_idx != first_unchecked:
            return
        steps[step_idx] = True
        p["steps"] = steps
        p.setdefault("step_times", {})[str(step_idx)] = \
            datetime.now().isoformat()
        if all(steps):
            self._show_reward(p.get("name", ""))
        self.data_changed.emit()

    def _on_edit(self) -> None:
        from ..dialogs.deadline_dialog import DeadlineDialog
        dlg = DeadlineDialog(
            self.T, self.data, edit_idx=self.proj_idx, parent=self)
        if dlg.exec():
            self.data_changed.emit()

    def _on_delete(self) -> None:
        p = self._p()
        reply = QMessageBox.question(
            self, t("삭제 확인"),
            f"'{p.get('name', '')}' {t('마감을 삭제할 까요?')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.data["projects"].pop(self.proj_idx)
            self.data_changed.emit()

    def _show_reward(self, name: str) -> None:
        import random
        rewards = ["🎉 참 잘했어요!", "⭐ 완벽해요!", "🎀 마감 클리어!", "🌟 천사인가요?"]
        msg = random.choice(rewards)
        box = QMessageBox(self)
        box.setWindowTitle("완료!")
        box.setText(f"{msg}\n[{name}] {t('모든 단계 완료!')} ✨")
        box.exec()
