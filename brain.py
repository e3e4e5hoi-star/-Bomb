# -*- coding: utf-8 -*-
"""
مغز یادگیرنده Bomfun6
- دیتابیس SQLite برای ذخیره دائمی
- امتیازدهی خودکار به سایت‌ها
- Circuit Breaker برای سایت‌های خراب
- یادگیری payload موفق هر سایت
- اولویت‌بندی بر اساس عملکرد
"""

import os
import json
import time
import sqlite3
import threading
from datetime import datetime
from typing import Optional, List, Dict, Tuple


DB_FILE = "bomfun6.db"


class Brain:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    # ═══════════════════════════════════════════════════════════
    # راه‌اندازی دیتابیس
    # ═══════════════════════════════════════════════════════════

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=10.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._conn()
            try:
                c = conn.cursor()

                c.execute("""
                    CREATE TABLE IF NOT EXISTS sites (
                        url TEXT PRIMARY KEY,
                        name TEXT DEFAULT '',
                        category TEXT DEFAULT 'unknown',
                        priority INTEGER DEFAULT 3,
                        score REAL DEFAULT 50.0,
                        success_count INTEGER DEFAULT 0,
                        fail_count INTEGER DEFAULT 0,
                        last_status INTEGER DEFAULT 0,
                        last_used REAL DEFAULT 0,
                        avg_latency REAL DEFAULT 0,
                        preferred_variant TEXT DEFAULT '',
                        circuit_fails INTEGER DEFAULT 0,
                        circuit_until REAL DEFAULT 0,
                        circuit_reason TEXT DEFAULT '',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                c.execute("""
                    CREATE TABLE IF NOT EXISTS results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        status INTEGER NOT NULL,
                        latency REAL DEFAULT 0,
                        variant TEXT DEFAULT '',
                        success INTEGER DEFAULT 0,
                        session_id TEXT DEFAULT '',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                c.execute("CREATE INDEX IF NOT EXISTS idx_results_url ON results(url)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_results_time ON results(created_at)")

                c.execute("""
                    CREATE TABLE IF NOT EXISTS variants (
                        url TEXT NOT NULL,
                        variant TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        success_count INTEGER DEFAULT 0,
                        last_success REAL DEFAULT 0,
                        PRIMARY KEY (url, variant)
                    )
                """)

                c.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        phone_hash TEXT DEFAULT '',
                        started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        ended_at TEXT DEFAULT '',
                        total_sent INTEGER DEFAULT 0,
                        total_success INTEGER DEFAULT 0,
                        mode TEXT DEFAULT 'single'
                    )
                """)

                c.execute("""
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        date TEXT PRIMARY KEY,
                        total INTEGER DEFAULT 0,
                        success INTEGER DEFAULT 0,
                        failed INTEGER DEFAULT 0,
                        blocked INTEGER DEFAULT 0
                    )
                """)

                conn.commit()
            finally:
                conn.close()

    # ═══════════════════════════════════════════════════════════
    # ثبت سایت جدید
    # ═══════════════════════════════════════════════════════════

    def register_site(self, url: str, name: str = "", category: str = "unknown", priority: int = 3):
        with self._lock:
            conn = self._conn()
            try:
                conn.execute("""
                    INSERT INTO sites (url, name, category, priority)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        name = excluded.name,
                        category = excluded.category,
                        priority = MIN(sites.priority, excluded.priority),
                        updated_at = CURRENT_TIMESTAMP
                """, (url, name, category, priority))
                conn.commit()
            finally:
                conn.close()

    def register_sites(self, sites: List[Tuple]):
        """sites = [(url, name, category, priority), ...] یا [(url, name, category), ...]"""
        for item in sites:
            if len(item) == 4:
                self.register_site(item[0], item[1], item[2], item[3])
            else:
                self.register_site(item[0], item[1], item[2], 3)

    # ═══════════════════════════════════════════════════════════
    # ثبت نتیجه
    # ═══════════════════════════════════════════════════════════

    def record(self, url: str, status: int, latency: float = 0.0,
               variant: str = "", session_id: str = ""):
        with self._lock:
            conn = self._conn()
            try:
                c = conn.cursor()

                # ۱) ثبت در جدول نتایج
                success = 1 if 200 <= status < 300 else 0
                c.execute("""
                    INSERT INTO results (url, status, latency, variant, success, session_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (url, status, latency, variant, success, session_id))

                # ۲) به‌روزرسانی امتیاز
                row = c.execute("SELECT score, success_count, fail_count, avg_latency FROM sites WHERE url = ?", (url,)).fetchone()
                if not row:
                    self.register_site(url)
                    row = c.execute("SELECT score, success_count, fail_count, avg_latency FROM sites WHERE url = ?", (url,)).fetchone()

                score = row["score"] or 50.0
                sc = row["success_count"] or 0
                fc = row["fail_count"] or 0
                avg_lat = row["avg_latency"] or 0.0

                # به‌روزرسانی latency میانگین
                if latency > 0:
                    avg_lat = latency if avg_lat == 0 else 0.7 * avg_lat + 0.3 * latency

                # امتیازدهی
                if 200 <= status < 300:
                    score = min(100.0, score + 8)
                    sc += 1
                elif status == 429:
                    score = max(0, score - 5)
                elif status in (401, 403):
                    score = max(0, score - 3)
                    fc += 1
                elif status == 404:
                    score = max(0, score - 10)
                    fc += 1
                elif status in (400, 422):
                    score = max(0, score - 2)
                    fc += 1
                elif status in (500, 502, 503, 504):
                    score = max(0, score - 4)
                    fc += 1
                elif status in (-1, -2, -3):
                    score = max(0, score - 3)
                    fc += 1

                c.execute("""
                    UPDATE sites
                    SET score = ?, success_count = ?, fail_count = ?,
                        avg_latency = ?, last_status = ?, last_used = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE url = ?
                """, (score, sc, fc, avg_lat, status, time.time(), url))

                # ۳) آپدیت variant موفق
                if success and variant:
                    c.execute("""
                        INSERT INTO variants (url, variant, payload, success_count, last_success)
                        VALUES (?, ?, ?, 1, ?)
                        ON CONFLICT(url, variant) DO UPDATE SET
                            success_count = variants.success_count + 1,
                            last_success = excluded.last_success
                    """, (url, variant, variant, time.time()))

                    c.execute("UPDATE sites SET preferred_variant = ? WHERE url = ?", (variant, url))

                # ۴) Circuit Breaker
                if status in (404, 429) or status >= 500 or status in (-1, -2, -3):
                    cr = c.execute("SELECT circuit_fails FROM sites WHERE url = ?", (url,)).fetchone()
                    fails = (cr["circuit_fails"] if cr else 0) + 1
                    if fails >= 3:
                        until = time.time() + 300
                        reason = "not_found" if status == 404 else ("rate_limit" if status == 429 else "errors")
                        c.execute("""
                            UPDATE sites
                            SET circuit_fails = 0, circuit_until = ?, circuit_reason = ?
                            WHERE url = ?
                        """, (until, reason, url))
                    else:
                        c.execute("UPDATE sites SET circuit_fails = ? WHERE url = ?", (fails, url))
                elif success:
                    c.execute("""
                        UPDATE sites
                        SET circuit_fails = 0, circuit_until = 0, circuit_reason = ''
                        WHERE url = ?
                    """, (url,))

                # ۵) آمار روزانه
                today = datetime.now().strftime("%Y-%m-%d")
                c.execute("""
                    INSERT INTO daily_stats (date, total, success, failed, blocked)
                    VALUES (?, 1, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        total = daily_stats.total + 1,
                        success = daily_stats.success + excluded.success,
                        failed = daily_stats.failed + excluded.failed,
                        blocked = daily_stats.blocked + excluded.blocked
                """, (
                    today,
                    1 if success else 0,
                    0 if success else 1,
                    1 if status in (401, 403, 429) else 0,
                ))

                conn.commit()
            finally:
                conn.close()

    # ═══════════════════════════════════════════════════════════
    # خواندن اطلاعات
    # ═══════════════════════════════════════════════════════════

    def get_site(self, url: str) -> Optional[dict]:
        with self._lock:
            conn = self._conn()
            try:
                row = conn.execute("SELECT * FROM sites WHERE url = ?", (url,)).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

    def get_score(self, url: str) -> float:
        site = self.get_site(url)
        return float(site["score"]) if site else 50.0

    def get_preferred_variant(self, url: str) -> str:
        site = self.get_site(url)
        if not site:
            return ""
        return site.get("preferred_variant") or ""

    def is_circuit_open(self, url: str) -> bool:
        site = self.get_site(url)
        if not site:
            return False
        until = site.get("circuit_until") or 0
        return until > time.time()

    def cooldown_remaining(self, url: str) -> int:
        site = self.get_site(url)
        if not site:
            return 0
        until = site.get("circuit_until") or 0
        return max(0, int(until - time.time()))

    # ═══════════════════════════════════════════════════════════
    # اولویت‌بندی هوشمند
    # ═══════════════════════════════════════════════════════════

    def sorted_urls(self, urls: List[str]) -> List[str]:
        """
        اولویت‌بندی:
        1) سایت‌های با priority پایین‌تر (1=بالا) اول
        2) در همان priority: امتیاز بالاتر اول
        3) سایت‌های cooldown شده آخر
        """
        scored = []
        for u in urls:
            site = self.get_site(u) or {}
            priority = site.get("priority", 3)
            score = site.get("score", 50.0)
            cooldown = self.cooldown_remaining(u)
            is_open = cooldown > 0

            # کلید مرتب‌سازی
            key = (
                1 if is_open else 0,   # cooldown‌ها آخر
                priority,              # اولویت
                -score,                # امتیاز بالاتر اول
            )
            scored.append((key, u))

        scored.sort(key=lambda x: x[0])
        return [u for _, u in scored]

    # ═══════════════════════════════════════════════════════════
    # گزارش‌ها
    # ═══════════════════════════════════════════════════════════

    def get_stats(self) -> dict:
        with self._lock:
            conn = self._conn()
            try:
                total = conn.execute("SELECT COUNT(*) as c FROM sites").fetchone()["c"]
                good = conn.execute("SELECT COUNT(*) as c FROM sites WHERE score >= 60").fetchone()["c"]
                mid = conn.execute("SELECT COUNT(*) as c FROM sites WHERE score >= 30 AND score < 60").fetchone()["c"]
                bad = conn.execute("SELECT COUNT(*) as c FROM sites WHERE score < 30").fetchone()["c"]
                cool = conn.execute("SELECT COUNT(*) as c FROM sites WHERE circuit_until > ?", (time.time(),)).fetchone()["c"]
                return {"total": total, "good": good, "mid": mid, "bad": bad, "cooling": cool}
            finally:
                conn.close()

    def get_top_sites(self, limit: int = 10) -> List[dict]:
        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute("""
                    SELECT url, name, score, success_count, fail_count
                    FROM sites
                    WHERE success_count > 0
                    ORDER BY score DESC, success_count DESC
                    LIMIT ?
                """, (limit,)).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def get_working_sites(self, min_score: float = 60.0) -> List[str]:
        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute("""
                    SELECT url FROM sites
                    WHERE score >= ? AND success_count > 0
                    ORDER BY score DESC
                """, (min_score,)).fetchall()
                return [r["url"] for r in rows]
            finally:
                conn.close()

    def get_daily_stats(self, days: int = 7) -> List[dict]:
        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute("""
                    SELECT * FROM daily_stats
                    ORDER BY date DESC
                    LIMIT ?
                """, (days,)).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    # ═══════════════════════════════════════════════════════════
    # نگهداری
    # ═══════════════════════════════════════════════════════════

    def cleanup_old_results(self, days: int = 30):
        with self._lock:
            conn = self._conn()
            try:
                conn.execute("""
                    DELETE FROM results
                    WHERE created_at < datetime('now', ?)
                """, (f"-{days} days",))
                conn.commit()
            finally:
                conn.close()

    def reset_scores(self):
        with self._lock:
            conn = self._conn()
            try:
                conn.execute("UPDATE sites SET score = 50.0, circuit_until = 0, circuit_fails = 0")
                conn.commit()
            finally:
                conn.close()

    def export_to_json(self, path: str = "brain_export.json"):
        with self._lock:
            conn = self._conn()
            try:
                sites = [dict(r) for r in conn.execute("SELECT * FROM sites ORDER BY score DESC").fetchall()]
                stats = self.get_stats()
                data = {
                    "exported_at": datetime.now().isoformat(),
                    "stats": stats,
                    "sites": sites,
                }
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            finally:
                conn.close()