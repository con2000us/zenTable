#!/usr/bin/env python3
"""Theme loading/cache/list utilities for zentable."""

from __future__ import annotations

import json
import os
import sys
import zipfile
from typing import Optional, Tuple

from .loader import load_json

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROJECT_ROOT = os.path.dirname(_SCRIPTS_DIR)
THEMES_DIR = os.path.join(_PROJECT_ROOT, 'themes')
CACHE_BASE = os.environ.get('ZENTABLE_CACHE_DIR', '/tmp/zentable_themes')


def _read_template_from_zip(zip_path):
    """從 zip 內讀取 template.json（支援根目錄或 mode/theme_name/template.json）。"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            candidates = ['template.json'] + [n for n in z.namelist() if n.endswith('template.json')]
            for c in candidates:
                try:
                    content = z.read(c)
                    return json.loads(content.decode('utf-8'))
                except (KeyError, json.JSONDecodeError):
                    continue
    except (zipfile.BadZipFile, OSError):
        pass
    return None


def load_theme_from_themes_dir(theme_name, mode='css'):
    for base in [THEMES_DIR]:
        if not base:
            continue
        zip_path = os.path.join(base, mode, theme_name + '.zip')
        if os.path.isfile(zip_path):
            try:
                data = _read_template_from_zip(zip_path)
                if data:
                    return data
            except Exception as e:
                print(f"⚠️  載入主題失敗 {zip_path}: {e}", file=sys.stderr)
        folder_path = os.path.join(base, mode, theme_name, 'template.json')
        if os.path.exists(folder_path):
            try:
                return load_json(folder_path)
            except Exception as e:
                print(f"⚠️  載入主題失敗 {folder_path}: {e}", file=sys.stderr)
    return None


def list_themes_in_dir(mode='css'):
    seen = set()
    for base in [THEMES_DIR]:
        if not base or not os.path.isdir(base):
            continue
        mode_dir = os.path.join(base, mode)
        if not os.path.isdir(mode_dir):
            continue
        for name in os.listdir(mode_dir):
            if name in seen:
                continue
            full = os.path.join(mode_dir, name)
            if name.endswith('.zip') and os.path.isfile(full):
                seen.add(name[:-4])
            elif os.path.isdir(full) and os.path.exists(os.path.join(full, 'template.json')):
                seen.add(name)
    return sorted(seen)


def get_theme_source_path(theme_name, mode='css'):
    def find_path(name):
        for base in [THEMES_DIR]:
            if not base:
                continue
            zip_path = os.path.join(base, mode, name + '.zip')
            if os.path.isfile(zip_path):
                return (os.path.abspath(zip_path), True)
            folder_path = os.path.join(base, mode, name, 'template.json')
            if os.path.exists(folder_path):
                return (os.path.abspath(os.path.join(base, mode, name)), False)
        return None

    r = find_path(theme_name)
    if r:
        return r
    alias = {"dark": "default_dark", "light": "default_light"}.get(theme_name)
    if alias:
        r = find_path(alias)
        if r:
            return r
    for fallback in ["default_dark", "default_light"]:
        r = find_path(fallback)
        if r:
            return r
    return None


def _rmtree_safe(d):
    if not os.path.isdir(d):
        return
    for name in os.listdir(d):
        p = os.path.join(d, name)
        if os.path.isdir(p):
            _rmtree_safe(p)
        else:
            try:
                os.remove(p)
            except OSError:
                pass
    try:
        os.rmdir(d)
    except OSError:
        pass


def ensure_theme_cache(theme_name, mode='css'):
    src = get_theme_source_path(theme_name, mode)
    if not src:
        raise ValueError(f"主題 '{theme_name}' 不存在於 themes/{mode}/")
    path, is_zip = src
    if not is_zip:
        return path
    cache_dir = os.path.join(CACHE_BASE, f"{mode}_{theme_name}")
    meta_path = os.path.join(cache_dir, '.cache_meta')
    try:
        zip_mtime = os.path.getmtime(path)
    except OSError:
        zip_mtime = 0
    if os.path.isdir(cache_dir) and os.path.isfile(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            if meta.get('source') == path and meta.get('mtime') == zip_mtime:
                return cache_dir
        except (json.JSONDecodeError, OSError):
            pass
    if os.path.isdir(cache_dir):
        _rmtree_safe(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(path, 'r') as z:
            z.extractall(cache_dir)
    except (zipfile.BadZipFile, OSError) as e:
        print(f"⚠️  解壓主題失敗 {path}: {e}", file=sys.stderr)
        raise
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump({"source": path, "mtime": zip_mtime}, f)
    return cache_dir


def get_theme(theme_name, mode='css'):
    theme = load_theme_from_themes_dir(theme_name, mode)
    if theme:
        print(f"🎨 從 themes 目錄載入: {theme_name} ({mode})", file=sys.stderr)
        return theme
    alias = {"dark": "default_dark", "light": "default_light"}.get(theme_name)
    if alias:
        theme = load_theme_from_themes_dir(alias, mode)
        if theme:
            print(f"🎨 從 themes 目錄載入: {alias} ({mode}) [別名 {theme_name}]", file=sys.stderr)
            return theme
    if theme_name not in ("default_dark", "default_light"):
        for fallback in ["default_dark", "default_light"]:
            theme = load_theme_from_themes_dir(fallback, mode)
            if theme:
                print(f"⚠️  主題 '{theme_name}' 不存在，使用 {fallback}", file=sys.stderr)
                return theme
    raise ValueError(f"主題 '{theme_name}' 不存在於 themes/{mode}/ 目錄，且無法找到預設主題")
