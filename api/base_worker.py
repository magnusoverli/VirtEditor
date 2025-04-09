from PyQt6.QtCore import QThread, pyqtSignal, Qt
from utils.logger import logger

class BaseApiWorker(QThread):
    """Base worker thread class for API operations"""
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = True
    
    def stop(self):
        """Safely stop the thread"""
        logger.debug(f"Stopping {self.__class__.__name__}")
        self.running = False
        self.wait()  # Wait for the thread to finish