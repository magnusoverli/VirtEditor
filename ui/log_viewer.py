import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTextEdit, QPushButton, 
                            QHBoxLayout, QCheckBox, QLabel, QComboBox)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont

from utils.logger import log_signaler

class LogViewer(QDialog):
    """Dialog for viewing application logs in real-time"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Viewer")
        self.setMinimumSize(800, 400)
        
        # Set up the UI components
        self.setup_ui()
        
        # Connect to the log signaler
        log_signaler.logSignal.connect(self.add_log_message)
        
        # Auto-scroll timer
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self.check_auto_scroll)
        self.scroll_timer.start(100)  # Check every 100 ms
        
        # Add welcome message
        self.add_log_message("INFO", "Log viewer initialized")
        
    def setup_ui(self):
        """Set up the UI components"""
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Level filter
        self.level_label = QLabel("Filter level:")
        controls_layout.addWidget(self.level_label)
        
        self.level_combo = QComboBox()
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setCurrentText("INFO")  # Default to INFO
        self.level_combo.currentTextChanged.connect(self.apply_filter)
        controls_layout.addWidget(self.level_combo)
        
        # Auto-scroll checkbox
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        controls_layout.addWidget(self.auto_scroll_check)
        
        # Spacer
        controls_layout.addStretch()
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_log)
        controls_layout.addWidget(self.clear_button)
        
        layout.addLayout(controls_layout)
        
        # Log text display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.document().setMaximumBlockCount(1000)  # Limit for performance
        
        # Set monospace font for better log readability
        font = QFont("Consolas")
        if not font.exactMatch():
            font = QFont("Courier New")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(9)
        self.log_text.setFont(font)
        
        # Set background to a light color for better contrast
        self.log_text.setStyleSheet("background-color: #f5f5f5;")
        
        layout.addWidget(self.log_text)
        
        # Close button
        button_layout = QHBoxLayout()
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
    
    @pyqtSlot(str, str)
    def add_log_message(self, level, message):
        """Add a log message to the display"""
        # Filter by level
        level_index = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
        current_level_index = level_index.get(self.level_combo.currentText(), 1)
        message_level_index = level_index.get(level, 1)
        
        if message_level_index < current_level_index:
            return  # Skip messages below current filter level
        
        # Set text color based on level
        format = QTextCharFormat()
        
        if level == "DEBUG":
            format.setForeground(QColor("#666666"))  # Dark gray
        elif level == "INFO":
            format.setForeground(QColor("#000000"))  # Black
        elif level == "WARNING":
            format.setForeground(QColor("#FF8C00"))  # Dark orange
            format.setFontWeight(QFont.Weight.Bold)
        elif level == "ERROR":
            format.setForeground(QColor("#FF0000"))  # Red
            format.setFontWeight(QFont.Weight.Bold)
        elif level == "CRITICAL":
            format.setForeground(QColor("#FFFFFF"))  # White
            format.setBackground(QColor("#FF0000"))  # Red background
            format.setFontWeight(QFont.Weight.Bold)
        
        # Add message with proper formatting
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Save current format and restore it after insertText
        old_format = cursor.charFormat()
        cursor.setCharFormat(format)
        
        # Insert the message and a newline to ensure each log is on a separate line
        cursor.insertText(message + "\n")
        
        # Restore original format
        cursor.setCharFormat(old_format)
        
        # Auto-scroll if enabled
        if self.auto_scroll_check.isChecked():
            self.scroll_to_bottom()
    
    def check_auto_scroll(self):
        """Check if auto-scroll is needed"""
        if self.auto_scroll_check.isChecked():
            self.scroll_to_bottom()
    
    def scroll_to_bottom(self):
        """Scroll the log text to the bottom"""
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """Clear the log display"""
        self.log_text.clear()
        self.add_log_message("INFO", "Log cleared")
    
    def apply_filter(self):
        """Apply the level filter"""
        # For simplicity, just clear and let new messages come in
        self.log_text.clear()
        self.add_log_message("INFO", f"Log level set to {self.level_combo.currentText()}")
    
    def closeEvent(self, event):
        """Handle close event"""
        # Disconnect from the log signaler
        try:
            log_signaler.logSignal.disconnect(self.add_log_message)
        except:
            pass
        event.accept()