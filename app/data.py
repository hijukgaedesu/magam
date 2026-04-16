"""데이터 로드/저장 (JSON) — 구 magam_dist.py 데이터와 호환"""
from __future__ import annotations

import json
import os
from pathlib import Path

# 새 기본 경로
DATA_PATH = Path.home() / ".chorong_magam" / "data.json"
# 구 tkinter 앱 경로 (마이그레이션용)
_OLD_DATA_PATH = Path.home() / "artist_dashboard_data.json"

DEFAULTS: dict = {
    "projects": [],
    "daily_work": {},
    "daily_memos": {},
    "todos": [],
    "theme": "lavender",
    "language": "ko",
    "username": "초롱",
    "daily_goal": 0.0,
    "header_image": "",
    "stickers": [],
    "tracked_programs": [
        {"name": "Clip Studio Paint", "exe": "CLIPStudioPaint.exe"}
    ],
    "commission_mode": False,
    "deadline_notif": True,
    "font_family": "맑은 고딕",
    "custom_color": "#9b7fe8",
    "custom_mode": "라이트",
    "custom_theme": {},
}


def _migrate_old_data(old: dict) -> dict:
    """구 버전 데이터를 새 형식으로 변환"""
    new = DEFAULTS.copy()
    # 공통 키 복사
    for k in ("projects", "daily_work", "todos"):
        if k in old:
            new[k] = old[k]
    # 테마 이름 매핑 (구 → 신)
    theme_map = {"라벤더": "lavender", "핑크": "pink", "스카이": "sky", "민트": "mint"}
    old_theme = old.get("theme", "라벤더")
    new["theme"] = theme_map.get(old_theme, "lavender")
    new["username"] = old.get("username", "초롱")
    new["daily_memos"] = old.get("daily_memos", {})
    new["commission_mode"] = old.get("commission_mode", False)
    new["deadline_notif"] = old.get("deadline_notif", True)
    new["custom_color"] = old.get("custom_color", "#9b7fe8")
    new["custom_mode"] = old.get("custom_mode", "라이트")
    new["custom_theme"] = old.get("custom_theme", {})
    new["tracked_programs"] = old.get(
        "tracked_programs",
        [{"name": "Clip Studio Paint", "exe": "CLIPStudioPaint.exe"}]
    )
    return new


def load_data() -> dict:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 1) 새 경로 시도
    if DATA_PATH.exists():
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in DEFAULTS.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            pass

    # 2) 구 tkinter 앱 데이터 마이그레이션
    if _OLD_DATA_PATH.exists():
        try:
            with open(_OLD_DATA_PATH, "r", encoding="utf-8") as f:
                old = json.load(f)
            data = _migrate_old_data(old)
            save_data(data)  # 새 경로에 저장
            return data
        except Exception:
            pass

    # 3) 기본값
    data = DEFAULTS.copy()
    save_data(data)
    return data


def save_data(data: dict) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
