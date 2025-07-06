import customtkinter as ctk
from tkinter import filedialog
from download_worker import DownloadWorker
import os
import uuid


class M3U8DownloaderGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.app = ctk.CTk()
        self.app.geometry("800x600")
        self.app.title("M3U8 Batch Downloader")

        self.output_dir = None
        self.downloads = {}

        self.folder_button = ctk.CTkButton(self.app, text="Select Download Folder", command=self.select_folder)
        self.folder_button.pack(pady=10)

        self.url_entry = ctk.CTkEntry(self.app, placeholder_text="Enter M3U8 URL", width=600)
        self.url_entry.pack(pady=10)

        self.download_button = ctk.CTkButton(self.app, text="Start Download", command=self.start_download)
        self.download_button.pack(pady=5)

        self.scrollable_frame = ctk.CTkScrollableFrame(self.app, width=750, height=480)
        self.scrollable_frame.pack(pady=10)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir = folder

    def start_download(self):
        if not self.output_dir:
            return

        url = self.url_entry.get().strip()
        if not url:
            return

        self.url_entry.delete(0, ctk.END)

        name = str(uuid.uuid4())[:8]

        # UI elements for this download
        label = ctk.CTkLabel(self.scrollable_frame, text=f"{url[:60]}...", wraplength=700)
        label.pack(anchor="w", padx=10, pady=3)

        progress = ctk.CTkProgressBar(self.scrollable_frame, width=700)
        progress.set(0)
        progress.pack(padx=10, pady=3)

        status = ctk.CTkLabel(self.scrollable_frame, text="Starting...")
        status.pack(anchor="w", padx=10)

        btn_frame = ctk.CTkFrame(self.scrollable_frame)
        btn_frame.pack(pady=3)

        pause_btn = ctk.CTkButton(btn_frame, text="Pause")
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel")

        pause_btn.grid(row=0, column=0, padx=5)
        cancel_btn.grid(row=0, column=1, padx=5)

        # Worker thread
        worker = DownloadWorker(
            name=name,
            url=url,
            output_dir=self.output_dir,
            progress_callback=self.update_progress,
            done_callback=self.download_done
        )

        # Store everything
        self.downloads[name] = {
            "worker": worker,
            "progress": progress,
            "status": status,
            "pause_btn": pause_btn,
            "cancel_btn": cancel_btn,
            "paused": False,
        }

        # Bind pause/resume
        pause_btn.configure(command=lambda: self.toggle_pause(name))
        cancel_btn.configure(command=lambda: self.cancel_download(name))

        worker.start()

    def toggle_pause(self, name):
        d = self.downloads[name]
        if d["paused"]:
            d["worker"].resume()
            d["pause_btn"].configure(text="Pause")
            d["paused"] = False
        else:
            d["worker"].pause()
            d["pause_btn"].configure(text="Resume")
            d["paused"] = True

    def cancel_download(self, name):
        d = self.downloads[name]
        d["worker"].cancel()
        d["status"].configure(text="❌ Cancelled")
        d["pause_btn"].configure(state="disabled")
        d["cancel_btn"].configure(state="disabled")

    def update_progress(self, name, percent, downloaded_mb, total_mb, speed):
        d = self.downloads.get(name)
        if d:
            d["progress"].set(percent / 100)
            d["status"].configure(
                text=f"{percent:.2f}% | {downloaded_mb:.2f}MB / {total_mb:.2f}MB | {speed:.2f}MB/s"
            )

    def download_done(self, name, success, msg):
        d = self.downloads.get(name)
        if d:
            d["status"].configure(text=f"{'✅' if success else '❌'} {msg}")
            d["pause_btn"].configure(state="disabled")
            d["cancel_btn"].configure(state="disabled")

    def run(self):
        self.app.mainloop()
