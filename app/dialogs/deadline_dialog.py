"""마감 추가 / 편집 다이얼로그"""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QDateEdit, QRadioButton, QButtonGroup,
    QComboBox, QWidget, QFrame, QScrollArea, QCheckBox,
    QDoubleSpinBox, QSpinBox,
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont

from ..i18n import t
from ..utils import STEPS_PRESETS
from ..data import save_data


CATEGORIES = ["개인작", "커미션", "웹툰", "일러스트", "기타"]


class DeadlineDialog(QDialog):
    """마감 추가 또는 편집 다이얼로그.

    새 마감 추가:  DeadlineDialog(T, data, parent=self)
    기존 마감 편집: DeadlineDialog(T, data, parent=self, edit_idx=i)
    """

    saved = Signal()

    def __init__(self, T: dict, data: dict, parent=None, edit_idx: int = -1) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self.edit_idx = edit_idx
        self._editing = (edit_idx >= 0)
        self._step_edits: list[QLineEdit] = []

        self.setWindowTitle(t("마감 편집") if self._editing else t("+ 마감 추가"))
        self.setMinimumWidth(420)
        self.setModal(True)
        self.setStyleSheet(f"QDialog {{ background: {self.T['bg']}; }}")
        self._build()
        if self._editing:
            self._load_existing()

    # ── UI 구성 ───────────────────────────────────────────
    def _build(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background: {self.T['bg']}; border: none; }}")

        content = QWidget()
        content.setStyleSheet(f"background: {self.T['bg']};")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(24, 20, 24, 10)
        vbox.setSpacing(14)

        # 작품 이름
        vbox.addWidget(self._section_label(t("작품 이름")))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(t("예: 리뷰 일러스트"))
        self._name_edit.setFixedHeight(36)
        self._style_input(self._name_edit)
        vbox.addWidget(self._name_edit)

        # 카테고리
        vbox.addWidget(self._section_label(t("카테고리")))
        cat_row = QHBoxLayout()
        cat_row.setSpacing(6)
        self._cat_group = QButtonGroup(self)
        for cat in CATEGORIES:
            rb = QRadioButton(t(cat))
            rb.setStyleSheet(f"""
                QRadioButton {{
                    font-size: 12px;
                    color: {self.T['text']};
                    spacing: 4px;
                }}
                QRadioButton::indicator {{
                    width: 14px; height: 14px;
                    border-radius: 7px;
                    border: 2px solid {self.T['accent']};
                    background: transparent;
                }}
                QRadioButton::indicator:checked {{
                    background: {self.T['accent']};
                    border: 2px solid {self.T['accent']};
                }}
            """)
            self._cat_group.addButton(rb)
            cat_row.addWidget(rb)
            if cat == "개인작":
                rb.setChecked(True)
        cat_row.addStretch()
        vbox.addLayout(cat_row)

        # 마감일
        vbox.addWidget(self._section_label(t("마감일")))
        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDate(QDate.currentDate().addDays(7))
        self._date_edit.setFixedHeight(36)
        self._date_edit.setDisplayFormat("yyyy-MM-dd")
        self._style_input(self._date_edit)
        vbox.addWidget(self._date_edit)

        # 커미션 가격 (커미션 모드일 때만 표시)
        self._price_frame = QWidget()
        price_vbox = QVBoxLayout(self._price_frame)
        price_vbox.setContentsMargins(0, 0, 0, 0)
        price_vbox.setSpacing(6)
        price_vbox.addWidget(self._section_label(t("커미션 가격 (원)")))
        self._price_spin = QDoubleSpinBox()
        self._price_spin.setMinimum(0)
        self._price_spin.setMaximum(99_999_999)
        self._price_spin.setSingleStep(10000)
        self._price_spin.setDecimals(0)
        self._price_spin.setFixedHeight(36)
        self._style_input(self._price_spin)
        price_vbox.addWidget(self._price_spin)
        vbox.addWidget(self._price_frame)
        self._price_frame.setVisible(self.data.get("commission_mode", False))

        # 작업 단계 프리셋
        vbox.addWidget(self._section_label(t("작업 단계 프리셋")))
        self._preset_combo = QComboBox()
        self._preset_combo.setFixedHeight(36)
        self._style_input(self._preset_combo)
        for preset_name in STEPS_PRESETS:
            self._preset_combo.addItem(t(preset_name))
        self._preset_combo.addItem(t("직접 입력"))
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        vbox.addWidget(self._preset_combo)

        # 단계 입력 영역
        self._steps_frame = QFrame()
        self._steps_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.T['accent_light']};
                border-radius: 10px;
                border: none;
            }}
        """)
        self._steps_vbox = QVBoxLayout(self._steps_frame)
        self._steps_vbox.setContentsMargins(12, 10, 12, 10)
        self._steps_vbox.setSpacing(6)
        vbox.addWidget(self._steps_frame)

        # 단계 추가 버튼 (직접 입력 모드)
        self._add_step_btn = QPushButton(t("+ 단계 추가"))
        self._add_step_btn.setFixedHeight(28)
        self._add_step_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_step_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent_light']};
                color: {self.T['accent']};
                border: none;
                border-radius: 8px;
                font-size: 11px;
                font-weight: 700;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: {self.T['accent']};
                color: white;
            }}
        """)
        self._add_step_btn.clicked.connect(self._add_custom_step)
        self._add_step_btn.hide()
        vbox.addWidget(self._add_step_btn, 0, Qt.AlignmentFlag.AlignLeft)

        # 메모
        vbox.addWidget(self._section_label(t("메모 (선택)")))
        self._memo_edit = QTextEdit()
        self._memo_edit.setPlaceholderText(t("간단한 메모..."))
        self._memo_edit.setFixedHeight(72)
        self._memo_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {self.T['accent_light']};
                color: {self.T['text']};
                border: none;
                border-radius: 10px;
                padding: 8px;
                font-size: 12px;
            }}
        """)
        vbox.addWidget(self._memo_edit)

        vbox.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # 하단 버튼
        btn_frame = QFrame()
        btn_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.T['card']};
                border-top: 1px solid {self.T['accent_light']};
            }}
        """)
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(24, 12, 24, 12)
        btn_layout.setSpacing(10)

        cancel_btn = QPushButton(t("취소"))
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent_light']};
                color: {self.T['text']};
                border: none; border-radius: 10px;
                font-size: 13px; padding: 0 16px;
            }}
            QPushButton:hover {{ background: {self.T['muted']}; color: white; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton(t("저장"))
        save_btn.setFixedHeight(36)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent']};
                color: white;
                border: none; border-radius: 10px;
                font-size: 13px; font-weight: 700; padding: 0 20px;
            }}
            QPushButton:hover {{ background: {self.T['accent_dark'] if 'accent_dark' in self.T else self.T['accent']}; }}
        """)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        main_layout.addWidget(btn_frame)

        # 첫 프리셋 적용
        self._on_preset_changed(0)

    # ── 섹션 레이블 헬퍼 ───────────────────────────────────
    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {self.T['muted']};"
            f" background: transparent;")
        return lbl

    def _style_input(self, widget) -> None:
        widget.setStyleSheet(f"""
            QLineEdit, QDateEdit, QComboBox, QDoubleSpinBox, QSpinBox {{
                background: {self.T['accent_light']};
                color: {self.T['text']};
                border: none;
                border-radius: 10px;
                padding: 0 10px;
                font-size: 12px;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QDateEdit::drop-down {{
                border: none;
                padding-right: 8px;
            }}
        """)

    # ── 프리셋 변경 ────────────────────────────────────────
    def _on_preset_changed(self, idx: int) -> None:
        preset_names = list(STEPS_PRESETS.keys())
        is_custom = (idx >= len(preset_names))

        # 기존 단계 위젯 제거
        while self._steps_vbox.count():
            item = self._steps_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._step_edits.clear()

        if is_custom:
            self._add_step_btn.show()
            self._add_custom_step()
        else:
            self._add_step_btn.hide()
            preset_key = preset_names[idx]
            steps = STEPS_PRESETS[preset_key]
            for step_name in steps:
                lbl = QLabel(f"• {t(step_name)}")
                lbl.setStyleSheet(
                    f"font-size: 12px; color: {self.T['text']}; background: transparent;")
                self._steps_vbox.addWidget(lbl)

    def _add_custom_step(self) -> None:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        edit = QLineEdit()
        edit.setPlaceholderText(f"단계 {len(self._step_edits) + 1}")
        edit.setFixedHeight(30)
        edit.setStyleSheet(f"""
            QLineEdit {{
                background: white;
                color: {self.T['text']};
                border: none;
                border-radius: 8px;
                padding: 0 8px;
                font-size: 12px;
            }}
        """)
        row_layout.addWidget(edit)
        self._step_edits.append(edit)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.T['muted']};
                border: none;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{ color: {self.T['urgent']}; }}
        """)
        del_btn.clicked.connect(lambda _, r=row, e=edit: self._remove_step_row(r, e))
        row_layout.addWidget(del_btn)

        self._steps_vbox.addWidget(row)

    def _remove_step_row(self, row: QWidget, edit: QLineEdit) -> None:
        if edit in self._step_edits:
            self._step_edits.remove(edit)
        row.deleteLater()

    # ── 기존 데이터 로드 (편집 모드) ──────────────────────
    def _load_existing(self) -> None:
        p = self.data["projects"][self.edit_idx]
        self._name_edit.setText(p.get("name", ""))

        cat = p.get("category", "개인작")
        for btn in self._cat_group.buttons():
            if btn.text() == t(cat):
                btn.setChecked(True)
                break

        dl_str = p.get("deadline", "")
        if dl_str:
            try:
                d = QDate.fromString(dl_str, "yyyy-MM-dd")
                self._date_edit.setDate(d)
            except Exception:
                pass

        if self.data.get("commission_mode") and "price" in p:
            self._price_spin.setValue(p.get("price", 0))

        self._memo_edit.setPlainText(p.get("memo", ""))

        # 단계 — 직접 입력으로 설정
        step_names = p.get("step_names", [])
        if step_names:
            # 직접 입력 모드 선택
            self._preset_combo.setCurrentIndex(self._preset_combo.count() - 1)
            # 기존 단계들 채우기
            while self._steps_vbox.count():
                item = self._steps_vbox.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._step_edits.clear()
            for name in step_names:
                self._add_custom_step()
                self._step_edits[-1].setText(name)

    # ── 저장 ──────────────────────────────────────────────
    def _save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._name_edit.setFocus()
            return

        # 카테고리
        cat = "개인작"
        checked_btn = self._cat_group.checkedButton()
        if checked_btn:
            # 한국어로 역매핑
            btn_text = checked_btn.text()
            for orig in CATEGORIES:
                if t(orig) == btn_text:
                    cat = orig
                    break

        # 마감일
        deadline = self._date_edit.date().toString("yyyy-MM-dd")

        # 단계 이름 & 초기값
        preset_names = list(STEPS_PRESETS.keys())
        idx = self._preset_combo.currentIndex()
        is_custom = (idx >= len(preset_names))

        if is_custom:
            step_names = [e.text().strip() or f"단계{i+1}"
                          for i, e in enumerate(self._step_edits)]
        else:
            step_names = list(STEPS_PRESETS[preset_names[idx]])

        if self._editing:
            # 기존 단계 진행 상태 최대한 유지
            old_steps = self.data["projects"][self.edit_idx].get("steps", [])
            new_steps = old_steps[:len(step_names)]
            if len(new_steps) < len(step_names):
                new_steps += [False] * (len(step_names) - len(new_steps))
        else:
            new_steps = [False] * len(step_names)

        proj: dict = {
            "name":       name,
            "category":   cat,
            "deadline":   deadline,
            "step_names": step_names,
            "steps":      new_steps,
            "memo":       self._memo_edit.toPlainText().strip(),
        }

        if self.data.get("commission_mode"):
            proj["price"] = self._price_spin.value()

        if self._editing:
            self.data["projects"][self.edit_idx] = proj
        else:
            self.data.setdefault("projects", []).append(proj)

        save_data(self.data)
        self.saved.emit()
        self.accept()
