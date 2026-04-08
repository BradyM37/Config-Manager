"""
OptiLock Config Manager Launcher
Entry point for PyInstaller
"""

import sys
import os

# Handle frozen (PyInstaller) vs normal execution
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    application_path = sys._MEIPASS
else:
    # Running as script
    application_path = os.path.dirname(os.path.abspath(__file__))

# Add application path to sys.path
if application_path not in sys.path:
    sys.path.insert(0, application_path)

# Now import and run
from src.ui.app import main

if __name__ == "__main__":
    main()
