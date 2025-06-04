import json
import logging
import os
import time
from typing import Any, Dict, Optional

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
# Check if LOG_JSON is explicitly set to true, otherwise default to False
LOG_JSON_ENV = os.getenv('LOG_JSON', 'False')
LOG_JSON = LOG_JSON_ENV.lower() in ['true', '1', 'yes'] if LOG_JSON_ENV else False

DEBUG = os.getenv('DEBUG', 'False').lower() in ['true', '1', 'yes']
if DEBUG:
    LOG_LEVEL = 'DEBUG'

oh_aci_logger = logging.getLogger('openhands_aci')

current_log_level = logging.INFO
if LOG_LEVEL in logging.getLevelNamesMapping():
    current_log_level = logging.getLevelNamesMapping()[LOG_LEVEL]


class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the log record.
    """

    def __init__(self, fmt_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize the formatter with the specified format dictionary.
        """
        super().__init__()
        self.fmt_dict = fmt_dict if fmt_dict else {}

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the specified record as JSON.
        """
        record_dict = {
            'timestamp': int(time.time() * 1000),
            'time': self.formatTime(record, datefmt='%Y-%m-%d %H:%M:%S'),
            'name': record.name,
            'level': record.levelname,
            'message': record.getMessage(),
        }

        if record.exc_info:
            record_dict['exc_info'] = self.formatException(record.exc_info)

        if hasattr(record, 'stack_info') and record.stack_info:
            record_dict['stack_info'] = self.formatStack(record.stack_info)

        # Add custom fields from the record
        for key, value in self.fmt_dict.items():
            if key == 'asctime':
                # Already handled above
                continue
            if hasattr(record, key):
                record_dict[key] = getattr(record, key)

        return json.dumps(record_dict)


console_handler = logging.StreamHandler()
console_handler.setLevel(current_log_level)

if LOG_JSON:
    formatter: logging.Formatter = JSONFormatter()
else:
    formatter = logging.Formatter(
        '{asctime} - {name}:{levelname} - {message}',
        style='{',
        datefmt='%Y-%m-%d %H:%M',
    )

console_handler.setFormatter(formatter)

oh_aci_logger.setLevel(current_log_level)
oh_aci_logger.addHandler(console_handler)
oh_aci_logger.propagate = False
oh_aci_logger.debug('Logger initialized')
