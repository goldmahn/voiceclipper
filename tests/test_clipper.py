from voiceclipper.clipper import _clip_filename


def test_clip_filename_numbering() -> None:
    assert _clip_filename("who_sent_you", 0) == "who_sent_you.wav"
    assert _clip_filename("who_sent_you", 1) == "who_sent_you1.wav"
    assert _clip_filename("who_sent_you", 2) == "who_sent_you2.wav"
