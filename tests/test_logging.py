"""Tests for spinorama logger resource management."""

import logging

from spinorama._logging import close_logger, logger, setup_logger


def _owned_handlers() -> list[logging.Handler]:
    return [handler for handler in logger.handlers if getattr(handler, "_spinorama_handler", False)]


def test_setup_logger_closes_previous_handlers(tmp_path) -> None:
    close_logger()
    log_path = tmp_path / "spinorama.log"

    setup_logger(path=str(log_path))
    first_file_handler = next(
        handler for handler in _owned_handlers() if isinstance(handler, logging.FileHandler)
    )
    setup_logger(path=str(log_path))

    assert first_file_handler.stream is None or first_file_handler.stream.closed
    assert len(_owned_handlers()) == 2

    close_logger()
    assert _owned_handlers() == []
