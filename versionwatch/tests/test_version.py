from versionwatch.recorder import event_id_for, resolve_version
from versionwatch.events import EventSource, EventType, FileEvent


def test_resolve_version_new_file():
    event_type, version, previous, overwritten = resolve_version(None)
    assert (event_type, version, previous, overwritten) == ("created", 1, None, False)


def test_resolve_version_overwrite():
    prev = {"version": 1, "is_deleted": False}
    event_type, version, previous, overwritten = resolve_version(prev)
    assert (event_type, version, previous, overwritten) == ("modified", 2, 1, True)


def test_resolve_version_after_delete():
    prev = {"version": 3, "is_deleted": True}
    event_type, version, previous, overwritten = resolve_version(prev)
    assert (event_type, version, previous, overwritten) == ("created", 4, 3, False)


def test_event_id_is_stable():
    ev = FileEvent(
        source=EventSource.FTP_LOG,
        event_type=EventType.MODIFIED,
        rel_path="oct/a.ma",
        host_path="/srv/ftp/oct/a.ma",
        size=10,
        checksum="abc",
        observed_at=1234.0,
    )
    assert event_id_for(ev) == event_id_for(ev)
    assert event_id_for(ev) != event_id_for(
        FileEvent(
            source=EventSource.WATCHDOG,
            event_type=EventType.MODIFIED,
            rel_path="oct/a.ma",
            host_path="/srv/ftp/oct/a.ma",
            size=10,
            checksum="abc",
            observed_at=1234.0,
        )
    )