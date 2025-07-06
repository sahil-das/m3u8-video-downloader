import customtkinter as ctk
from tkinter import filedialog, messagebox
from download_worker import DownloadWorker
import os
import uuid
import webbrowser
import threading

class M3U8DownloaderGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.app = ctk.CTk()
        self.app.geometry("800x700")
        self.app.title("M3U8 Batch Downloader")

        self.output_dir = None
        self.downloads = {}
        self.active_downloads = 0
        self.download_queue = []
        self.max_active_downloads = 5

        self.folder_button = ctk.CTkButton(self.app, text="Select Download Folder", command=self.select_folder)
        self.folder_button.pack(pady=5)

        self.folder_label = ctk.CTkLabel(self.app, text="No folder selected", text_color="gray")
        self.folder_label.pack()

        self.url_entry = ctk.CTkEntry(self.app, placeholder_text="Enter M3U8 URL", width=600)
        self.url_entry.pack(pady=5)

        self.name_entry = ctk.CTkEntry(self.app, placeholder_text="Optional: Rename file (without extension)", width=400)
        self.name_entry.pack(pady=5)

        self.start_button = ctk.CTkButton(self.app, text="Start Download", command=self.start_download)
        self.start_button.pack(pady=5)

        self.limit_dropdown = ctk.CTkOptionMenu(self.app, values=[str(i) for i in range(1, 11)], command=self.set_max_downloads)
        self.limit_dropdown.set(str(self.max_active_downloads))
        self.limit_dropdown.pack(pady=5)

        self.scrollable_frame = ctk.CTkScrollableFrame(self.app, width=750, height=480)
        self.scrollable_frame.pack(pady=10)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir = folder
            self.folder_label.configure(text=f"Download to: {folder}", text_color="lightgreen")

    def set_max_downloads(self, value):
        self.max_active_downloads = int(value)
        self.try_start_queued_downloads()

    def start_download(self):
        if not self.output_dir:
            messagebox.showwarning("Select Folder", "Please select a download folder first.")
            return

        url = self.url_entry.get().strip()
        if not url:
            return

        self.url_entry.delete(0, ctk.END)
        rename = self.name_entry.get().strip()
        self.name_entry.delete(0, ctk.END)

        name = rename if rename else str(uuid.uuid4())[:8]

        label = ctk.CTkLabel(self.scrollable_frame, text=f"{url[:60]}...", wraplength=700)
        label.pack(anchor="w", padx=10, pady=2)

        progress = ctk.CTkProgressBar(self.scrollable_frame, width=700)
        progress.set(0)
        progress.pack(padx=10, pady=2)

        status = ctk.CTkLabel(self.scrollable_frame, text="Queued...")
        status.pack(anchor="w", padx=10)

        btn_frame = ctk.CTkFrame(self.scrollable_frame)
        btn_frame.pack(pady=2)

        pause_btn = ctk.CTkButton(btn_frame, text="Pause")
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel")

        pause_btn.grid(row=0, column=0, padx=5)
        cancel_btn.grid(row=0, column=1, padx=5)

        path_label = ctk.CTkLabel(self.scrollable_frame, text="", text_color="#00ffff", cursor="hand2")
        path_label.pack(anchor="w", padx=10)

        worker = DownloadWorker(
            name=name,
            url=url,
            output_dir=self.output_dir,
            progress_callback=self.update_progress,
            done_callback=self.download_done
        )

        self.downloads[name] = {
            "worker": worker,
            "progress": progress,
            "status": status,
            "pause_btn": pause_btn,
            "cancel_btn": cancel_btn,
            "label": label,
            "paused": False,
            "path": os.path.join(self.output_dir, f"{name}.mp4"),
            "path_label": path_label
        }

        pause_btn.configure(command=lambda: self.toggle_pause(name))
        cancel_btn.configure(command=lambda: self.cancel_download(name))
        path_label.bind("<Button-1>", lambda e, n=name: self.open_file_folder(n))

        self.download_queue.append(name)
        self.try_start_queued_downloads()

    def try_start_queued_downloads(self):
        while self.download_queue and self.active_downloads < self.max_active_downloads:
            name = self.download_queue.pop(0)
            worker = self.downloads[name]["worker"]
            self.downloads[name]["status"].configure(text="Downloading...")
            worker.start()
            self.active_downloads += 1

    def toggle_pause(self, name):
        d = self.downloads[name]
        if d["paused"]:
            d["worker"].resume()
            d["pause_btn"].configure(text="Pause")
            d["paused"] = False
            self.try_start_queued_downloads()
        else:
            d["worker"].pause()
            d["pause_btn"].configure(text="Resume")
            d["paused"] = True
            d["status"].configure(text="Paused")
            self.active_downloads -= 1
            self.try_start_queued_downloads()

    def cancel_download(self, name):
        d = self.downloads[name]
        d["worker"].cancel()
        d["status"].configure(text="❌ Cancelled")
        d["pause_btn"].configure(state="disabled")
        d["cancel_btn"].configure(state="disabled")
        self.active_downloads -= 1
        self.try_start_queued_downloads()

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

            if success:
                path = d["path"]
                d["path_label"].configure(text=path)
            self.active_downloads -= 1
            self.try_start_queued_downloads()

    def open_file_folder(self, name):
        d = self.downloads[name]
        path = d["path"]
        if os.path.exists(path):
            folder = os.path.dirname(path)
            webbrowser.open(folder)

    def run(self):
        self.app.mainloop()
