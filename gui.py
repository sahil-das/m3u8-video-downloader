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
        self.app.geometry("920x680")
        self.app.title("🎬 M3U8 Batch Video Downloader")

        self.output_dir = None
        self.downloads = {}
        self.active_downloads = 0
        self.queue = []
        self.resume_queue = []
        self.max_parallel = 3

        header = ctk.CTkLabel(self.app, text="📥 M3U8 Batch Video Downloader", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=10)

        # ── Control Frame ─────────────────────────────
        control_frame = ctk.CTkFrame(self.app)
        control_frame.pack(pady=5, fill="x", padx=10)

        
        self.folder_entry = ctk.CTkEntry(control_frame, width=500)
        self.folder_entry.insert(0, "No folder selected")
        self.folder_entry.configure(state="normal", text_color="gray")
        self.folder_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

        self.folder_button = ctk.CTkButton(control_frame, text="📁 Select Folder", command=self.select_folder, width=150)
        self.folder_button.grid(row=0, column=0, padx=10, pady=(10, 2), sticky="w")

        self.parallel_label = ctk.CTkLabel(control_frame, text="Maximum Parallel Downloads")
        self.parallel_label.grid(row=0, column=2, padx=10, pady=(10, 0), sticky="w")

        self.parallel_dropdown = ctk.CTkOptionMenu(control_frame, values=[str(i) for i in range(1, 11)],
                                                   command=self.set_parallel, width=100)
        self.parallel_dropdown.set("3")
        self.parallel_dropdown.grid(row=1, column=2, padx=10, pady=(0, 10), sticky="w")

        control_frame.grid_columnconfigure(1, weight=1)

        # ── Input Fields ──────────────────────────────
        self.url_entry = ctk.CTkEntry(self.app, placeholder_text="Enter M3U8 URL", width=700)
        self.url_entry.pack(pady=(15, 5))

        self.name_entry = ctk.CTkEntry(self.app, placeholder_text="Optional: Enter custom file name (without .mp4)", width=700)
        self.name_entry.pack(pady=(0, 10))

        self.download_button = ctk.CTkButton(self.app, text="🚀 Start Download", command=self.start_download)
        self.download_button.pack(pady=5)

        self.scrollable_frame = ctk.CTkScrollableFrame(self.app, width=870, height=450)
        self.scrollable_frame.pack(pady=10)

    def set_parallel(self, value):
        self.max_parallel = int(value)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir = folder
            self.folder_entry.configure(state="normal", text_color="lightgreen")
            self.folder_entry.delete(0, ctk.END)
            self.folder_entry.insert(0, folder)

    def start_download(self):
        folder_input = self.folder_entry.get().strip()
        if folder_input and os.path.isdir(folder_input):
            self.output_dir = folder_input
        if not self.output_dir:
            messagebox.showwarning("Folder Required", "Please select or enter a valid folder before starting download.")
            return

        self.url_entry.delete(0, ctk.END)
        self.name_entry.delete(0, ctk.END)

        name = custom_name if custom_name else str(uuid.uuid4())[:8]

        frame = ctk.CTkFrame(self.scrollable_frame)
        frame.pack(padx=10, pady=5, fill="x")

        title_text = custom_name if custom_name else url[:80] + "..."
        title = ctk.CTkLabel(frame, text=title_text, anchor="w", font=ctk.CTkFont(weight="bold"))
        title.pack(anchor="w", padx=10, pady=(5, 0))

        progress = ctk.CTkProgressBar(frame)
        progress.set(0)
        progress.pack(fill="x", padx=10, pady=5)

        status = ctk.CTkLabel(frame, text="⏳ Waiting...", text_color="yellow")
        status.pack(anchor="w", padx=10)

        btn_row = ctk.CTkFrame(frame)
        btn_row.pack(anchor="w", padx=10, pady=5)
        
        file_label = ctk.CTkLabel(frame, text="", text_color="gray")
        file_label.pack(anchor="w", padx=10, pady=(0, 5))

        pause_btn = ctk.CTkButton(btn_row, text="Pause", width=80)
        cancel_btn = ctk.CTkButton(btn_row, text="Cancel", width=80)
        pause_btn.grid(row=0, column=0, padx=5)
        cancel_btn.grid(row=0, column=1, padx=5)


        self.downloads[name] = {
            "url": url,
            "progress": progress,
            "status": status,
            "pause_btn": pause_btn,
            "cancel_btn": cancel_btn,
            "file_label": file_label,
            "frame": frame,
            "paused": False,
            "custom_name": name
        }

        pause_btn.configure(command=lambda: self.toggle_pause(name))
        cancel_btn.configure(command=lambda: self.cancel_download(name))

        self.queue.append((name, url))
        self.try_start_next()

    def try_start_next(self):
        while self.active_downloads < self.max_parallel and self.resume_queue:
            name = self.resume_queue.pop(0)
            d = self.downloads[name]
            if d["paused"]:
                d["worker"].resume()
                d["pause_btn"].configure(text="Pause")
                d["status"].configure(text="▶️ Resumed", text_color="skyblue")
                d["paused"] = False
                self.active_downloads += 1

        while self.active_downloads < self.max_parallel and self.queue:
            name, url = self.queue.pop(0)
            self.start_worker(name, url)

    def start_worker(self, name, url):
        self.active_downloads += 1
        file_name = self.downloads[name]["custom_name"]
        worker = DownloadWorker(
            name=file_name,
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
        d["status"].configure(
            text=f"⬇️ {percent:.2f}% | {downloaded_mb:.2f}MB / {total_mb:.2f}MB @ {speed:.2f} MB/s",
            text_color="lightblue"
        )

    def download_done(self, name, success, message):
        d = self.downloads[name]
        d["pause_btn"].configure(state="disabled")
        d["cancel_btn"].configure(state="disabled")

        if success:
            d["status"].configure(text=f"✅ {message}", text_color="lightgreen")
            output_path = os.path.join(self.output_dir, f"{d['custom_name']}.mp4")
            d["file_label"].configure(text=output_path, text_color="#00C0FF")
            d["file_label"].bind("<Button-1>", lambda e, path=output_path: webbrowser.open(f'file:///{path}'))
        else:
            d["status"].configure(text=f"❌ {message}", text_color="red")

        if not d.get("paused"):
            self.active_downloads -= 1

        self.try_start_next()

    def toggle_pause(self, name):
        d = self.downloads[name]

        if d["paused"]:
            if self.active_downloads < self.max_parallel:
                d["worker"].resume()
                d["pause_btn"].configure(text="Pause")
                d["status"].configure(text="▶️ Resumed", text_color="skyblue")
                d["paused"] = False
                self.active_downloads += 1
            else:
                d["status"].configure(text="⏳ Waiting to resume...", text_color="orange")
                if name not in self.resume_queue:
                    self.resume_queue.append(name)
        else:
            d["worker"].pause()
            d["pause_btn"].configure(text="Resume")
            d["status"].configure(text="⏸️ Paused", text_color="orange")
            d["paused"] = True
            self.active_downloads -= 1
            self.try_start_next()

    def cancel_download(self, name):
        d = self.downloads[name]
        d["worker"].cancel()
        d["status"].configure(text="❌ Cancelled", text_color="red")
        d["pause_btn"].configure(state="disabled")
        d["cancel_btn"].configure(state="disabled")
        if not d["paused"]:
            self.active_downloads -= 1
        if name in self.resume_queue:
            self.resume_queue.remove(name)
        self.try_start_next()

    def run(self):
        self.app.mainloop()


if __name__ == "__main__":
    M3U8DownloaderGUI().run()
