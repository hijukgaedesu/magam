"""메인 윈도우 — 전체 레이아웃 조합"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QScrollArea, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QCloseEvent

from .data import load_data, save_data
from .theme import get_theme, qss
from .i18n import set_language, t
from .widgets.header_bar import HeaderBar
from .widgets.left_panel import LeftPanel
from .widgets.right_panel import RightPanel
from .widgets.sticker_layer import StickerManager


class MainWindow(QMainWindow):
    # 전역 데이터 변경 시그널 → 모든 패널이 구독
    data_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.data = load_data()

        # 언어 초기화
        set_language(self.data.get("language", "ko"))

        # 테마 초기화
        self.T = get_theme(self.data.get("theme", "lavender"), self.data)

        self.setWindowTitle("0w0 Deadline Tracker")
        self.setMinimumSize(QSize(980, 660))
        self.resize(1200, 800)

        self._sticker_manager: StickerManager | None = None
        self._build_ui()
        self._apply_theme()
        self._init_stickers()

    # ── UI 구성 ──────────────────────────────────────────
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 상단 헤더
        self.header = HeaderBar(self.T, self.data, self)
        self.header.add_clicked.connect(self._open_add_dialog)
        self.header.stats_clicked.connect(self._open_stats_dialog)
        self.header.archive_clicked.connect(self._open_archive_dialog)
        self.header.income_clicked.connect(self._open_commission_dialog)
        self.header.settings_clicked.connect(self._open_settings)
        self.header.sticker_clicked.connect(self._open_sticker_picker)
        root.addWidget(self.header)

        # 좌 / 우 분할
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        splitter.setObjectName("mainSplitter")

        # 좌측 (스크롤 가능한 메인 컨텐츠)
        self.left_panel = LeftPanel(self.T, self.data, self)
        self.left_panel.data_changed.connect(self._on_data_changed)
        splitter.addWidget(self.left_panel)

        # 우측 패널
        self.right_panel = RightPanel(self.T, self.data, self)
        self.right_panel.data_changed.connect(self._on_data_changed)
        splitter.addWidget(self.right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([880, 290])

        root.addWidget(splitter)

    def _apply_theme(self) -> None:
        self.setStyleSheet(qss(self.T))

    # ── 데이터 변경 콜백 ──────────────────────────────────
    def _on_data_changed(self) -> None:
        save_data(self.data)
        self.left_panel.refresh()
        self.right_panel.refresh()
        self.header.refresh()

    def save(self) -> None:
        save_data(self.data)

    # ── 다이얼로그 열기 ───────────────────────────────────
    def _open_add_dialog(self) -> None:
        from .dialogs.deadline_dialog import DeadlineDialog
        dlg = DeadlineDialog(self.T, self.data, parent=self)
        if dlg.exec():
            self._on_data_changed()

    def _open_stats_dialog(self) -> None:
        from .dialogs.stats_dialog import StatsDialog
        dlg = StatsDialog(self.T, self.data, parent=self)
        dlg.exec()

    def _open_archive_dialog(self) -> None:
        from .dialogs.archive_dialog import ArchiveDialog
        dlg = ArchiveDialog(self.T, self.data, parent=self)
        if dlg.exec():
            self._on_data_changed()

    def _open_commission_dialog(self) -> None:
        from .dialogs.commission_dialog import CommissionDialog
        dlg = CommissionDialog(self.T, self.data, parent=self)
        dlg.exec()

    def _open_settings(self) -> None:
        from .dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.T, self.data, parent=self)
        if dlg.exec():
            # 테마·언어 재적용 후 전체 재구축
            set_language(self.data.get("language", "ko"))
            self.T = get_theme(self.data.get("theme", "lavender"), self.data)
            self._apply_theme()
            # 헤더/패널 재구축
            self._rebuild_all()

    def _init_stickers(self) -> None:
        if self._sticker_manager:
            self._sticker_manager.close_all()
        self._sticker_manager = StickerManager(self.T, self.data, self)

    def _open_sticker_picker(self) -> None:
        if self._sticker_manager:
            self._sticker_manager.open_picker(self)

    def _rebuild_all(self) -> None:
        """테마/언어 변경 후 UI 전체 재구성"""
        old = self.centralWidget()
        if old:
            old.deleteLater()
        self._build_ui()
        self._apply_theme()
        self._init_stickers()

    # ── 종료 ─────────────────────────────────────────────
    def closeEvent(self, event: QCloseEvent) -> None:
        self.save()
        if hasattr(self.right_panel, "stop_threads"):
            self.right_panel.stop_threads()
        if self._sticker_manager:
            self._sticker_manager.save_positions()
        super().closeEvent(event)
