import os
import uuid
import webbrowser
import urllib.parse
import shutil
import glob
import subprocess
import platform
import customtkinter as ctk
from tkinter import messagebox

from downloader import DownloadWorker
from settings import load_settings
from settings_ui import build_settings_tab
from notifier import notify

import tkinter as tk

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None

        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9)
        )
        label.pack(ipadx=4, ipady=2)

    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None
            
def open_folder_in_explorer(path):
    try:
        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", os.path.normpath(path)])
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", "-R", path])
        else:  # Linux
            folder = os.path.dirname(path)
            subprocess.run(["xdg-open", folder])
    except Exception as e:
        print(f"[Open Folder Error] {e}")

def shorten_path_middle(path, max_length=80):
    """Shortens a file path by truncating the middle."""
    if len(path) <= max_length:
        return path
    part_len = (max_length - 5) // 2
    return path[:part_len] + "..." + path[-part_len:]

class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        self.clean_old_segments()
        self.max_parallel = self.settings.get("max_parallel", 5)

        self.workers = {}
        self.download_widgets = {}

        self.queue = []
        self.resume_queue = []
        self.active_downloads = 0

        root.title("M3U8 Video Downloader")
        root.geometry("800x500")
        root.minsize(600, 400)
        root.resizable(True, True)

        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)

        self.notebook = ctk.CTkTabview(root)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self.build_download_tab()
        self.build_log_tab()
        build_settings_tab(self.notebook, self.reload_settings)

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def clean_old_segments(self):
        segments_root = os.path.join(self.settings["output_dir"], "segments")
        if os.path.exists(segments_root):
            for folder in glob.glob(os.path.join(segments_root, "*")):
                shutil.rmtree(folder, ignore_errors=True)

    def reload_settings(self):
        self.settings = load_settings()
        self.max_parallel = self.settings.get("max_parallel", 3)
        self.log_box.insert("end", "[INFO] Settings reloaded.\n")
      
    def build_download_tab(self):
        tab = self.notebook.add("Download")
        frame = ctk.CTkFrame(tab)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
    
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=3)
        frame.grid_columnconfigure(2, weight=1)
        frame.grid_rowconfigure(3, weight=1)
    
        # ✅ CTkEntry with direct placeholder (NO StringVar)
        ctk.CTkLabel(frame, text="M3U8 URL:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.url_entry = ctk.CTkEntry(frame, placeholder_text="Enter M3U8 URL", width=400)
        self.url_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
    
        ctk.CTkLabel(frame, text="Video Name:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.name_entry = ctk.CTkEntry(frame, placeholder_text="Optional: Custom name (no .mp4)", width=400)
        self.name_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
    
        # ✅ Buttons with padding
        ctk.CTkButton(frame, text="Start Download", command=self.start_download)\
            .grid(row=2, column=1, pady=10, sticky="e", padx=(0, 15))
    
        ctk.CTkButton(frame, text="Cancel All", command=self.cancel_all)\
            .grid(row=2, column=2, pady=10, sticky="w", padx=(15, 0))
    
        # ✅ Scroll area for active downloads
        self.scroll_area = ctk.CTkScrollableFrame(frame, width=700, height=250)
        self.scroll_area.grid(row=3, column=0, columnspan=3, padx=10, pady=20, sticky="nsew")
                  
    def build_log_tab(self):
        tab = self.notebook.add("Logs")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        self.log_box = ctk.CTkTextbox(tab)
        self.log_box.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

    def on_close(self):
        for worker in self.workers.values():
            try:
                worker.cancel()
                if worker.segment_dir and os.path.exists(worker.segment_dir):
                    shutil.rmtree(worker.segment_dir, ignore_errors=True)
            except Exception as e:
                print(f"[Cleanup Error] {e}")
        self.root.destroy()

    # [Your download logic, callbacks, pause/cancel remain unchanged]

    def add_download_widget(self, name):
        frame = ctk.CTkFrame(self.scroll_area)
        frame.pack(fill="x", pady=5, padx=5)

        title = ctk.CTkLabel(frame, text=name, font=ctk.CTkFont(weight="bold"))
        title.pack(anchor="w", padx=10)

        progress = ctk.CTkProgressBar(frame)
        progress.set(0)
        progress.pack(fill="x", padx=10, pady=2)

        status = ctk.CTkLabel(frame, text="Starting...", text_color="yellow")
        status.pack(anchor="w", padx=10)

        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(anchor="w", padx=10, pady=5)

        pause_btn = ctk.CTkButton(btn_frame, text="Pause", width=80)
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", width=80)
        pause_btn.grid(row=0, column=0, padx=5)
        cancel_btn.grid(row=0, column=1, padx=5)

        self.download_widgets[name] = {
            "frame": frame,
            "progress": progress,
            "status": status,
            "pause_btn": pause_btn,
            "cancel_btn": cancel_btn,
            "paused": False
        }
        return pause_btn, cancel_btn
        
        
    def start_download(self):
        url = self.url_entry.get().strip()
        raw_name = self.name_entry.get().strip()
    
        if not url:
            messagebox.showerror("Missing Info", "Please enter a valid M3U8 URL.")
            return
    
        # Validate output path before proceeding
        output_path = self.settings.get("output_dir", "").strip()
        
        if (
            not output_path
            or output_path.isspace()
            or not os.path.exists(output_path)
            or not os.path.isdir(output_path)
            or not os.access(output_path, os.W_OK)
        ):
            messagebox.showwarning(
                "Invalid Download Folder",
                f"The folder:\n\n{output_path}\n\nis not valid or writable.\nPlease fix it in Settings."
            )
            return

        # If no name entered, generate from URL
        if not raw_name:
            parsed = urllib.parse.urlparse(url)
            base = os.path.basename(parsed.path)
            raw_name = os.path.splitext(base)[0] or parsed.netloc or "video"
            raw_name = raw_name.strip()[:30].replace(" ", "_") or "video"

            # Add a short unique suffix to avoid collision
            raw_name += "_" + str(uuid.uuid4())[:4]
   
        name = raw_name
        counter = 1
        while os.path.exists(os.path.join(output_path, name + ".mp4")):
            name = f"{raw_name}_{counter}"
            counter += 1
    
        if name in self.workers or any(n == name for n, _ in self.queue):
            messagebox.showwarning("Already Exists", f"Download '{name}' is already queued or running.")
            return
    
        pause_btn, cancel_btn = self.add_download_widget(name)
    
        def progress_callback(name, percent, downloaded_mb, estimated_mb, speed):
            def safe_update():
                w = self.download_widgets.get(name)
                if w:
                    w["progress"].set(percent / 100)
        
                    # === ETA calculation ===
                    remaining_mb = max(0, estimated_mb - downloaded_mb)
                    eta_seconds = remaining_mb / speed if speed > 0 else 0
                    mins, secs = divmod(int(eta_seconds), 60)
                    eta_text = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        
                    # === Updated status text
                    w["status"].configure(
                        text=(
                            f"⬇️ {percent:.2f}% - {downloaded_mb:.2f}MB / ~{estimated_mb:.2f}MB "
                            f"@ {speed:.2f}MB/s | ETA: {eta_text}"
                        ),
                        text_color="lightblue"
                    )
            self.root.after(0, safe_update)
           
        def done_callback(name, success, msg):
            def safe_gui_update():
                w = self.download_widgets.get(name)
                if not w:
                    return
        
                icon = "✅" if success else "❌"
                color = "lightgreen" if success else "red"
        
                if success:
                    w["status"].configure(text="✅ Download complete", text_color=color)
        
                    # Generate clickable, truncated path
                    output_path = os.path.join(self.settings["output_dir"], f"{name}.mp4")
                    short_display_path = shorten_path_middle(output_path, 80)
                    display_path = "📂 " + short_display_path
        
                    file_label = ctk.CTkLabel(
                        w["frame"],
                        text=display_path,
                        text_color="#00BFFF",
                        cursor="hand2"
                    )
        
                    # Place label above the Pause/Cancel buttons
                    btn_frame = w["pause_btn"].master
                    file_label.pack(before=btn_frame, anchor="w", padx=10, pady=(0, 5))
        
                    file_label.bind("<Button-1>", lambda e: open_folder_in_explorer(output_path))
                    Tooltip(file_label, "Open in Explorer")

                else:
                    short_msg = msg.strip().splitlines()[0][:80] + "..." if len(msg) > 80 else msg.strip().splitlines()[0]
                    w["status"].configure(text=f"{icon} {short_msg}", text_color=color)
        
                # Disable buttons
                w["pause_btn"].configure(state="disabled")
                w["cancel_btn"].configure(state="disabled")
        
                if msg.lower().startswith("cancelled"):
                    w["frame"].destroy()
                    self.download_widgets.pop(name, None)
        
                # Logging and notification
                clipped_msg = msg.strip()
                log_msg = clipped_msg[:1000] + "..." if len(clipped_msg) > 1000 else clipped_msg
                note_msg = clipped_msg[:250] + "..." if len(clipped_msg) > 250 else clipped_msg
        
                self.log_box.insert("end", f"[{name}] {log_msg}\n")
                self.log_box.see("end")
        
                self.active_downloads = max(0, self.active_downloads - 1)
                self.workers.pop(name, None)
                self.try_start_next()
        
                notify(f"Download {name}", note_msg)
        
            self.root.after(0, safe_gui_update)
            
        worker = DownloadWorker(
            name=name,
            url=url,
            output_dir=output_path,
            progress_callback=progress_callback,
            done_callback=done_callback,
            num_connections=self.settings["num_connections"]
        )
        self.workers[name] = worker
    
        pause_btn.configure(command=lambda: self.toggle_pause(name))
        cancel_btn.configure(command=lambda: self.cancel_download(name))
    
        self.queue.append((name, url))
        self.try_start_next()

    def try_start_next(self):
        while self.active_downloads < self.max_parallel and self.resume_queue:
            name = self.resume_queue.pop(0)
            if name in self.workers:
                worker = self.workers[name]
                if worker.is_alive():
                    worker.resume()
                else:
                    worker.start()
                self.download_widgets[name]["status"].configure(text="▶️ Resumed", text_color="skyblue")
                self.download_widgets[name]["pause_btn"].configure(text="Pause")
                self.download_widgets[name]["paused"] = False
                self.active_downloads += 1

        while self.active_downloads < self.max_parallel and self.queue:
            name, url = self.queue.pop(0)
            self._start_worker(name)

    def _start_worker(self, name):
        self.workers[name].start()
        self.download_widgets[name]["status"].configure(text="▶️ Downloading...", text_color="green")
        self.active_downloads += 1

    def toggle_pause(self, name):
        if name in self.workers:
            w = self.download_widgets[name]
            worker = self.workers[name]
            if w["paused"]:
                if self.active_downloads < self.max_parallel:
                    worker.resume()
                    w["pause_btn"].configure(text="Pause")
                    w["status"].configure(text="▶️ Resumed", text_color="skyblue")
                    w["paused"] = False
                    self.active_downloads += 1
                else:
                    if name not in self.resume_queue:
                        self.resume_queue.append(name)
                    w["status"].configure(text="⏳ Waiting to resume...", text_color="orange")
            else:
                worker.pause()
                w["pause_btn"].configure(text="Resume")
                w["status"].configure(text="⏸️ Paused", text_color="orange")
                w["paused"] = True
                self.active_downloads = max(0, self.active_downloads - 1)
                self.try_start_next()

    def cancel_download(self, name):
        if name in self.workers:
            self.workers[name].cancel()
            w = self.download_widgets[name]
            w["status"].configure(text="❌ Cancelling...", text_color="orange")
            w["pause_btn"].configure(state="disabled")
            w["cancel_btn"].configure(state="disabled")
            if name in self.resume_queue:
                self.resume_queue.remove(name)

    def cancel_all(self):
        for name in list(self.workers.keys()):
            self.cancel_download(name)
        self.log_box.insert("end", "[INFO] All downloads cancelled.\n")

