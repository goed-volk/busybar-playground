import io
import logging

import pytest

from busybar_kit.cli import SecretRedactionFilter, setup_logging

TOKEN = "s3cret-token-value"


@pytest.fixture
def clean_root():
    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    levels = {n: logging.getLogger(n).level for n in ("busylib", "httpx2", "httpcore2")}
    yield
    root.handlers[:] = saved[0]
    root.setLevel(saved[1])
    for name, level in levels.items():
        logging.getLogger(name).setLevel(level)


def _record(msg, *args, name="app", exc_info=None):
    return logging.LogRecord(name, logging.INFO, __file__, 1, msg, args, exc_info)


def test_filter_scrubs_message_and_args():
    flt = SecretRedactionFilter([TOKEN, None, ""])
    record = _record("auth %s ok", TOKEN)
    assert flt.filter(record)
    assert record.getMessage() == "auth <redacted> ok"


def test_filter_scrubs_exception_text():
    flt = SecretRedactionFilter()
    flt.add(TOKEN)
    try:
        raise RuntimeError(f"bad {TOKEN}")
    except RuntimeError:
        import sys

        record = _record("failed", exc_info=sys.exc_info())
    flt.filter(record)
    assert TOKEN not in record.exc_text and "<redacted>" in record.exc_text


def test_filter_without_secrets_passes_through():
    record = _record("hello %s", "world")
    assert SecretRedactionFilter().filter(record)
    assert record.args == ("world",)


def test_setup_logging_uses_stderr_by_default(clean_root, capsys):
    setup_logging()
    logging.getLogger("busybar_kit.test").warning("to stderr")
    out, err = capsys.readouterr()
    assert out == "" and "to stderr" in err


def test_setup_logging_redacts_across_loggers(clean_root):
    stream = io.StringIO()
    redaction = setup_logging(stream=stream, secrets=[TOKEN])
    redaction.add("later-secret")
    logging.getLogger("busylib.client.base").warning("header %s", TOKEN)
    logging.getLogger("httpx2").warning("url ?t=later-secret")
    logging.getLogger("my_app").warning("plain")
    text = stream.getvalue()
    assert TOKEN not in text and "later-secret" not in text
    assert text.count("<redacted>") == 2 and "plain" in text


def test_setup_logging_quiets_third_party_info(clean_root):
    stream = io.StringIO()
    setup_logging(stream=stream)
    logging.getLogger("busylib.client.display").info("display_draw application_name=x")
    logging.getLogger("httpx2").info("HTTP Request: POST ...")
    logging.getLogger("busylib.client.base").error(
        "API error %s request_id=%s: %s (body=%s)", 409, "r", "conflict", "{}"
    )
    logging.getLogger("busylib.client.base").error(
        "API error %s request_id=%s: %s (body=%s)", 500, "r", "boom", "{}"
    )
    logging.getLogger("my_app").info("app info")
    text = stream.getvalue()
    assert "display_draw" not in text and "HTTP Request" not in text
    assert "conflict" not in text and "boom" in text and "app info" in text


def test_setup_logging_verbose_keeps_everything(clean_root):
    stream = io.StringIO()
    setup_logging(True, stream=stream)
    logging.getLogger("busylib.client.display").info("display_draw")
    logging.getLogger("busylib.client.base").error(
        "API error %s request_id=%s: %s (body=%s)", 409, "r", "conflict", "{}"
    )
    logging.getLogger("busybar_kit.draw").debug("dbg")
    text = stream.getvalue()
    assert "display_draw" in text and "conflict" in text and "dbg" in text


def test_setup_logging_is_idempotent(clean_root):
    setup_logging(stream=io.StringIO())
    setup_logging(stream=io.StringIO())
    ours = [h for h in logging.getLogger().handlers if getattr(h, "_busybar_kit", False)]
    assert len(ours) == 1
