# main.py
import customtkinter as ctk
from gui import DownloaderApp
from settings import load_settings
import os
import sys

def resource_path(relative):
    """ Get absolute path to resource (for PyInstaller or local dev) """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)

if __name__ == "__main__":
    config = load_settings()
    ctk.set_appearance_mode(config.get("theme", "dark"))
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()

    # ✅ Set taskbar and window icon
    icon_path = resource_path("assets/icon.ico")
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)

    app = DownloaderApp(root)
    root.mainloop()
