"""테마 색상 정의 + QSS 생성"""
from __future__ import annotations

THEMES: dict[str, dict[str, str]] = {
    "lavender": {
        "bg":                "#F8F6FF",
        "card":              "#FDFCFF",
        "accent":            "#9b7fe8",
        "accent_light":      "#E8E0FF",
        "sidebar":           "#cdc4f0",   # 원본처럼 밝은 라벤더
        "sidebar_btn":       "#b8aee0",
        "sidebar_btn_hover": "#d8d0f8",
        "sidebar_text":      "#3A2860",
        "text":              "#3A2860",
        "muted":             "#9888C0",
        "urgent":            "#E53935",
        "warn":              "#E8943A",
        "safe":              "#3AB89A",
    },
    "pink": {
        "bg":                "#FFFFFF",
        "card":              "#FFFAFC",
        "accent":            "#f0a8c0",
        "accent_light":      "#fdeef5",
        "sidebar":           "#fce0ec",   # 원본 핑크
        "sidebar_btn":       "#f8cede",
        "sidebar_btn_hover": "#feeaf3",
        "sidebar_text":      "#6a2840",
        "text":              "#3a1828",
        "muted":             "#c8a8b8",
        "urgent":            "#E53935",
        "warn":              "#ECC898",
        "safe":              "#98D8BC",
    },
    "sky": {
        "bg":                "#f2f8ff",
        "card":              "#f8fbff",
        "accent":            "#78b0e0",
        "accent_light":      "#d0eaff",
        "sidebar":           "#c4dff5",   # 밝은 하늘색
        "sidebar_btn":       "#aacce8",
        "sidebar_btn_hover": "#d8eeff",
        "sidebar_text":      "#283858",
        "text":              "#283858",
        "muted":             "#88a8c8",
        "urgent":            "#E53935",
        "warn":              "#e0a040",
        "safe":              "#50c090",
    },
    "mint": {
        "bg":                "#f0faf6",
        "card":              "#f6fdf9",
        "accent":            "#60c098",
        "accent_light":      "#c8f0e0",
        "sidebar":           "#b8e8d4",   # 밝은 민트
        "sidebar_btn":       "#9ed8c0",
        "sidebar_btn_hover": "#ccf0e4",
        "sidebar_text":      "#183a28",
        "text":              "#183a28",
        "muted":             "#78a890",
        "urgent":            "#E53935",
        "warn":              "#e0a040",
        "safe":              "#60c098",
    },
}


def get_theme(name: str, data: dict | None = None) -> dict[str, str]:
    if name == "커스텀" and data:
        return data.get("custom_theme", THEMES["lavender"])
    return THEMES.get(name, THEMES["lavender"])


# ── 각종 pill / badge 색상 ─────────────────────────────
def pill_colors(urg: str, T: dict) -> tuple[str, str]:
    """(배경색, 텍스트색) 반환"""
    bg = {"urgent": "#fde8e8", "warn": "#fff0d0",
          "safe": "#d6f5ec", "done": "#e8f5e9"}
    tc = {"urgent": T["urgent"], "warn": T["warn"],
          "safe": T["safe"], "done": "#388e3c"}
    return bg.get(urg, "#eeeeee"), tc.get(urg, "#333333")


# ── 메인 QSS ──────────────────────────────────────────
def qss(T: dict) -> str:
    return f"""
/* ══ Base ══ */
QMainWindow, QWidget#central {{
    background: {T['bg']};
}}
QWidget {{
    font-size: 13px;
    color: {T['text']};
}}

/* ══ ScrollArea ══ */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    width: 6px;
    background: {T['accent_light']};
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {T['accent']};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    height: 6px;
    background: {T['accent_light']};
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {T['accent']};
    border-radius: 3px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ══ Input ══ */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {T['card']};
    color: {T['text']};
    border: 1.5px solid {T['accent_light']};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {T['accent']};
    selection-color: white;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1.5px solid {T['accent']};
}}
QLineEdit::placeholder {{ color: {T['muted']}; }}

/* ══ ComboBox ══ */
QComboBox {{
    background: {T['card']};
    color: {T['text']};
    border: 1.5px solid {T['accent_light']};
    border-radius: 8px;
    padding: 5px 10px;
    min-height: 28px;
}}
QComboBox:hover {{ border-color: {T['accent']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {T['card']};
    color: {T['text']};
    border: 1px solid {T['accent_light']};
    selection-background-color: {T['accent_light']};
    selection-color: {T['text']};
    outline: none;
}}

/* ══ PushButton ══ */
QPushButton {{
    background: {T['accent_light']};
    color: {T['text']};
    border: none;
    border-radius: 10px;
    padding: 6px 16px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {T['accent']}; color: white; }}
QPushButton:pressed {{ background: {T['sidebar_btn']}; color: white; }}
QPushButton#accent {{
    background: {T['accent']};
    color: white;
}}
QPushButton#accent:hover {{ background: {T['sidebar_btn']}; }}
QPushButton#ghost {{
    background: transparent;
    color: {T['muted']};
    border: 1.5px solid {T['accent_light']};
}}
QPushButton#ghost:hover {{ background: {T['accent_light']}; color: {T['text']}; }}
QPushButton#danger:hover {{ background: {T['urgent']}; color: white; }}
QPushButton#sidebar {{
    background: {T['sidebar_btn']};
    color: {T['sidebar_text']};
    border-radius: 14px;
    padding: 5px 14px;
    font-weight: 700;
}}
QPushButton#sidebar:hover {{ background: {T['sidebar_btn_hover']}; }}

/* ══ CheckBox ══ */
QCheckBox {{
    spacing: 6px;
    color: {T['text']};
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 4px;
    border: 1.5px solid {T['accent']};
    background: {T['card']};
}}
QCheckBox::indicator:checked {{
    background: {T['accent']};
    border-color: {T['accent']};
    image: url(:/icons/check.svg);
}}

/* ══ RadioButton ══ */
QRadioButton {{
    spacing: 6px;
    color: {T['text']};
}}
QRadioButton::indicator {{
    width: 15px; height: 15px;
    border-radius: 7px;
    border: 1.5px solid {T['accent']};
    background: {T['card']};
}}
QRadioButton::indicator:checked {{
    background: {T['accent']};
    border-color: {T['accent']};
}}

/* ══ Slider ══ */
QSlider::groove:horizontal {{
    height: 4px;
    background: {T['accent_light']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px; height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    background: {T['accent']};
}}
QSlider::sub-page:horizontal {{
    background: {T['accent']};
    border-radius: 2px;
}}

/* ══ ProgressBar ══ */
QProgressBar {{
    border: none;
    background: {T['accent_light']};
    border-radius: 4px;
    text-align: center;
    color: transparent;
    max-height: 8px;
}}
QProgressBar::chunk {{
    background: {T['accent']};
    border-radius: 4px;
}}

/* ══ Splitter ══ */
QSplitter::handle {{
    background: {T['accent_light']};
}}

/* ══ Tooltip ══ */
QToolTip {{
    background: {T['card']};
    color: {T['text']};
    border: 1px solid {T['accent_light']};
    border-radius: 6px;
    padding: 4px 8px;
}}

/* ══ Dialog ══ */
QDialog {{
    background: {T['bg']};
}}

/* ══ Frame cards ══ */
QFrame#card {{
    background: {T['card']};
    border-radius: 16px;
    border: 1px solid {T['accent_light']};
}}

/* ══ Label variants ══ */
QLabel#muted {{ color: {T['muted']}; }}
QLabel#accent {{ color: {T['accent']}; font-weight: 700; }}
QLabel#section-title {{ font-size: 14px; font-weight: 700; color: {T['text']}; }}
"""
