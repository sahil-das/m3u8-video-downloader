# gui.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
from download_worker import DownloadWorker

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class M3U8DownloaderGUI:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("M3U8 Video Downloader")
        self.app.geometry("500x400")
        self.create_widgets()

    def create_widgets(self):
        self.url_label = ctk.CTkLabel(self.app, text="M3U8 URL:")
        self.url_label.pack(pady=10)

        self.url_entry = ctk.CTkEntry(self.app, width=400)
        self.url_entry.pack()

        self.output_label = ctk.CTkLabel(self.app, text="Save As (.mp4):")
        self.output_label.pack(pady=10)

        frame = ctk.CTkFrame(self.app, fg_color="transparent")
        frame.pack()

        self.output_entry = ctk.CTkEntry(frame, width=300)
        self.output_entry.pack(side="left", padx=(0, 10))

        browse_btn = ctk.CTkButton(frame, text="Browse", command=self.browse_file)
        browse_btn.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(self.app, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(20, 10))

        self.progress_info_label = ctk.CTkLabel(self.app, text="Downloaded: 0 MB / 0 MB (0%)")
        self.progress_info_label.pack()

        self.download_speed_label = ctk.CTkLabel(self.app, text="Speed: 0 MB/s")
        self.download_speed_label.pack(pady=(0, 10))

        self.download_btn = ctk.CTkButton(self.app, text="Download", command=self.start_download)
        self.download_btn.pack(pady=10)

    def browse_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
        if path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, path)

    def start_download(self):
        url = self.url_entry.get().strip()
        output_file = self.output_entry.get().strip()

        if not url or not output_file:
            messagebox.showerror("Error", "Please enter both M3U8 URL and output file path.")
            return

        self.progress_bar.set(0)
        self.download_info_text("Downloaded: 0 MB / 0 MB (0%)")
        self.download_speed_label.configure(text="Speed: 0 MB/s")
        self.download_btn.configure(state="disabled", text="Downloading...")

        self.worker = DownloadWorker(
            url=url,
            output_file=output_file,
            progress_callback=self.update_progress,
            done_callback=self.download_done
        )
        self.worker.start()

    def update_progress(self, percent, downloaded_mb, total_mb, speed):
        self.progress_bar.set(percent / 100)
        self.progress_info_label.configure(
            text=f"Downloaded: {downloaded_mb:.2f} MB / {total_mb:.2f} MB ({percent:.1f}%)"
        )
        self.download_speed_label.configure(text=f"Speed: {speed:.2f} MB/s")

    def download_info_text(self, text):
        self.progress_info_label.configure(text=text)

    def download_done(self, success, msg):
        self.download_btn.configure(state="normal", text="Download")
        if success:
            messagebox.showinfo("Success", "Download complete and converted to MP4!")
        else:
            messagebox.showerror("Error", f"Download failed: {msg}")

    def run(self):
        self.app.mainloop()
