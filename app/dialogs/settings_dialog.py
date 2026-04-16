"""설정 다이얼로그"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget, QScrollArea, QComboBox, QCheckBox,
    QLineEdit, QTabWidget, QFileDialog, QMessageBox,
    QColorDialog, QSlider,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from ..i18n import t, set_language
from ..theme import THEMES, get_theme
from ..data import save_data, DATA_PATH


LANG_OPTIONS = [
    ("한국어", "ko"),
    ("English", "en"),
    ("日本語", "ja"),
    ("中文",   "zh"),
]

FONT_OPTIONS = [
    ("시스템 기본", ""),
    ("Malgun Gothic", "Malgun Gothic"),
    ("나눔고딕", "NanumGothic"),
    ("돋움", "Dotum"),
    ("굴림", "Gulim"),
]


class SettingsDialog(QDialog):
    settings_changed = Signal()   # 언어/테마 변경 → 전체 리빌드 필요

    def __init__(self, T: dict, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.T = T
        self.data = data
        self.setWindowTitle(t("⚙ 설정"))
        self.setMinimumSize(440, 540)
        self.resize(480, 600)
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
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {self.T['accent']};
                color: white;
                font-weight: 700;
            }}
        """)

        tabs.addTab(self._make_appearance_tab(), t("외관"))
        tabs.addTab(self._make_features_tab(), t("기능"))
        tabs.addTab(self._make_data_tab(), t("데이터"))

        vbox.addWidget(tabs)

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
        btn_layout.setSpacing(8)

        cancel_btn = QPushButton(t("취소"))
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton(t("저장 & 적용"))
        save_btn.setObjectName("accent")
        save_btn.setFixedHeight(36)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        vbox.addWidget(btn_frame)

    # ── 외관 탭 ───────────────────────────────────────────
    def _make_appearance_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {self.T['bg']};")
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(20, 16, 20, 16)
        vbox.setSpacing(14)

        # 언어
        vbox.addWidget(self._sec_lbl(t("언어")))
        self._lang_combo = QComboBox()
        self._lang_combo.setFixedHeight(34)
        self._style_combo(self._lang_combo)
        cur_lang = self.data.get("language", "ko")
        for i, (display, code) in enumerate(LANG_OPTIONS):
            self._lang_combo.addItem(display)
            if code == cur_lang:
                self._lang_combo.setCurrentIndex(i)
        vbox.addWidget(self._lang_combo)

        # 테마
        vbox.addWidget(self._sec_lbl(t("테마")))
        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)
        self._theme_btns: dict[str, QPushButton] = {}
        cur_theme = self.data.get("theme", "lavender")
        theme_labels = {
            "lavender": "💜 라벤더",
            "pink":     "🌸 핑크",
            "sky":      "💙 스카이",
            "mint":     "🌿 민트",
            "커스텀":   "🎨 커스텀",
        }
        for key, label in theme_labels.items():
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setChecked(key == cur_theme)
            btn.clicked.connect(lambda _, k=key: self._select_theme(k))
            self._theme_btns[key] = btn
            theme_row.addWidget(btn)
        theme_row.addStretch()
        vbox.addLayout(theme_row)
        self._refresh_theme_btns()

        # 커스텀 색상 (커스텀 테마일 때)
        self._custom_color_row = QHBoxLayout()
        self._custom_color_row.setSpacing(8)
        custom_lbl = QLabel(t("기준 색상:"))
        custom_lbl.setStyleSheet(
            f"font-size: 12px; color: {self.T['text']}; background: transparent;")
        self._custom_color_row.addWidget(custom_lbl)

        self._color_preview = QFrame()
        self._color_preview.setFixedSize(28, 28)
        cur_color = self.data.get("custom_color", "#9b7fe8")
        self._color_preview.setStyleSheet(
            f"background: {cur_color}; border-radius: 14px; border: none;")
        self._custom_color_row.addWidget(self._color_preview)

        pick_btn = QPushButton(t("색상 선택"))
        pick_btn.setFixedHeight(28)
        pick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pick_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent_light']};
                color: {self.T['accent']};
                border: none;
                border-radius: 10px;
                padding: 0 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {self.T['accent']};
                color: white;
            }}
        """)
        pick_btn.clicked.connect(self._pick_color)
        self._custom_color_row.addWidget(pick_btn)
        self._custom_color_row.addStretch()

        color_widget = QWidget()
        color_widget.setStyleSheet("background: transparent;")
        color_widget.setLayout(self._custom_color_row)
        vbox.addWidget(color_widget)

        # 포인트 색상 (safe/warn/urgent)
        self._point_colors = {
            "safe":   self.data.get("custom_safe_color",   ""),
            "warn":   self.data.get("custom_warn_color",   ""),
            "urgent": self.data.get("custom_urgent_color", ""),
        }
        point_labels = {
            "safe":   ("🟢 완료/안전", "#3AB89A"),
            "warn":   ("🟡 경고",      "#E8943A"),
            "urgent": ("🔴 긴급",      "#E53935"),
        }
        self._point_previews: dict[str, QFrame] = {}

        for key, (label, default) in point_labels.items():
            row = QHBoxLayout()
            lbl = QLabel(t(label))
            lbl.setStyleSheet(
                f"font-size: 11px; color: {self.T['text']}; background: transparent;")
            row.addWidget(lbl)

            preview = QFrame()
            preview.setFixedSize(22, 22)
            col = self._point_colors[key] or default
            preview.setStyleSheet(
                f"background: {col}; border-radius: 11px; border: none;")
            self._point_previews[key] = preview
            row.addWidget(preview)

            pbtn = QPushButton(t("변경"))
            pbtn.setFixedHeight(22)
            pbtn.setCursor(Qt.CursorShape.PointingHandCursor)
            pbtn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.T['accent_light']};
                    color: {self.T['accent']};
                    border: none; border-radius: 8px;
                    padding: 0 8px; font-size: 10px; font-weight: 700;
                }}
                QPushButton:hover {{ background: {self.T['accent']}; color: white; }}
            """)
            pbtn.clicked.connect(lambda _, k=key: self._pick_point_color(k))
            row.addWidget(pbtn)

            reset_btn = QPushButton(t("기본값"))
            reset_btn.setFixedHeight(22)
            reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            reset_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {self.T['muted']};
                    border: none; font-size: 10px;
                }}
                QPushButton:hover {{ color: {self.T['text']}; }}
            """)
            reset_btn.clicked.connect(lambda _, k=key, d=default: self._reset_point_color(k, d))
            row.addWidget(reset_btn)
            row.addStretch()

            row_w = QWidget()
            row_w.setStyleSheet("background: transparent;")
            row_w.setLayout(row)
            color_widget_layout = color_widget.layout()
            # color_widget의 부모 vbox에 직접 추가
            vbox.addWidget(row_w)
            self.__point_rows = getattr(self, "_point_rows_list", [])
            self._point_rows_list = self.__point_rows
            self._point_rows_list.append(row_w)

        color_widget.setVisible(cur_theme == "커스텀")
        self._color_widget = color_widget
        # 포인트 색상 행도 같이 토글
        for rw in getattr(self, "_point_rows_list", []):
            rw.setVisible(cur_theme == "커스텀")

        # 다크 모드
        vbox.addWidget(self._sec_lbl(t("다크 모드")))
        self._dark_check = QCheckBox(t("다크 모드 사용"))
        self._dark_check.setChecked(self.data.get("dark_mode", False))
        self._dark_check.setStyleSheet(f"""
            QCheckBox {{
                font-size: 12px;
                color: {self.T['text']};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                border-radius: 4px;
                border: 2px solid {self.T['accent']};
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {self.T['accent']};
                border: 2px solid {self.T['accent']};
            }}
        """)
        vbox.addWidget(self._dark_check)

        # 폰트
        vbox.addWidget(self._sec_lbl(t("폰트")))
        self._font_combo = QComboBox()
        self._font_combo.setFixedHeight(34)
        self._style_combo(self._font_combo)
        cur_font = self.data.get("font_family", "")
        for i, (display, family) in enumerate(FONT_OPTIONS):
            self._font_combo.addItem(display)
            if family == cur_font:
                self._font_combo.setCurrentIndex(i)
        vbox.addWidget(self._font_combo)

        vbox.addStretch()
        return w

    def _add_prog_row(self, text: str = "") -> None:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)

        edit = QLineEdit(text)
        edit.setPlaceholderText("clip studio paint.exe")
        edit.setFixedHeight(28)
        edit.setStyleSheet(f"""
            QLineEdit {{
                background: {self.T['accent_light']};
                color: {self.T['text']};
                border: none;
                border-radius: 8px;
                padding: 0 8px;
                font-size: 11px;
            }}
        """)
        row_layout.addWidget(edit)
        self._prog_edits.append(edit)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(22, 22)
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
        del_btn.clicked.connect(lambda _, r=row, e=edit: self._remove_prog_row(r, e))
        row_layout.addWidget(del_btn)

        self._prog_vbox.addWidget(row)

    def _remove_prog_row(self, row: QWidget, edit: QLineEdit) -> None:
        if edit in self._prog_edits:
            self._prog_edits.remove(edit)
        row.deleteLater()

    def _pick_point_color(self, key: str) -> None:
        cur = self._point_colors.get(key, "#3AB89A")
        color = QColorDialog.getColor(QColor(cur or "#3AB89A"), self, t("색상 선택"))
        if color.isValid():
            self._point_colors[key] = color.name()
            self._point_previews[key].setStyleSheet(
                f"background: {color.name()}; border-radius: 11px; border: none;")

    def _reset_point_color(self, key: str, default: str) -> None:
        self._point_colors[key] = ""
        self._point_previews[key].setStyleSheet(
            f"background: {default}; border-radius: 11px; border: none;")

    def _select_theme(self, key: str) -> None:
        for k, btn in self._theme_btns.items():
            btn.setChecked(k == key)
        is_custom = (key == "커스텀")
        self._color_widget.setVisible(is_custom)
        for rw in getattr(self, "_point_rows_list", []):
            rw.setVisible(is_custom)
        self._refresh_theme_btns()

    def _refresh_theme_btns(self) -> None:
        for key, btn in self._theme_btns.items():
            active = btn.isChecked()
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.T['accent'] if active else self.T['accent_light']};
                    color: {'white' if active else self.T['text']};
                    border: none;
                    border-radius: 15px;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 0 8px;
                }}
                QPushButton:hover {{
                    background: {self.T['accent']};
                    color: white;
                }}
            """)

    def _pick_color(self) -> None:
        cur = self.data.get("custom_color", "#9b7fe8")
        color = QColorDialog.getColor(QColor(cur), self, t("색상 선택"))
        if color.isValid():
            hex_color = color.name()
            self.data["custom_color"] = hex_color
            self._color_preview.setStyleSheet(
                f"background: {hex_color}; border-radius: 14px; border: none;")

    # ── 기능 탭 ───────────────────────────────────────────
    def _make_features_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {self.T['bg']};")
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(20, 16, 20, 16)
        vbox.setSpacing(14)

        # 커미션 모드
        vbox.addWidget(self._sec_lbl(t("커미션 모드")))
        self._commission_check = QCheckBox(t("커미션 수입 기록 사용"))
        self._commission_check.setChecked(self.data.get("commission_mode", False))
        self._style_checkbox(self._commission_check)
        vbox.addWidget(self._commission_check)

        commission_desc = QLabel(t("마감에 가격을 기록하고 월별 수입을 확인할 수 있어요."))
        commission_desc.setStyleSheet(
            f"font-size: 11px; color: {self.T['muted']}; background: transparent;")
        commission_desc.setWordWrap(True)
        vbox.addWidget(commission_desc)

        sep = self._separator()
        vbox.addWidget(sep)

        # CS 트래커
        vbox.addWidget(self._sec_lbl(t("CS 트래커")))
        self._cs_check = QCheckBox(t("작업 프로그램 자동 추적 사용"))
        self._cs_check.setChecked(self.data.get("cs_tracker_enabled", False))
        self._style_checkbox(self._cs_check)
        vbox.addWidget(self._cs_check)

        cs_desc = QLabel(t("사용 중인 프로그램을 자동으로 감지해 작업 시간을 기록해요."))
        cs_desc.setStyleSheet(
            f"font-size: 11px; color: {self.T['muted']}; background: transparent;")
        cs_desc.setWordWrap(True)
        vbox.addWidget(cs_desc)

        # 추적 프로그램 목록
        vbox.addWidget(self._sec_lbl(t("추적할 프로그램 (exe 이름)")))

        self._prog_container = QWidget()
        self._prog_container.setStyleSheet("background: transparent;")
        self._prog_vbox = QVBoxLayout(self._prog_container)
        self._prog_vbox.setContentsMargins(0, 0, 0, 0)
        self._prog_vbox.setSpacing(4)
        vbox.addWidget(self._prog_container)

        self._prog_edits: list[QLineEdit] = []
        default_progs = ["clip studio paint.exe", "photoshop.exe", "sai2.exe"]
        raw_progs = self.data.get("tracked_programs", default_progs)
        for prog in raw_progs:
            # 혹시 dict/기타 타입이면 str로 변환
            self._add_prog_row(prog if isinstance(prog, str) else "")

        add_prog_btn = QPushButton(t("+ 프로그램 추가"))
        add_prog_btn.setFixedHeight(26)
        add_prog_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_prog_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.T['accent_light']};
                color: {self.T['accent']};
                border: none;
                border-radius: 8px;
                font-size: 11px;
                font-weight: 700;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background: {self.T['accent']};
                color: white;
            }}
        """)
        add_prog_btn.clicked.connect(lambda: self._add_prog_row(""))
        vbox.addWidget(add_prog_btn, 0, Qt.AlignmentFlag.AlignLeft)

        sep2 = self._separator()
        vbox.addWidget(sep2)

        # 일 목표 시간
        vbox.addWidget(self._sec_lbl(t("일 작업 목표 시간")))
        goal_row = QHBoxLayout()
        self._goal_edit = QLineEdit(str(self.data.get("daily_goal", 4)))
        self._goal_edit.setFixedWidth(60)
        self._goal_edit.setFixedHeight(32)
        self._goal_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._goal_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {self.T['accent_light']};
                color: {self.T['text']};
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
            }}
        """)
        goal_row.addWidget(self._goal_edit)
        goal_unit = QLabel(t("시간"))
        goal_unit.setStyleSheet(
            f"font-size: 12px; color: {self.T['muted']}; background: transparent;")
        goal_row.addWidget(goal_unit)
        goal_row.addStretch()
        vbox.addLayout(goal_row)

        vbox.addStretch()
        return w

    # ── 데이터 탭 ─────────────────────────────────────────
    def _make_data_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {self.T['bg']};")
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(20, 16, 20, 16)
        vbox.setSpacing(14)

        # 데이터 위치 표시
        vbox.addWidget(self._sec_lbl(t("데이터 저장 위치")))
        path_lbl = QLabel(str(DATA_PATH))
        path_lbl.setStyleSheet(
            f"font-size: 10px; color: {self.T['muted']}; background: {self.T['accent_light']};"
            f" border-radius: 8px; padding: 8px;")
        path_lbl.setWordWrap(True)
        vbox.addWidget(path_lbl)

        sep = self._separator()
        vbox.addWidget(sep)

        # 백업
        vbox.addWidget(self._sec_lbl(t("백업 / 가져오기")))

        export_btn = QPushButton(t("📤 데이터 내보내기 (JSON)"))
        export_btn.setFixedHeight(36)
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_outline_btn(export_btn)
        export_btn.clicked.connect(self._export_data)
        vbox.addWidget(export_btn)

        import_btn = QPushButton(t("📥 데이터 가져오기 (JSON)"))
        import_btn.setFixedHeight(36)
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_outline_btn(import_btn)
        import_btn.clicked.connect(self._import_data)
        vbox.addWidget(import_btn)

        sep2 = self._separator()
        vbox.addWidget(sep2)

        # 초기화
        vbox.addWidget(self._sec_lbl(t("⚠ 위험 구역")))
        reset_btn = QPushButton(t("🗑 모든 데이터 초기화"))
        reset_btn.setFixedHeight(36)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: #fde8e8;
                color: {self.T['urgent']};
                border: none;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {self.T['urgent']};
                color: white;
            }}
        """)
        reset_btn.clicked.connect(self._reset_data)
        vbox.addWidget(reset_btn)

        vbox.addStretch()
        return w

    # ── 저장 ──────────────────────────────────────────────
    def _save(self) -> None:
        # 언어
        lang_idx = self._lang_combo.currentIndex()
        new_lang = LANG_OPTIONS[lang_idx][1]
        self.data["language"] = new_lang
        set_language(new_lang)

        # 테마
        selected_theme = "lavender"
        for key, btn in self._theme_btns.items():
            if btn.isChecked():
                selected_theme = key
                break
        self.data["theme"] = selected_theme

        # 커스텀 테마 생성
        if selected_theme == "커스텀":
            from ..utils import generate_theme
            mode = "다크" if self._dark_check.isChecked() else "라이트"
            base_color = self.data.get("custom_color", "#9b7fe8")
            self.data["custom_safe_color"]   = self._point_colors.get("safe",   "")
            self.data["custom_warn_color"]   = self._point_colors.get("warn",   "")
            self.data["custom_urgent_color"] = self._point_colors.get("urgent", "")
            self.data["custom_theme"] = generate_theme(
                base_color, mode,
                safe_color   = self.data["custom_safe_color"],
                warn_color   = self.data["custom_warn_color"],
                urgent_color = self.data["custom_urgent_color"],
            )

        # 다크 모드
        self.data["dark_mode"] = self._dark_check.isChecked()

        # 폰트
        font_idx = self._font_combo.currentIndex()
        self.data["font_family"] = FONT_OPTIONS[font_idx][1]

        # 기능
        self.data["commission_mode"]    = self._commission_check.isChecked()
        self.data["cs_tracker_enabled"] = self._cs_check.isChecked()
        self.data["tracked_programs"]   = [
            e.text().strip() for e in self._prog_edits if e.text().strip()
        ]

        try:
            goal = float(self._goal_edit.text())
            if goal > 0:
                self.data["daily_goal"] = goal
        except ValueError:
            pass

        save_data(self.data)
        self.settings_changed.emit()
        self.accept()

    # ── 데이터 내보내기 / 가져오기 / 초기화 ──────────────
    def _export_data(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, t("데이터 내보내기"), "chorong_backup.json",
            "JSON Files (*.json)"
        )
        if path:
            try:
                Path(path).write_text(
                    json.dumps(self.data, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                QMessageBox.information(self, t("완료"), t("데이터를 내보냈어요."))
            except Exception as e:
                QMessageBox.warning(self, t("오류"), str(e))

    def _import_data(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("데이터 가져오기"), "", "JSON Files (*.json)"
        )
        if path:
            try:
                new_data = json.loads(Path(path).read_text(encoding="utf-8"))
                reply = QMessageBox.question(
                    self,
                    t("확인"),
                    t("현재 데이터를 덮어씁니다. 계속할까요?"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.data.clear()
                    self.data.update(new_data)
                    save_data(self.data)
                    self.settings_changed.emit()
                    self.accept()
            except Exception as e:
                QMessageBox.warning(self, t("오류"), str(e))

    def _reset_data(self) -> None:
        reply = QMessageBox.question(
            self,
            t("초기화 확인"),
            t("모든 마감, 작업 기록, 설정이 삭제됩니다.\n정말로 초기화할까요?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.data.clear()
            self.data["projects"]   = []
            self.data["daily_work"] = {}
            self.data["todos"]      = []
            save_data(self.data)
            self.settings_changed.emit()
            self.accept()

    # ── 헬퍼 ──────────────────────────────────────────────
    def _sec_lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {self.T['muted']};"
            f" background: transparent;")
        return lbl

    def _style_combo(self, combo: QComboBox) -> None:
        combo.setStyleSheet(f"""
            QComboBox {{
                background: {self.T['accent_light']};
                color: {self.T['text']};
                border: none;
                border-radius: 10px;
                padding: 0 10px;
                font-size: 12px;
            }}
            QComboBox::drop-down {{ border: none; padding-right: 8px; }}
        """)

    def _style_checkbox(self, cb: QCheckBox) -> None:
        cb.setStyleSheet(f"""
            QCheckBox {{
                font-size: 12px;
                color: {self.T['text']};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                border-radius: 4px;
                border: 2px solid {self.T['accent']};
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {self.T['accent']};
                border: 2px solid {self.T['accent']};
            }}
        """)

    def _style_outline_btn(self, btn: QPushButton) -> None:
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.T['accent']};
                border: 2px solid {self.T['accent']};
                border-radius: 10px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {self.T['accent']};
                color: white;
            }}
        """)

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(
            f"background: {self.T['accent_light']}; max-height: 1px;")
        return sep
