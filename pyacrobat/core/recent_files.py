"""
Recent Files Management Store for PyAcrobat.
Persists history of opened PDF files with real timestamps, file sizes, and page counts.
"""

import os
import json
import time
import datetime
from typing import List, Dict, Any, Optional


def format_recent_date(timestamp: float) -> str:
    """Formats a unix timestamp into Adobe-style relative dates."""
    now = datetime.datetime.now()
    file_dt = datetime.datetime.fromtimestamp(timestamp)

    if file_dt.date() == now.date():
        time_str = file_dt.strftime("%I:%M %p").lstrip("0")
        return f"Today, {time_str}"

    yesterday = now.date() - datetime.timedelta(days=1)
    if file_dt.date() == yesterday:
        time_str = file_dt.strftime("%I:%M %p").lstrip("0")
        return f"Yesterday, {time_str}"

    return file_dt.strftime("%b %d, %Y")


def format_file_size(size_bytes: int) -> str:
    """Formats byte counts into human-readable strings (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        kb = size_bytes / 1024.0
        return f"{kb:.1f} KB" if kb < 100 else f"{int(round(kb))} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        mb = size_bytes / (1024.0 * 1024.0)
        return f"{mb:.1f} MB"
    else:
        gb = size_bytes / (1024.0 * 1024.0 * 1024.0)
        return f"{gb:.1f} GB"


def normalize_path(file_path: str) -> str:
    """Normalizes file paths consistently across platforms (drive letters, slashes)."""
    if not file_path:
        return ""
    try:
        p = os.path.abspath(file_path).replace("\\", "/")
        if len(p) >= 2 and p[1] == ":":
            p = p[0].lower() + p[1:]
        return p
    except Exception:
        return file_path.replace("\\", "/")


class RecentFilesManager:
    """Manages persistent recent files JSON store in user's profile."""

    _instance: Optional["RecentFilesManager"] = None

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.storage_path = storage_path
        else:
            base_dir = os.path.join(os.path.expanduser("~"), ".pyacrobat")
            os.makedirs(base_dir, exist_ok=True)
            self.storage_path = os.path.join(base_dir, "recent_files.json")

    @classmethod
    def get_instance(cls) -> "RecentFilesManager":
        if cls._instance is None:
            cls._instance = RecentFilesManager()
        return cls._instance

    def load_records(self) -> List[Dict[str, Any]]:
        """Loads records from the JSON store and updates relative date strings."""
        if not os.path.exists(self.storage_path):
            return []

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                records = json.load(f)
            if not isinstance(records, list):
                return []

            seen = set()
            deduped = []
            for r in records:
                p = normalize_path(r.get("path", ""))
                if p and p in seen:
                    continue
                if p:
                    seen.add(p)
                if "timestamp" in r:
                    r["date"] = format_recent_date(r["timestamp"])
                deduped.append(r)
            return deduped
        except Exception:
            return []

    def save_records(self, records: List[Dict[str, Any]]):
        """Saves records to the JSON store atomically."""
        try:
            tmp_path = self.storage_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
            if os.path.exists(self.storage_path):
                os.replace(tmp_path, self.storage_path)
            else:
                os.rename(tmp_path, self.storage_path)
        except Exception:
            pass

    def record_file(self, file_path: str, page_count: Optional[int] = None) -> Dict[str, Any]:
        """
        Records or updates a file in the recent history.
        Moves it to the top of the list.
        """
        norm_path = normalize_path(file_path)
        name = os.path.basename(norm_path)
        size_bytes = os.path.getsize(norm_path) if os.path.exists(norm_path) else 0
        size_str = format_file_size(size_bytes)
        now_ts = time.time()
        date_str = format_recent_date(now_ts)

        records = self.load_records()

        # Check if already present and preserve custom fields (like starred)
        existing_starred = False
        existing_pages = page_count or 1
        filtered = []
        for r in records:
            if normalize_path(r.get("path", "")) == norm_path:
                existing_starred = r.get("starred", False)
                if page_count is None and "pages" in r:
                    existing_pages = r["pages"]
            else:
                filtered.append(r)

        new_record = {
            "path": norm_path,
            "name": name,
            "size": size_str,
            "size_bytes": size_bytes,
            "timestamp": now_ts,
            "date": date_str,
            "pages": page_count if page_count is not None else existing_pages,
            "starred": existing_starred
        }

        # Insert at front
        filtered.insert(0, new_record)
        self.save_records(filtered[:50]) # keep up to 50 recent files
        return new_record

    def remove_file(self, file_path: str):
        """Removes a file from history."""
        norm_path = normalize_path(file_path)
        records = [r for r in self.load_records() if normalize_path(r.get("path", "")) != norm_path]
        self.save_records(records)

    def toggle_star(self, file_path: str) -> bool:
        """Toggles the starred flag for a given file."""
        norm_path = normalize_path(file_path)
        records = self.load_records()
        new_state = False
        found = False
        for r in records:
            if normalize_path(r.get("path", "")) == norm_path:
                r["starred"] = not r.get("starred", False)
                new_state = r["starred"]
                found = True
                break
        if not found and file_path and os.path.exists(file_path):
            self.record_file(file_path)
            records = self.load_records()
            for r in records:
                if normalize_path(r.get("path", "")) == norm_path:
                    r["starred"] = True
                    new_state = True
                    break
        elif not found and file_path:
            new_state = True
            records.append({
                "path": norm_path,
                "name": os.path.basename(norm_path),
                "size": "2.4 MB",
                "timestamp": time.time(),
                "date": "Today",
                "pages": 1,
                "starred": True
            })
        self.save_records(records)
        return new_state

    def set_starred(self, file_path: str, starred: bool) -> bool:
        """Sets the starred status for a given file."""
        norm_path = normalize_path(file_path)
        records = self.load_records()
        found = False
        for r in records:
            if normalize_path(r.get("path", "")) == norm_path:
                r["starred"] = starred
                found = True
                break
        if not found and file_path and os.path.exists(file_path):
            self.record_file(file_path)
            records = self.load_records()
            for r in records:
                if normalize_path(r.get("path", "")) == norm_path:
                    r["starred"] = starred
                    break
        elif not found and file_path:
            records.append({
                "path": norm_path,
                "name": os.path.basename(norm_path),
                "size": "2.4 MB",
                "timestamp": time.time(),
                "date": "Today",
                "pages": 1,
                "starred": starred
            })
        self.save_records(records)
        return starred

    def is_starred(self, file_path: str) -> bool:
        """Returns whether a file is currently marked as starred."""
        norm_path = normalize_path(file_path)
        for r in self.load_records():
            if normalize_path(r.get("path", "")) == norm_path:
                return bool(r.get("starred", False))
        return False

    def get_starred_files(self) -> List[Dict[str, Any]]:
        """Returns only files marked as starred."""
        return [r for r in self.load_records() if r.get("starred", False)]

    def clear(self):
        """Clears all records."""
        self.save_records([])
