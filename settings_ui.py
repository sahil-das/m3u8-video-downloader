import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from settings import load_settings, save_settings

def build_settings_tab(notebook, on_settings_updated=None):
    config = load_settings()

    tab_frame = notebook.add("⚙️ Settings")
    content = ctk.CTkFrame(tab_frame)
    content.pack(padx=30, pady=30, fill="both", expand=True)

    ctk.CTkLabel(content, text="⚙️ Application Settings", font=ctk.CTkFont(size=20, weight="bold"))\
        .grid(row=0, column=0, columnspan=3, pady=(0, 20))

    # === Download Folder ===
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

    # === Threads per Download ===
    ctk.CTkLabel(content, text="Threads per Download:").grid(row=2, column=0, sticky="w", padx=5, pady=10)
    conn_var = ctk.IntVar(value=config.get("num_connections", 8))
    if str(conn_var.get()) not in ["1", "2", "4", "8", "16", "32"]:
        conn_var.set(8)
    conn_menu = ctk.CTkOptionMenu(content, variable=conn_var, values=["1", "2", "4", "8", "16", "32"])
    conn_menu.grid(row=2, column=1, columnspan=2, padx=5, pady=10, sticky="w")

    # === Max Parallel Downloads ===
    ctk.CTkLabel(content, text="Max Parallel Downloads:").grid(row=3, column=0, sticky="w", padx=5, pady=10)
    max_var = ctk.IntVar(value=config.get("max_parallel", 3))
    max_menu = ctk.CTkOptionMenu(content, variable=max_var, values=[str(i) for i in range(1, 11)])
    max_menu.grid(row=3, column=1, columnspan=2, padx=5, pady=10, sticky="w")

    # === FFmpeg Path ===
    ctk.CTkLabel(content, text="FFmpeg Path:").grid(row=4, column=0, sticky="w", padx=5, pady=10)
    ffmpeg_var = ctk.StringVar(value=config.get("ffmpeg_path", "ffmpeg"))
    ffmpeg_entry = ctk.CTkEntry(content, textvariable=ffmpeg_var, width=300)
    ffmpeg_entry.grid(row=4, column=1, columnspan=2, padx=5, pady=10, sticky="w")

    # === Theme ===
    ctk.CTkLabel(content, text="Theme:").grid(row=5, column=0, sticky="w", padx=5, pady=10)
    theme_var = ctk.StringVar(value=config.get("theme", "dark"))
    theme_menu = ctk.CTkOptionMenu(content, variable=theme_var, values=["light", "dark", "system"])
    theme_menu.grid(row=5, column=1, columnspan=2, padx=5, pady=10, sticky="w")

    # === Notification Toggle ===
    notify_var = ctk.BooleanVar(value=config.get("enable_notifications", True))
    notify_check = ctk.CTkCheckBox(content, text="Enable Download Notifications", variable=notify_var)
    notify_check.grid(row=6, column=0, columnspan=3, sticky="w", padx=5, pady=10)

    # === Save Button ===
    def save():
        try:
            output_path = output_entry.get().strip()

            # === Strict folder validation ===
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

            new_cfg = {
                "output_dir": output_path,
                "num_connections": conn_var.get(),
                "max_parallel": max_var.get(),
                "ffmpeg_path": ffmpeg_var.get().strip(),
                "theme": theme_var.get(),
                "enable_notifications": notify_var.get()
            }
            save_settings(new_cfg)

            if on_settings_updated:
                on_settings_updated()

            ctk.set_appearance_mode(new_cfg["theme"])
            messagebox.showinfo("Settings", "Settings saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings:\n{e}")

    ctk.CTkButton(content, text="💾 Save Settings", command=save).grid(row=7, column=0, columnspan=3, pady=(30, 10))

    content.grid_columnconfigure(0, weight=1)
    content.grid_columnconfigure(1, weight=1)
    content.grid_columnconfigure(2, weight=1)
