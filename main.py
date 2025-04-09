import sys
import os
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.logger import setup_logger

def main():
    # Set up the logger
    logger = setup_logger()
    logger.info("Application starting")
    
    # Create the application
    app = QApplication(sys.argv)
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    logger.info("Main window displayed")
    
    # Start the event loop
    exit_code = app.exec()
    logger.info(f"Application exiting with code {exit_code}")
    return exit_code

if __name__ == "__main__":
    sys.exit(main())