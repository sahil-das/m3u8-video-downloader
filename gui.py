import customtkinter as ctk
from tkinter import filedialog, messagebox
from download_worker import DownloadWorker
import os
import uuid
import webbrowser

class M3U8DownloaderGUI:
def init(self):
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
    self.segment_threads = 8  # ✅ Default value for segment threads  

    header = ctk.CTkLabel(self.app, text="📥 M3U8 Batch Video Downloader", font=ctk.CTkFont(size=20, weight="bold"))  
    header.pack(pady=10)  

    # ── Control Frame ─────────────────────────────  
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

    # ── Parallel Downloads Dropdown ─────────────────────  
    self.parallel_label = ctk.CTkLabel(control_frame, text="Maximum Parallel Downloads")  
    self.parallel_label.grid(row=0, column=2, padx=10, pady=(10, 0), sticky="w")  

    self.parallel_dropdown = ctk.CTkOptionMenu(control_frame, values=[str(i) for i in range(1, 11)],  
                                               command=self.set_parallel, width=100)  
    self.parallel_dropdown.set("3")  
    self.parallel_dropdown.grid(row=1, column=2, padx=10, pady=(0, 10), sticky="w")  

    # ── Segment Threads Dropdown ────────────────────────  
    self.segment_label = ctk.CTkLabel(control_frame, text="Threads per Video")  
    self.segment_label.grid(row=0, column=3, padx=10, pady=(10, 0), sticky="w")  

    self.segment_dropdown = ctk.CTkOptionMenu(control_frame, values=["1", "2", "4", "8", "16", "32"],  
                                              command=self.set_segment_threads, width=100)  
    self.segment_dropdown.set(str(self.segment_threads))  
    self.segment_dropdown.grid(row=1, column=3, padx=10, pady=(0, 10), sticky="w")  

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

def clear_placeholder(self, event=None):  
    current = self.folder_entry.get()  
    if current == "No folder selected":  
        self.folder_entry.delete(0, ctk.END)  
        self.folder_entry.configure(text_color="white")  

def restore_placeholder(self, event=None):  
    current = self.folder_entry.get().strip()  
    if not current:  
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

# (Rest of your code remains unchanged...)  

def run(self):  
    self.app.mainloop()

if name == "main":
M3U8DownloaderGUI().run()

