import os
import uuid
import webbrowser
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, DND_TEXT, TkinterDnD

import customtkinter as ctk
from download_worker import DownloadWorker


class M3U8DownloaderGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.app = TkinterDnD.Tk()
        self.app.geometry("920x680")
        self.app.title("🎬 M3U8 Batch Video Downloader")

        self.output_dir = None
        self.downloads = {}
        self.active_downloads = 0
        self.queue = []
        self.resume_queue = []
        self.max_parallel = 3
        self.segment_threads = 8

        self.setup_gui()

    def setup_gui(self):
        header = ctk.CTkLabel(self.app, text="📥 M3U8 Batch Video Downloader", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=10)

        # ── Controls ──────────────────────
        control_frame = ctk.CTkFrame(self.app)
        control_frame.pack(pady=5, fill="x", padx=10)

        self.folder_button = ctk.CTkButton(control_frame, text="📁 Select Folder", command=self.select_folder, width=150)
        self.folder_button.grid(row=0, column=0, padx=10, pady=(10, 2), sticky="w")

        self.folder_entry = ctk.CTkEntry(control_frame, width=500)
        self.folder_entry.insert(0, "No folder selected")
        self.folder_entry.configure(text_color="gray")
        self.folder_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")
        self.folder_entry.bind("<FocusIn>", self.clear_placeholder)
        self.folder_entry.bind("<FocusOut>", self.restore_placeholder)
        self.folder_entry.drop_target_register(DND_FILES)
        self.folder_entry.dnd_bind('<<Drop>>', self.on_folder_drop)

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

        # ── Input Fields ──────────────────
        self.url_entry = ctk.CTkEntry(self.app, placeholder_text="Enter M3U8 URL", width=700)
        self.url_entry.pack(pady=(15, 5))
        self.url_entry.drop_target_register(DND_TEXT)
        self.url_entry.dnd_bind('<<Drop>>', self.on_url_drop)

        self.name_entry = ctk.CTkEntry(self.app, placeholder_text="Optional: Enter custom file name (without .mp4)", width=700)
        self.name_entry.pack(pady=(0, 10))
        self.name_entry.drop_target_register(DND_TEXT)
        self.name_entry.dnd_bind('<<Drop>>', self.on_name_drop)

        self.download_button = ctk.CTkButton(self.app, text="🚀 Start Download", command=self.start_download)
        self.download_button.pack(pady=5)

        self.scrollable_frame = ctk.CTkScrollableFrame(self.app, width=870, height=450)
        self.scrollable_frame.pack(pady=10)

    # ── DnD Handlers ─────────────────────
    def on_folder_drop(self, event):
        path = event.data.strip().strip("{").strip("}")
        if os.path.isdir(path):
            self.output_dir = path
            self.folder_entry.configure(text_color="lightgreen")
            self.folder_entry.delete(0, ctk.END)
            self.folder_entry.insert(0, path)

    def on_url_drop(self, event):
        text = event.data.strip()
        if text.startswith("http"):
            self.url_entry.delete(0, ctk.END)
            self.url_entry.insert(0, text)

    def on_name_drop(self, event):
        text = os.path.basename(event.data.strip())
        base = os.path.splitext(text)[0]
        self.name_entry.delete(0, ctk.END)
        self.name_entry.insert(0, base)

    # (The rest of the code remains unchanged — includes start_download, update_progress, etc.)

    def clear_placeholder(self, event=None):
        if self.folder_entry.get() == "No folder selected":
            self.folder_entry.delete(0, ctk.END)
            self.folder_entry.configure(text_color="white")

    def restore_placeholder(self, event=None):
        if not self.folder_entry.get().strip():
            self.folder_entry.insert(0, "No folder selected")
            self.folder_entry.configure(text_color="gray")

    def set_parallel(self, value): self.max_parallel = int(value)
    def set_segment_threads(self, value): self.segment_threads = int(value)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir = folder
            self.folder_entry.configure(text_color="lightgreen")
            self.folder_entry.delete(0, ctk.END)
            self.folder_entry.insert(0, folder)

    # ... [KEEP all the rest of the methods as in your original gui.py]
    # start_download(), try_start_next(), start_worker(), update_progress(),
    # download_done(), toggle_pause(), cancel_download()

    def run(self):
        self.app.mainloop()


if __name__ == "__main__":
    M3U8DownloaderGUI().run()