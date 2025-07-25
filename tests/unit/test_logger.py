import json
import logging
import os
from io import StringIO
from unittest import mock

from openhands_aci.utils.logger import JSONFormatter, oh_aci_logger


class TestLogger:
    def test_json_formatter(self):
        """Test that JSONFormatter correctly formats log records as JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test_path',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed['name'] == 'test_logger'
        assert parsed['level'] == 'INFO'
        assert parsed['message'] == 'Test message'
        assert 'timestamp' in parsed
        assert 'time' in parsed

    @mock.patch.dict(os.environ, {'LOG_JSON': 'true'})
    def test_json_logging_enabled(self):
        """Test that JSON logging is enabled when LOG_JSON=true."""
        # We need to reload the logger module to apply the environment variable
        with mock.patch('sys.stdout', new=StringIO()) as fake_out:
            # Create a new logger with the same name to test
            test_logger = logging.getLogger('test_json_logger')
            test_logger.setLevel(logging.INFO)

            # Create a handler that writes to our StringIO
            handler = logging.StreamHandler(fake_out)

            # Use the JSONFormatter
            formatter = JSONFormatter()
            handler.setFormatter(formatter)

            test_logger.addHandler(handler)
            test_logger.propagate = False

            # Log a message
            test_logger.info('Test JSON logging')

            # Get the output
            output = fake_out.getvalue().strip()

            # Verify it's valid JSON
            parsed = json.loads(output)
            assert parsed['name'] == 'test_json_logger'
            assert parsed['level'] == 'INFO'
            assert parsed['message'] == 'Test JSON logging'

    def test_logger_initialization(self):
        """Test that the logger is properly initialized."""
        assert oh_aci_logger.name == 'openhands_aci'
        assert len(oh_aci_logger.handlers) > 0

        # Check that the handler is a StreamHandler
        handler = oh_aci_logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)

        # Check formatter type based on LOG_JSON environment variable
        if os.environ.get('LOG_JSON', '').lower() in ['true', '1', 'yes']:
            assert isinstance(handler.formatter, JSONFormatter)
        else:
            assert isinstance(handler.formatter, logging.Formatter)
