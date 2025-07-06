# gui.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
from download_worker import DownloadWorker
import os
from threading import Semaphore

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class M3U8DownloaderGUI:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("M3U8 Multi Downloader")
        self.app.geometry("600x600")

        self.semaphore = Semaphore(3)  # Max 3 downloads at once
        self.download_widgets = {}  # Store UI for each download

        self.create_widgets()

    def create_widgets(self):
        self.url_label = ctk.CTkLabel(self.app, text="M3U8 URLs (one per line):")
        self.url_label.pack(pady=(10, 5))

        self.url_textbox = ctk.CTkTextbox(self.app, height=120)
        self.url_textbox.pack(padx=10)

        self.output_label = ctk.CTkLabel(self.app, text="Select Download Folder:")
        self.output_label.pack(pady=(15, 5))

        folder_frame = ctk.CTkFrame(self.app, fg_color="transparent")
        folder_frame.pack(pady=5)

        self.folder_entry = ctk.CTkEntry(folder_frame, width=400)
        self.folder_entry.pack(side="left", padx=10)

        browse_btn = ctk.CTkButton(folder_frame, text="Browse", command=self.browse_folder)
        browse_btn.pack(side="left")

        self.start_btn = ctk.CTkButton(self.app, text="Start Downloads", command=self.start_downloads)
        self.start_btn.pack(pady=15)

        self.scroll_frame = ctk.CTkScrollableFrame(self.app, width=560, height=300)
        self.scroll_frame.pack(pady=10)

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, path)

    def start_downloads(self):
        urls = self.url_textbox.get("1.0", "end").strip().splitlines()
        folder = self.folder_entry.get().strip()

        if not urls or not folder:
            messagebox.showerror("Error", "Please enter URLs and folder.")
            return

        for i, url in enumerate(urls):
            name = f"Video {i + 1}"
            output_file = os.path.join(folder, f"video_{i + 1}.mp4")
            self.add_download_row(name)

            worker = DownloadWorker(
                url=url,
                output_file=output_file,
                progress_callback=self.update_progress,
                done_callback=self.download_done,
                name=name
            )

            def run_worker(w):
                with self.semaphore:
                    w.start()

            from threading import Thread
            Thread(target=run_worker, args=(worker,)).start()

    def add_download_row(self, name):
        label = ctk.CTkLabel(self.scroll_frame, text=name)
        label.pack()

        progress = ctk.CTkProgressBar(self.scroll_frame, width=500)
        progress.set(0)
        progress.pack(pady=3)

        info = ctk.CTkLabel(self.scroll_frame, text="0 MB / 0 MB (0%) | Speed: 0 MB/s")
        info.pack(pady=(0, 10))

        self.download_widgets[name] = {
            "label": label,
            "progress": progress,
            "info": info
        }

    def update_progress(self, name, percent, downloaded_mb, total_mb, speed):
        widget = self.download_widgets.get(name)
        if widget:
            widget["progress"].set(percent / 100)
            widget["info"].configure(
                text=f"{downloaded_mb:.2f} MB / {total_mb:.2f} MB ({percent:.1f}%) | Speed: {speed:.2f} MB/s"
            )

    def download_done(self, name, success, msg):
        widget = self.download_widgets.get(name)
        if widget:
            status = "✅ Success" if success else f"❌ Failed: {msg}"
            widget["info"].configure(text=widget["info"].cget("text") + f" | {status}")

    def run(self):
        self.app.mainloop()
