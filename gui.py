import ctypes
import customtkinter as ctk
from tkinter import filedialog, messagebox
from download_worker import DownloadWorker
import os
import uuid
import webbrowser
import tkinterdnd2  # ✅ Fix for drag and drop

# 🛠 Fix blurry UI on high-DPI displays
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

class M3U8DownloaderGUI(tkinterdnd2.TkinterDnD.Tk):  # ✅ Inherit from TkinterDnD.Tk
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

        self.folder_entry = ctk.CTkEntry(control_frame, width=500)
        self.folder_entry.insert(0, "No folder selected")
        self.folder_entry.configure(text_color="gray")
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

        self.url_entry = ctk.CTkEntry(self, placeholder_text="Enter or drop M3U8 URL", width=700)
        self.url_entry.pack(pady=(15, 5))

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
            self.url_entry.delete(0, ctk.END)
            self.url_entry.insert(0, dropped)
            self.url_entry.configure(text_color="white")

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
            self.folder_entry.configure(text_color="lightgreen")
            self.folder_entry.delete(0, ctk.END)
            self.folder_entry.insert(0, dropped)

    def clear_placeholder(self, event=None):
        if self.folder_entry.get() == "No folder selected":
            self.folder_entry.delete(0, ctk.END)
            self.folder_entry.configure(text_color="white")

    def restore_placeholder(self, event=None):
        if not self.folder_entry.get().strip():
            self.folder_entry.insert(0, "No folder selected")
            self.folder_entry.configure(text_color="gray")

    def set_parallel(self, value):
        self.max_parallel = int(value)

    def set_segment_threads(self, value):
        self.segment_threads = int(value)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir = folder
            self.folder_entry.configure(text_color="lightgreen")
            self.folder_entry.delete(0, ctk.END)
            self.folder_entry.insert(0, folder)

    def start_download(self):
        url = self.url_entry.get().strip()
        custom_name = self.name_entry.get().strip()

        if not url:
            messagebox.showerror("URL Required", "Please enter a valid M3U8 URL.")
            return

        folder_input = self.folder_entry.get().strip()
        if folder_input != "No folder selected" and os.path.isdir(folder_input):
            self.output_dir = folder_input
        if not self.output_dir:
            messagebox.showwarning("Folder Required", "Please select a valid output folder.")
            return

        self.url_entry.delete(0, ctk.END)
        self.name_entry.delete(0, ctk.END)

        short_name = custom_name if custom_name else str(uuid.uuid4())[:8]
        file_name = short_name + ".mp4"

        frame = ctk.CTkFrame(self.scrollable_frame)
        frame.pack(padx=10, pady=5, fill="x")

        title = ctk.CTkLabel(frame, text=custom_name or url[:80] + "...", anchor="w", font=ctk.CTkFont(weight="bold"))
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

        self.downloads[short_name] = {
            "url": url,
            "progress": progress,
            "status": status,
            "pause_btn": pause_btn,
            "cancel_btn": cancel_btn,
            "file_label": file_label,
            "frame": frame,
            "paused": False,
            "custom_name": short_name
        }

        pause_btn.configure(command=lambda: self.toggle_pause(short_name))
        cancel_btn.configure(command=lambda: self.cancel_download(short_name))

        self.queue.append((short_name, url))
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
        file_name = self.downloads[name]["custom_name"] + ".mp4"
        worker = DownloadWorker(
            name=name,
            url=url,
            output_dir=self.output_dir,
            progress_callback=self.update_progress,
            done_callback=self.download_done,
            num_connections=self.segment_threads
        )
        self.downloads[name]["worker"] = worker
        self.downloads[name]["file_name"] = file_name
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
            output_path = os.path.join(self.output_dir, d["file_name"])
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
        self.mainloop()

if __name__ == "__main__":
    M3U8DownloaderGUI().run()
