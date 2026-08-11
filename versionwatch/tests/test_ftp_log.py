from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from versionwatch.events import EventSource, EventType
from versionwatch.ftp_log import parse_ftp_line

ROOT = Path("/srv/ftp")
try:
    TZ = ZoneInfo("Asia/Shanghai")
except ZoneInfoNotFoundError:  # Windows 无系统 tzdata 时的回退
    TZ = timezone(timedelta(hours=8))


def test_parse_upload():
    line = (
        'Tue Jun  1 10:00:05 2026 [pid 1234] [ftpuser] OK UPLOAD: Client '
        '"192.168.1.10", "/oct/mk2/shot/s03/a.ma", 123456 bytes, 123.45Kbyte/sec'
    )
    ev = parse_ftp_line(line, ROOT, TZ)
    assert ev is not None
    assert ev.source == EventSource.FTP_LOG
    assert ev.event_type == EventType.MODIFIED
    assert ev.rel_path == "oct/mk2/shot/s03/a.ma"
    assert ev.host_path == "/srv/ftp/oct/mk2/shot/s03/a.ma"
    assert ev.size == 123456
    assert ev.actor == "ftpuser"
    assert ev.client_ip == "192.168.1.10"


def test_parse_delete():
    line = (
        'Tue Jun  1 10:00:06 2026 [pid 1234] [ftpuser] OK DELETE: Client '
        '"192.168.1.10", "/oct/mk2/shot/s03/a.ma"'
    )
    ev = parse_ftp_line(line, ROOT, TZ)
    assert ev is not None
    assert ev.event_type == EventType.DELETED
    assert ev.rel_path == "oct/mk2/shot/s03/a.ma"


def test_parse_rename():
    line = (
        'Tue Jun  1 10:00:07 2026 [pid 1234] [ftpuser] OK RENAME: Client '
        '"192.168.1.10", from "/oct/a.ma" to "/oct/b.ma"'
    )
    ev = parse_ftp_line(line, ROOT, TZ)
    assert ev is not None
    assert ev.event_type == EventType.MOVED
    assert ev.rel_path == "oct/b.ma"
    assert ev.move_src == "oct/a.ma"


def test_parse_fail_ignored():
    line = (
        'Tue Jun  1 10:00:08 2026 [pid 1234] [ftpuser] FAL UPLOAD: Client '
        '"192.168.1.10", "/oct/a.ma", 0 bytes, 0.00Kbyte/sec'
    )
    assert parse_ftp_line(line, ROOT, TZ) is None


def test_parse_garbage():
    assert parse_ftp_line("not a log line", ROOT, TZ) is None


def test_parse_download_ignored():
    line = (
        'Tue Jun  1 10:00:09 2026 [pid 1234] [ftpuser] OK RETR: Client '
        '"192.168.1.10", "/oct/a.ma"'
    )
    assert parse_ftp_line(line, ROOT, TZ) is None


def test_year_rollover_guard():
    # 日志年份超前当前时间超过 24h 时回退一年
    next_year = datetime.now(TZ).year + 1
    line = (
        f"Tue Jun  1 10:00:00 {next_year} [pid 1] [u] OK UPLOAD: Client "
        '"1.2.3.4", "/a.ma", 1 bytes, 1.00Kbyte/sec'
    )
    ev = parse_ftp_line(line, ROOT, TZ)
    assert ev is not None
    assert datetime.fromtimestamp(ev.observed_at, TZ).year == next_year - 1


def test_no_weekday_prefix_also_ok():
    line = (
        'Jun  1 10:00:05 2026 [pid 1234] [ftpuser] OK UPLOAD: Client '
        '"192.168.1.10", "/oct/a.ma", 1 bytes, 1.00Kbyte/sec'
    )
    ev = parse_ftp_line(line, ROOT, TZ)
    assert ev is not None
    assert ev.rel_path == "oct/a.ma"