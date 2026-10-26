"""
Unit tests for the Qt message filter in matchypatchy.__main__
"""
from types import SimpleNamespace
from unittest.mock import patch


def _handler():
    from matchypatchy import __main__ as main
    with patch.object(main, "qInstallMessageHandler") as install:
        main.quiet_qt_messages()
    return install.call_args.args[0]


def test_pts_warning_is_dropped(capsys):
    _handler()(None, SimpleNamespace(category="default"),
               "QFFmpeg::Demuxer received AVPacket with pts == AV_NOPTS_VALUE")
    assert capsys.readouterr().err == ""


def test_other_messages_print_like_qt(capsys):
    handler = _handler()
    handler(None, SimpleNamespace(category="default"), "plain warning")
    handler(None, SimpleNamespace(category="qt.multimedia.ffmpeg"), "categorised")
    assert capsys.readouterr().err == "plain warning\nqt.multimedia.ffmpeg: categorised\n"
