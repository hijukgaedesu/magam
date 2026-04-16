"""공통 유틸리티 함수"""
from __future__ import annotations

import calendar
import random
from datetime import date, datetime

from .i18n import t, _translations

STEPS_PRESETS: dict[str, list[str]] = {
    "기본 5단계": ["러프", "선화", "채색", "보정", "완성"],
    "3단계":      ["스케치", "채색", "완성"],
    "웹툰":       ["콘티", "선화", "배경", "채색", "업로드"],
    "일러스트":   ["아이디어", "러프", "채색", "최종"],
    "원고 작성":  ["아이디어", "구성/플롯", "원고 작성", "검토/수정", "완성"],
    "커미션":     ["러프", "러프 피드백", "선화", "선화 피드백", "채색", "최종 전달"],
}

MOTIVES = {
    "urgent": ["지금 바로 시작해요! 🔥", "마감이 코앞이에요! 🚨",
               "집중! 할 수 있어요 💪", "파이팅! 거의 다 왔어요 🎯"],
    "warn":   ["슬슬 시작할 때예요 🌿", "오늘 러프만이라도? ✏️",
               "꾸준히 가면 돼요 🌸", "한 단계씩 나아가요 ✔"],
    "safe":   ["아직 여유 있어요 🌙", "미리 시작하면 최고! ⭐",
               "편하게 시작해요 🎵", "기분 좋을 때 그려봐요 🎨"],
    "done":   ["완료! 수고했어요 🎉", "멋지게 해냈어요! 🏆", "최고예요, 진짜로! ✨"],
}

FAIRY_MSGS = [
    "러프만이라도 그려볼까요? ✏️",
    "5분만 캔버스 이어봐요!",
    "선화 중이에요, 진짜로 🌙",
    "선화 하나만 올려도 대단할걸요 💪",
    "오늘도 고생 많아요 🧸",
    "마감 전에 맛있는 거 먹어요 🍰",
    "작업 지쳐도 지쳐가 아니에요!",
    "지금 이 시간도 충분해요 🌸",
]


def days_left(deadline_str: str) -> int:
    try:
        d = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        return (d - date.today()).days
    except Exception:
        return 999


def urgency(days: int, done: bool) -> str:
    if done:
        return "done"
    if days <= 3:
        return "urgent"
    if days <= 10:
        return "warn"
    return "safe"


def pill_text(days: int, done: bool) -> str:
    unit = _translations.get("_unit_days", "일")
    if done:
        return t("완료 ✓")
    if days < 0:
        return t("마감 초과!")
    if days == 0:
        return t("오늘 마감!")
    return f"D-{days}"


def motive_text(urg: str) -> str:
    key = f"_motives_{urg}"
    lst = _translations.get(key, MOTIVES.get(urg, MOTIVES["safe"]))
    return random.choice(lst)  # type: ignore[arg-type]


def fmt_month(y: int, m: int) -> str:
    fmt = _translations.get("_cal_month_fmt", "")
    if fmt:
        return fmt.format(y=y, m=m, m_abbr=calendar.month_abbr[m])  # type: ignore[str-format]
    return f"{y}년 {m}월"


def hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    max_c, min_c = max(r, g, b), min(r, g, b)
    la = (max_c + min_c) / 2
    if max_c == min_c:
        return 0.0, 0.0, la * 100
    d = max_c - min_c
    s = d / (2.0 - max_c - min_c) if la > 0.5 else d / (max_c + min_c)
    if max_c == r:
        h = (g - b) / d + (6 if g < b else 0)
    elif max_c == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return (h / 6) * 360, s * 100, la * 100


def hsl_to_hex(h: float, s: float, la: float) -> str:
    h, s, la = h / 360, s / 100, la / 100
    if s == 0:
        v = int(round(la * 255))
        return f"#{v:02x}{v:02x}{v:02x}"

    def hue2rgb(p: float, q: float, t_: float) -> float:
        if t_ < 0: t_ += 1
        if t_ > 1: t_ -= 1
        if t_ < 1/6: return p + (q - p) * 6 * t_
        if t_ < 1/2: return q
        if t_ < 2/3: return p + (q - p) * (2/3 - t_) * 6
        return p

    q = la * (1 + s) if la < 0.5 else la + s - la * s
    p = 2 * la - q
    r = hue2rgb(p, q, h + 1/3)
    g = hue2rgb(p, q, h)
    b = hue2rgb(p, q, h - 1/3)
    return f"#{int(round(r*255)):02x}{int(round(g*255)):02x}{int(round(b*255)):02x}"


def generate_theme(hex_color: str, mode: str = "라이트",
                   safe_color: str = "", warn_color: str = "",
                   urgent_color: str = "") -> dict[str, str]:
    try:
        h, s, _ = hex_to_hsl(hex_color)
    except Exception:
        h, s, _ = hex_to_hsl("#9b7fe8")
    s = max(s, 40)
    if mode == "라이트":
        theme = {
            "accent":            hsl_to_hex(h, s,        72),
            "accent_light":      hsl_to_hex(h, s * 0.7,  94),
            "urgent":            urgent_color or "#e53935",
            "warn":              warn_color   or hsl_to_hex(28,  70, 75),
            "safe":              safe_color   or hsl_to_hex(162, 50, 70),
            "bg":                "#ffffff",
            "sidebar":           hsl_to_hex(h, s * 0.6,  88),
            "sidebar_btn":       hsl_to_hex(h, s * 0.5,  82),
            "sidebar_btn_hover": hsl_to_hex(h, s * 0.4,  92),
            "sidebar_text":      hsl_to_hex(h, s * 0.5,  26),
            "card":              hsl_to_hex(h, s * 0.2,  99),
            "text":              hsl_to_hex(h, s * 0.4,  22),
            "muted":             hsl_to_hex(h, s * 0.35, 68),
        }
    else:  # 다크
        theme = {
            "accent":            hsl_to_hex(h, s,        68),
            "accent_light":      hsl_to_hex(h, s * 0.5,  28),
            "urgent":            urgent_color or "#e53935",
            "warn":              warn_color   or hsl_to_hex(28,  65, 62),
            "safe":              safe_color   or hsl_to_hex(162, 50, 52),
            "bg":                hsl_to_hex(h, s * 0.25, 13),
            "sidebar":           hsl_to_hex(h, s * 0.28, 10),
            "sidebar_btn":       hsl_to_hex(h, s * 0.25, 18),
            "sidebar_btn_hover": hsl_to_hex(h, s * 0.25, 26),
            "sidebar_text":      hsl_to_hex(h, s * 0.12, 86),
            "card":              hsl_to_hex(h, s * 0.22, 19),
            "text":              hsl_to_hex(h, s * 0.12, 88),
            "muted":             hsl_to_hex(h, s * 0.3,  55),
        }
    return theme
