from voiceclipper.util import sanitize_session_id


def test_sanitize_session_id() -> None:
    assert sanitize_session_id("Test Audio for Corpus Voces") == "Test_Audio_for_Corpus_Voces"
    assert sanitize_session_id("  session-001  ") == "session-001"
    assert sanitize_session_id("***") == "session"
