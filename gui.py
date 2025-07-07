from tkinter import *
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import subprocess
import os
import re

class M3U8DownloaderGUI:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("M3U8 Downloader")
        self.root.geometry("600x300")
        self.root.configure(bg="#1e1e1e")
        self.root.resizable(False, False)

        self.setup_ui()
        self.enable_drag_and_drop()

    def setup_ui(self):
        self.url_label = Label(self.root, text="M3U8 URL:", fg="white", bg="#1e1e1e", anchor="w")
        self.url_label.pack(fill="x", padx=10, pady=(15, 0))
        self.url_entry = Entry(self.root, bg="white", fg="black", width=80)
        self.url_entry.pack(padx=10, pady=5)

        self.name_label = Label(self.root, text="Video Name:", fg="white", bg="#1e1e1e", anchor="w")
        self.name_label.pack(fill="x", padx=10, pady=(10, 0))
        self.name_entry = Entry(self.root, bg="white", fg="black", width=80)
        self.name_entry.pack(padx=10, pady=5)

        self.folder_label = Label(self.root, text="Output Folder:", fg="white", bg="#1e1e1e", anchor="w")
        self.folder_label.pack(fill="x", padx=10, pady=(10, 0))

        folder_frame = Frame(self.root, bg="#1e1e1e")
        folder_frame.pack(padx=10, pady=5, fill="x")

        self.folder_entry = Entry(folder_frame, bg="white", fg="black", width=60)
        self.folder_entry.pack(side="left", fill="x", expand=True)

        self.browse_button = Button(folder_frame, text="Browse", command=self.browse_folder)
        self.browse_button.pack(side="left", padx=(10, 0))

        self.download_button = Button(self.root, text="Download", command=self.start_download, bg="#3a86ff", fg="white", width=20)
        self.download_button.pack(pady=20)

    def enable_drag_and_drop(self):
        self.url_entry.drop_target_register(DND_FILES)
        self.url_entry.dnd_bind('<<Drop>>', self.drop_url)

        self.name_entry.drop_target_register(DND_FILES)
        self.name_entry.dnd_bind('<<Drop>>', self.drop_name)

        self.folder_entry.drop_target_register(DND_FILES)
        self.folder_entry.dnd_bind('<<Drop>>', self.drop_folder)

    def drop_url(self, event):
        raw = event.data.strip()
        match = re.search(r'(https?://[^\s]+\.m3u8)', raw)
        if match:
            self.url_entry.delete(0, END)
            self.url_entry.insert(0, match.group(1))
        else:
            messagebox.showwarning("Invalid URL", "Please drop a valid .m3u8 link.")

    def drop_name(self, event):
        path = self._clean_path(event.data)
        if os.path.isfile(path):
            name = os.path.splitext(os.path.basename(path))[0]
            self.name_entry.delete(0, END)
            self.name_entry.insert(0, name)
        else:
            messagebox.showwarning("Invalid File", "Please drop a valid file.")

    def drop_folder(self, event):
        path = self._clean_path(event.data)
        if os.path.isdir(path):
            self.folder_entry.delete(0, END)
            self.folder_entry.insert(0, path)
        else:
            messagebox.showwarning("Invalid Folder", "Please drop a valid folder.")

    def _clean_path(self, raw_path):
        # Remove curly braces and split in case of multiple files
        cleaned = raw_path.strip().strip('{}').split()[0]
        return cleaned

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_entry.delete(0, END)
            self.folder_entry.insert(0, path)

    def start_download(self):
        url = self.url_entry.get().strip()
        name = self.name_entry.get().strip()
        folder = self.folder_entry.get().strip()

        if not url or not name or not folder:
            messagebox.showerror("Missing Fields", "Please fill all fields.")
            return

        output_path = os.path.join(folder, f"{name}.mp4")
        try:
            subprocess.run(['python', 'downloader.py', url, output_path], check=True)
            messagebox.showinfo("Success", f"Video downloaded successfully:\n{output_path}")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Download Failed", str(e))

    def run(self):
        self.root.mainloop()