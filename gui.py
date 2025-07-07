import customtkinter as ctk
from tkinter import filedialog, messagebox
from download_worker import DownloadWorker
import os
import uuid
import webbrowser


class M3U8DownloaderGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.app = ctk.CTk()
        self.app.geometry("900x650")
        self.app.title("🎬 M3U8 Batch Video Downloader")

        self.output_dir = None
        self.downloads = {}
        self.active_downloads = 0
        self.queue = []
        self.max_parallel = 3

        header = ctk.CTkLabel(self.app, text="📥 M3U8 Batch Video Downloader", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=10)

        control_frame = ctk.CTkFrame(self.app)
        control_frame.pack(pady=5)

        self.folder_button = ctk.CTkButton(control_frame, text="📁 Select Folder", command=self.select_folder)
        self.folder_button.grid(row=0, column=0, padx=10, pady=10)

        self.folder_label = ctk.CTkLabel(control_frame, text="No folder selected", text_color="gray", anchor="w", width=500)
        self.folder_label.grid(row=0, column=1, padx=10)

        self.parallel_dropdown = ctk.CTkOptionMenu(control_frame, values=[str(i) for i in range(1, 11)],
                                                   command=self.set_parallel, width=100)
        self.parallel_dropdown.set("3")
        self.parallel_dropdown.grid(row=0, column=2, padx=10)

        self.url_entry = ctk.CTkEntry(self.app, placeholder_text="Enter M3U8 URL and press 'Start Download'", width=700)
        self.url_entry.pack(pady=10)

        self.download_button = ctk.CTkButton(self.app, text="🚀 Start Download", command=self.start_download)
        self.download_button.pack(pady=5)

        self.scrollable_frame = ctk.CTkScrollableFrame(self.app, width=850, height=440)
        self.scrollable_frame.pack(pady=10)

    def set_parallel(self, value):
        self.max_parallel = int(value)
        self.try_start_next()

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir = folder
            self.folder_label.configure(text=folder, text_color="lightgreen")

    def start_download(self):
        if not self.output_dir:
            messagebox.showwarning("Folder Required", "Please select a folder before starting download.")
            return

        url = self.url_entry.get().strip()
        if not url:
            return

        self.url_entry.delete(0, ctk.END)
        name = str(uuid.uuid4())[:8]

        frame = ctk.CTkFrame(self.scrollable_frame)
        frame.pack(padx=10, pady=5, fill="x")

        title = ctk.CTkLabel(frame, text=url[:80] + "...", anchor="w")
        title.pack(anchor="w", padx=10, pady=(5, 0))

        progress = ctk.CTkProgressBar(frame)
        progress.set(0)
        progress.pack(fill="x", padx=10, pady=5)

        status = ctk.CTkLabel(frame, text="⏳ Waiting...")
        status.pack(anchor="w", padx=10)

        btn_row = ctk.CTkFrame(frame)
        btn_row.pack(anchor="w", padx=10, pady=5)

        pause_btn = ctk.CTkButton(btn_row, text="Pause", width=80)
        cancel_btn = ctk.CTkButton(btn_row, text="Cancel", width=80)
        pause_btn.grid(row=0, column=0, padx=5)
        cancel_btn.grid(row=0, column=1, padx=5)

        file_label = ctk.CTkLabel(frame, text="", text_color="#00C0FF")
        file_label.pack(anchor="w", padx=10, pady=(0, 5))

        self.downloads[name] = {
            "url": url,
            "progress": progress,
            "status": status,
            "pause_btn": pause_btn,
            "cancel_btn": cancel_btn,
            "file_label": file_label,
            "frame": frame,
            "paused": False,
            "running": False
        }

        pause_btn.configure(command=lambda: self.toggle_pause(name))
        cancel_btn.configure(command=lambda: self.cancel_download(name))

        self.queue.append((name, url))
        self.try_start_next()

    def try_start_next(self):
        running = sum(1 for d in self.downloads.values()
                      if "worker" in d and d["worker"].is_alive() and not d.get("paused", False))
        self.active_downloads = running
    
        while self.active_downloads < self.max_parallel and self.queue:
            name, url = self.queue.pop(0)
            self.start_worker(name, url)


    def start_worker(self, name, url):
        self.active_downloads += 1
        self.downloads[name]["running"] = True
        self.downloads[name]["status"].configure(text="⬇️ Downloading...")
        worker = DownloadWorker(
            name=name,
            url=url,
            output_dir=self.output_dir,
            progress_callback=self.update_progress,
            done_callback=self.download_done
        )
        self.downloads[name]["worker"] = worker
        worker.start()

    def update_progress(self, name, percent, downloaded_mb, total_mb, speed):
        d = self.downloads[name]
        d["progress"].set(percent / 100)
        d["status"].configure(text=f"{percent:.2f}% | {downloaded_mb:.2f}MB / {total_mb:.2f}MB @ {speed:.2f} MB/s")

    def download_done(self, name, success, message):
        d = self.downloads[name]
        d["pause_btn"].configure(state="disabled")
        d["cancel_btn"].configure(state="disabled")
        d["running"] = False

        if success:
            d["status"].configure(text=f"✅ {message}", text_color="lightgreen")
            output_path = os.path.join(self.output_dir, f"{name}.mp4")
            d["file_label"].configure(text="Saved as: " + output_path, text_color="#00C0FF")
            d["file_label"].bind("<Button-1>", lambda e, path=output_path: webbrowser.open(f'file:///{path}'))
        else:
            d["status"].configure(text=f"❌ {message}", text_color="red")

        self.active_downloads -= 1
        self.try_start_next()

    def toggle_pause(self, name):
        d = self.downloads[name]
        if d["paused"]:
            # Try to resume only if under max_parallel
            running = sum(1 for d in self.downloads.values()
                          if "worker" in d and d["worker"].is_alive() and not d["paused"])
            if running >= self.max_parallel:
                d["status"].configure(text="⏸️ Waiting to resume...", text_color="orange")
                return  # Don't resume now
            d["worker"].resume()
            d["pause_btn"].configure(text="Pause")
            d["status"].configure(text="▶️ Resumed...")
            d["paused"] = False
            self.active_downloads += 1
        else:
            d["worker"].pause()
            d["pause_btn"].configure(text="Resume")
            d["status"].configure(text="⏸️ Paused")
            d["paused"] = True
            self.active_downloads -= 1
            self.try_start_next()
    

        if d["paused"]:
            d["paused"] = False
            d["pause_btn"].configure(text="Pause")
            d["worker"].resume()
            d["status"].configure(text="⬇️ Downloading...")
        else:
            d["paused"] = True
            d["pause_btn"].configure(text="Resume")
            if "worker" in d:
                d["worker"].pause()
            d["status"].configure(text="⏸️ Paused")
            self.active_downloads -= 1
            self.try_start_next()

    def cancel_download(self, name):
        d = self.downloads[name]
        d["paused"] = False
        if "worker" in d:
            d["worker"].cancel()
        d["status"].configure(text="❌ Cancelled", text_color="red")
        d["pause_btn"].configure(state="disabled")
        d["cancel_btn"].configure(state="disabled")
        d["running"] = False
        self.active_downloads -= 1
        self.try_start_next()

    def run(self):
        self.app.mainloop()
