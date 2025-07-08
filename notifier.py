import os
import sys
from plyer import notification
from settings import load_settings

def resource_path(relative_path):
    """
    Get absolute path to resource, works for PyInstaller and dev.
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

def notify(title, message):
    settings = load_settings()
    
    if not settings.get("enable_notifications", True):
        return

    try:
        # Truncate message for Windows toast limit
        message = message[:240] + "..." if len(message) > 240 else message

        icon_path = resource_path("assets/icon.ico")
        if not os.path.isfile(icon_path):
            icon_path = None  # Avoid failure if icon is missing

        notification.notify(
            title=title,
            message=message,
            app_name="M3U8 Downloader",
            app_icon=icon_path,
            timeout=5  # seconds
        )
    except Exception as e:
        print(f"[Notifier] Failed to show notification: {e}")
