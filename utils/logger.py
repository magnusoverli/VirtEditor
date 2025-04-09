import os
import logging
import sys
import datetime
from logging.handlers import RotatingFileHandler
from PyQt6.QtCore import QObject, pyqtSignal, Qt

class LogSignaler(QObject):
    """Signal emitter for log messages"""
    logSignal = pyqtSignal(str, str)  # level, message

# Create a custom logger
logger = logging.getLogger('device_config_app')
logger.setLevel(logging.DEBUG)

# Create signal emitter
log_signaler = LogSignaler()

# Create log directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Create formatters
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

class SignalHandler(logging.Handler):
    """Handler to emit signals on log events"""
    def __init__(self):
        super().__init__()
        self.setFormatter(file_formatter)
        self.setLevel(logging.DEBUG)

    def emit(self, record):
        try:
            # Format timestamp for better readability - fixed formatting
            dt = datetime.datetime.fromtimestamp(record.created)
            timestamp = f"{dt.strftime('%Y-%m-%d %H:%M:%S')}.{int(dt.microsecond/1000):03d}"
            
            # Format message with clear structure
            formatted_msg = f"{timestamp} - {record.levelname} - {record.name} - {record.getMessage()}"
            
            # Emit signal with level and message
            log_signaler.logSignal.emit(record.levelname, formatted_msg)
        except Exception as e:
            # Print error to console for debugging
            print(f"Error in log handler: {str(e)}")
            self.handleError(record)

# Create handlers
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)

file_handler = RotatingFileHandler(
    os.path.join(log_dir, 'device_config_app.log'),
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)

signal_handler = SignalHandler()

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(signal_handler)

def setup_logger():
    """Set up the logger for use in the application"""
    # This function is mainly to ensure the logger is initialized
    return logger