import customtkinter as ctk
from tkinter import filedialog, messagebox
from download_worker import DownloadWorker
import os
import uuid
import threading

MAX_ACTIVE_DOWNLOADS = 2


class M3U8DownloaderGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.app = ctk.CTk()
        self.app.geometry("800x600")
        self.app.title("M3U8 Batch Downloader")

        self.output_dir = None
        self.downloads = {}
        self.download_queue = []
        self.active_downloads = 0

        self.folder_button = ctk.CTkButton(self.app, text="Select Download Folder", command=self.select_folder)
        self.folder_button.pack(pady=10)

        self.folder_label = ctk.CTkLabel(self.app, text="No folder selected", text_color="gray")
        self.folder_label.pack()

        self.url_entry = ctk.CTkEntry(self.app, placeholder_text="Enter M3U8 URL", width=600)
        self.url_entry.pack(pady=10)

        self.download_button = ctk.CTkButton(self.app, text="Start Download", command=self.enqueue_download)
        self.download_button.pack(pady=5)

        self.scrollable_frame = ctk.CTkScrollableFrame(self.app, width=750, height=480)
        self.scrollable_frame.pack(pady=10)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir = folder
            self.folder_label.configure(text=f"Selected Folder: {folder}", text_color="lightgreen")

    def enqueue_download(self):
        url = self.url_entry.get().strip()

        if not self.output_dir:
            messagebox.showwarning("No Folder Selected", "Please select a download folder before starting.")
            return

        if not url:
            return

        self.url_entry.delete(0, ctk.END)
        name = str(uuid.uuid4())[:8]

        # UI for this download
        label = ctk.CTkLabel(self.scrollable_frame, text=f"{url[:60]}...", wraplength=700)
        label.pack(anchor="w", padx=10, pady=3)

        progress = ctk.CTkProgressBar(self.scrollable_frame, width=700)
        progress.set(0)
        progress.pack(padx=10, pady=3)

        status = ctk.CTkLabel(self.scrollable_frame, text="Queued...")
        status.pack(anchor="w", padx=10)

        btn_frame = ctk.CTkFrame(self.scrollable_frame)
        btn_frame.pack(pady=3)

        pause_btn = ctk.CTkButton(btn_frame, text="Pause")
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel")

        pause_btn.grid(row=0, column=0, padx=5)
        cancel_btn.grid(row=0, column=1, padx=5)

        self.downloads[name] = {
            "url": url,
            "label": label,
            "progress": progress,
            "status": status,
            "pause_btn": pause_btn,
            "cancel_btn": cancel_btn,
            "paused": False,
            "worker": None
        }

        pause_btn.configure(command=lambda: self.toggle_pause(name))
        cancel_btn.configure(command=lambda: self.cancel_download(name))

        self.download_queue.append(name)
        self.try_start_next()

    def try_start_next(self):
        while self.active_downloads < MAX_ACTIVE_DOWNLOADS and self.download_queue:
            name = self.download_queue.pop(0)
            info = self.downloads[name]

            worker = DownloadWorker(
                name=name,
                url=info["url"],
                output_dir=self.output_dir,
                progress_callback=self.update_progress,
                done_callback=self.download_done
            )
            self.downloads[name]["worker"] = worker
            self.downloads[name]["status"].configure(text="Starting...")
            self.active_downloads += 1
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
        if d["worker"]:
            d["worker"].cancel()
        d["status"].configure(text="❌ Cancelled")
        d["pause_btn"].configure(state="disabled")
        d["cancel_btn"].configure(state="disabled")

        if self.downloads[name]["worker"].is_alive():
            self.active_downloads -= 1

        self.try_start_next()

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

        self.active_downloads -= 1
        self.try_start_next()

    def run(self):
        self.app.mainloop()
