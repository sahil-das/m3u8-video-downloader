import ctypes
import customtkinter as ctk
from tkinter import filedialog, messagebox
from download_worker import DownloadWorker
import os
import uuid
import webbrowser
import tkinterdnd2
import tkinter as tk  # ⬅ Native Tkinter for Entry widgets

# 🛠 Fix blurry UI on high-DPI displays
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

class M3U8DownloaderGUI(tkinterdnd2.TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        ctk.set_widget_scaling(1.1)
        ctk.set_window_scaling(1.1)

        self.geometry("920x680")
        self.title("🎬 M3U8 Batch Video Downloader")

        self.output_dir = None
        self.downloads = {}
        self.active_downloads = 0
        self.queue = []
        self.resume_queue = []
        self.max_parallel = 3
        self.segment_threads = 8

        self.setup_gui()
        self.enable_drag_and_drop()

    def setup_gui(self):
        header = ctk.CTkLabel(self, text="📥 M3U8 Batch Video Downloader", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=10)

        control_frame = ctk.CTkFrame(self)
        control_frame.pack(pady=5, fill="x", padx=10)

        self.folder_button = ctk.CTkButton(control_frame, text="📁 Select Folder", command=self.select_folder, width=150)
        self.folder_button.grid(row=0, column=0, padx=10, pady=(10, 2), sticky="w")

        self.folder_entry = tk.Entry(control_frame, width=70)
        self.folder_entry.insert(0, "No folder selected")
        self.folder_entry.configure(fg="gray")
        self.folder_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")
        self.folder_entry.bind("<FocusIn>", self.clear_placeholder)
        self.folder_entry.bind("<FocusOut>", self.restore_placeholder)

        self.parallel_label = ctk.CTkLabel(control_frame, text="Maximum Parallel Downloads")
        self.parallel_label.grid(row=0, column=2, padx=10, pady=(10, 0), sticky="w")

        self.parallel_dropdown = ctk.CTkOptionMenu(control_frame, values=[str(i) for i in range(1, 11)],
                                                   command=self.set_parallel, width=100)
        self.parallel_dropdown.set("3")
        self.parallel_dropdown.grid(row=1, column=2, padx=10, pady=(0, 10), sticky="w")

        self.segment_label = ctk.CTkLabel(control_frame, text="Threads per Video")
        self.segment_label.grid(row=0, column=3, padx=10, pady=(10, 0), sticky="w")

        self.segment_dropdown = ctk.CTkOptionMenu(control_frame, values=["1", "2", "4", "8", "16", "32"],
                                                  command=self.set_segment_threads, width=100)
        self.segment_dropdown.set(str(self.segment_threads))
        self.segment_dropdown.grid(row=1, column=3, padx=10, pady=(0, 10), sticky="w")

        control_frame.grid_columnconfigure(1, weight=1)

        self.url_entry = tk.Entry(self, width=90)
        self.url_entry.insert(0, "Enter or drop M3U8 URL")
        self.url_entry.configure(fg="gray")
        self.url_entry.pack(pady=(15, 5))
        self.url_entry.bind("<FocusIn>", self.clear_url_placeholder)
        self.url_entry.bind("<FocusOut>", self.restore_url_placeholder)

        self.name_entry = ctk.CTkEntry(self, placeholder_text="Optional: Enter custom file name (without .mp4)", width=700)
        self.name_entry.pack(pady=(0, 10))

        self.download_button = ctk.CTkButton(self, text="🚀 Start Download", command=self.start_download)
        self.download_button.pack(pady=5)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=870, height=450)
        self.scrollable_frame.pack(pady=10)

    def enable_drag_and_drop(self):
        for entry, drop_handler, drop_type in [
            (self.url_entry, self.drop_url, "DND_Text"),
            (self.name_entry, self.drop_name, "DND_Text"),
            (self.folder_entry, self.drop_folder, "DND_Files")
        ]:
            entry.drop_target_register(drop_type)
            entry.dnd_bind('<<Drop>>', drop_handler)

    def drop_url(self, event):
        dropped = event.data.strip().strip('{}')
        if dropped.startswith("http") and ".m3u8" in dropped:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, dropped)
            self.url_entry.configure(fg="white")

    def drop_name(self, event):
        dropped = event.data.strip().strip('{}')
        if dropped.endswith(".mp4"):
            dropped = dropped[:-4]
        self.name_entry.delete(0, ctk.END)
        self.name_entry.insert(0, dropped)

    def drop_folder(self, event):
        dropped = event.data.strip().strip('{}')
        if os.path.isdir(dropped):
            self.output_dir = dropped
            self.folder_entry.configure(fg="lightgreen")
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, dropped)

    def clear_placeholder(self, event=None):
        if self.folder_entry.get() == "No folder selected":
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.configure(fg="white")

    def restore_placeholder(self, event=None):
        if not self.folder_entry.get().strip():
            self.folder_entry.insert(0, "No folder selected")
            self.folder_entry.configure(fg="gray")

    def clear_url_placeholder(self, event=None):
        if self.url_entry.get() == "Enter or drop M3U8 URL":
            self.url_entry.delete(0, tk.END)
            self.url_entry.configure(fg="white")

    def restore_url_placeholder(self, event=None):
        if not self.url_entry.get().strip():
            self.url_entry.insert(0, "Enter or drop M3U8 URL")
            self.url_entry.configure(fg="gray")

    # All remaining methods (start_download, try_start_next, etc.) remain unchanged

    def run(self):
        self.mainloop()

if __name__ == "__main__":
    M3U8DownloaderGUI().run()
