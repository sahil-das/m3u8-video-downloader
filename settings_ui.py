import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from settings import load_settings, save_settings

def build_settings_tab(notebook, on_settings_updated=None):
    config = load_settings()

    tab_frame = notebook.add("⚙️ Settings")
    content = ctk.CTkFrame(tab_frame)
    content.pack(padx=30, pady=30, fill="both", expand=True)

    # Title
    ctk.CTkLabel(content, text="⚙️ Application Settings", font=ctk.CTkFont(size=20, weight="bold"))\
        .grid(row=0, column=0, columnspan=3, pady=(0, 20))

    # Download Folder
    ctk.CTkLabel(content, text="Download Folder:").grid(row=1, column=0, sticky="w", padx=5, pady=10)
    output_entry = ctk.CTkEntry(content, width=300, placeholder_text="Select download folder")
    output_entry.grid(row=1, column=1, padx=5, pady=10)
    output_entry.insert(0, config.get("output_dir", ""))

    def browse_folder():
        folder = filedialog.askdirectory()
        if folder:
            output_entry.delete(0, ctk.END)
            output_entry.insert(0, folder)

    ctk.CTkButton(content, text="📂 Browse", command=browse_folder).grid(row=1, column=2, padx=5, pady=10)

    # Threads per Download with validation
    ctk.CTkLabel(content, text="Threads per Download:").grid(row=2, column=0, sticky="w", padx=5, pady=10)
    VALID_THREADS = ["1", "2", "4", "8", "16", "32"]
    conn_value = str(config.get("num_connections", 8))
    if conn_value not in VALID_THREADS:
        conn_value = "8"
    conn_var = ctk.StringVar(value=conn_value)
    conn_menu = ctk.CTkOptionMenu(content, variable=conn_var, values=VALID_THREADS)
    conn_menu.grid(row=2, column=1, columnspan=2, padx=5, pady=10, sticky="w")

    # Max Parallel Downloads with validation
    ctk.CTkLabel(content, text="Max Parallel Downloads:").grid(row=3, column=0, sticky="w", padx=5, pady=10)
    MAX_PARALLEL_RANGE = [str(i) for i in range(1, 11)]
    max_value = str(config.get("max_parallel", 3))
    if max_value not in MAX_PARALLEL_RANGE:
        max_value = "3"
    max_var = ctk.StringVar(value=max_value)
    max_menu = ctk.CTkOptionMenu(content, variable=max_var, values=MAX_PARALLEL_RANGE)
    max_menu.grid(row=3, column=1, columnspan=2, padx=5, pady=10, sticky="w")

    # FFmpeg Path
    ctk.CTkLabel(content, text="FFmpeg Path:").grid(row=4, column=0, sticky="w", padx=5, pady=10)
    ffmpeg_var = ctk.StringVar(value=config.get("ffmpeg_path", "ffmpeg"))
    ffmpeg_entry = ctk.CTkEntry(content, textvariable=ffmpeg_var, width=300)
    ffmpeg_entry.grid(row=4, column=1, columnspan=2, padx=5, pady=10, sticky="w")

    # Theme
    ctk.CTkLabel(content, text="Theme:").grid(row=5, column=0, sticky="w", padx=5, pady=10)
    theme_var = ctk.StringVar(value=config.get("theme", "dark"))
    theme_menu = ctk.CTkOptionMenu(content, variable=theme_var, values=["light", "dark", "system"])
    theme_menu.grid(row=5, column=1, columnspan=2, padx=5, pady=10, sticky="w")

    # Notifications
    notify_var = ctk.BooleanVar(value=config.get("enable_notifications", True))
    notify_check = ctk.CTkCheckBox(content, text="Enable Download Notifications", variable=notify_var)
    notify_check.grid(row=6, column=0, columnspan=3, sticky="w", padx=5, pady=10)

    # Save Button
    def save():
        try:
            output_path = output_entry.get().strip()

            # Validate download folder
            if (
                not output_path
                or output_path.isspace()
                or not os.path.exists(output_path)
                or not os.path.isdir(output_path)
                or not os.access(output_path, os.W_OK)
            ):
                messagebox.showerror(
                    "Invalid Folder",
                    f"The folder:\n\n{output_path}\n\nis invalid, does not exist, or is not writable.\nPlease select a valid folder."
                )
                return

            # Validate thread count and max parallel before saving
            threads = int(conn_var.get())
            if threads not in [1, 2, 4, 8, 16, 32]:
                messagebox.showerror("Invalid Value", "Threads per Download must be one of 1, 2, 4, 8, 16, 32.")
                return

            max_parallel = int(max_var.get())
            if not (1 <= max_parallel <= 10):
                messagebox.showerror("Invalid Value", "Max Parallel Downloads must be between 1 and 10.")
                return

            new_cfg = {
                "output_dir": output_path,
                "num_connections": threads,
                "max_parallel": max_parallel,
                "ffmpeg_path": ffmpeg_var.get().strip(),
                "theme": theme_var.get(),
                "enable_notifications": notify_var.get()
            }

            save_settings(new_cfg)

            # Apply theme immediately
            ctk.set_appearance_mode(new_cfg["theme"])

            if on_settings_updated:
                on_settings_updated()

            messagebox.showinfo("Settings", "Settings saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings:\n{e}")

    ctk.CTkButton(content, text="💾 Save Settings", command=save).grid(row=7, column=0, columnspan=3, pady=(30, 10))

    content.grid_columnconfigure(0, weight=1)
    content.grid_columnconfigure(1, weight=1)
    content.grid_columnconfigure(2, weight=1)
