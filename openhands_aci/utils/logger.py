import logging
import os

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

DEBUG = os.getenv('DEBUG', 'False').lower() in ['true', '1', 'yes']
if DEBUG:
    LOG_LEVEL = 'DEBUG'

oh_aci_logger = logging.getLogger('openhands_aci')

current_log_level = logging.INFO
if LOG_LEVEL in logging.getLevelNamesMapping():
    current_log_level = logging.getLevelNamesMapping()[LOG_LEVEL]

console_handler = logging.StreamHandler()
console_handler.setLevel(current_log_level)
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
