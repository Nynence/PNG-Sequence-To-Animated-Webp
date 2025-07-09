import os
import subprocess
import threading
import tkinter as tk
import ctypes
from tkinter import filedialog, messagebox, ttk
import time
import concurrent.futures

myappid = 'ADGroup.RishWebpify.Converter.1'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# --- TRY TO IMPORT tkinterdnd2 for drag and drop
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

IMG2WEBP_PATH = os.path.join(os.path.dirname(__file__), "img2webp.exe")

class FolderDropFrame(ttk.Frame):
    """Responsive, scrollable drag-and-drop folders grid with canvas-drawn placeholder that never blocks drop.
       Each folder now includes a per-folder 'Loop' checkbox."""
    def __init__(self, parent, on_folders_changed, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_folders_changed = on_folders_changed
        self.folders = []
        self.bg_color = "#1e1e1e"
        self.folder_loops = {}  # New: Track per-folder loop

        # OUTER BOX
        self.box_frame = ttk.Frame(self, style="TEntry")
        self.box_frame.pack(fill="both", expand=True, padx=0, pady=(12, 0))
        self.box_frame.grid_propagate(False)

        # HEIGHT CONTROL (max 2.5 rows)
        cell_h = 65
        pad_hv = 18
        rows_visible = 2.5
        max_height = int(rows_visible * cell_h + (rows_visible - 1) * pad_hv)
        self.canvas_frame = tk.Frame(self.box_frame, bg=self.bg_color, height=max_height)
        self.canvas_frame.pack(fill="both", expand=False)
        self.canvas_frame.pack_propagate(False)

        # CANVAS & SCROLLBAR
        self.canvas = tk.Canvas(
            self.canvas_frame, bg=self.bg_color, highlightthickness=0, relief="flat"
        )
        self.canvas.pack(side="left", fill="both", expand=True, padx=(0, 20))

        style = ttk.Style()
        style.element_create("Custom.Vertical.Scrollbar.trough", "from", "clam")
        style.layout("Rish.Vertical.TScrollbar",
            [('Vertical.Scrollbar.trough',
                {'children': [('Vertical.Scrollbar.thumb', {'expand': '1', 'sticky': 'nswe'})],
                 'sticky': 'ns'})])
        style.configure("Rish.Vertical.TScrollbar",
            troughcolor="#1e1e1e", background="#222", bordercolor="#181818",
            lightcolor="#1e1e1e", darkcolor="#1e1e1e", arrowsize=10, gripcount=0, relief="flat",
            borderwidth=0)
        style.map("Rish.Vertical.TScrollbar",
            background=[('active', "#444444"), ('!active', "#222")],
            troughcolor=[('active', "#1e1e1e"), ('!active', "#1e1e1e")]
        )
        self.v_scroll = ttk.Scrollbar(
            self.canvas_frame, orient="vertical", command=self.canvas.yview,
            style="Rish.Vertical.TScrollbar"
        )
        self.canvas.configure(yscrollcommand=self.v_scroll.set)
        self.canvas_window = self.canvas.create_window((0, 0), window=tk.Frame(self.canvas, bg=self.bg_color), anchor="nw")
        self.items_frame = self.canvas.nametowidget(self.canvas.itemcget(self.canvas_window, "window"))
        self.items_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Drag & Drop events (canvas is target)
        if DND_AVAILABLE:
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind('<<Drop>>', self._on_drop)

        # Tooltip (truncated names)
        self.tooltip = tk.Toplevel(self)
        self.tooltip.withdraw()
        self.tooltip.overrideredirect(True)
        self.items_frame.bind_all("<Motion>", self._on_hover)
        self.hover_idx = None

        self._drawing = False
        self.draw_folders()

    def select_folders(self, event=None):
        folder = filedialog.askdirectory(mustexist=True, title="Select Folder", parent=self)
        if folder:
            self.add_folders([folder])

    def _on_drop(self, event):
        paths = self.winfo_toplevel().tk.splitlist(event.data)
        folders = [p for p in paths if os.path.isdir(p)]
        self.add_folders(folders)

    def add_folders(self, folders):
        for f in folders:
            if f not in self.folders and os.path.isdir(f):
                self.folders.append(f)
                self.folder_loops[f] = False  # Default: Loop enabled
        self.draw_folders()
        self.on_folders_changed(self.folders)

    def remove_folder(self, idx):
        folder = self.folders[idx]
        del self.folders[idx]
        if folder in self.folder_loops:
            del self.folder_loops[folder]
        self.draw_folders()
        self.on_folders_changed(self.folders)

    def clear(self):
        self.folders.clear()
        self.folder_loops.clear()
        self.draw_folders()
        self.on_folders_changed(self.folders)

    def draw_placeholder(self):
        self.canvas.delete("placeholder")
        self.canvas.update_idletasks()
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        text = "Drag & drop folders here\nor click 'Add Folder(s)'"
        self.canvas.create_text(
            w // 2, h // 2,
            text=text,
            font=("Helvetica", 13, "italic"),
            fill="#bbbbbb",
            tags="placeholder",
            justify="center"
        )

    def draw_folders(self):
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        self._drawing = True

        w = self.canvas.winfo_width() or 600
        cols = 2
        min_box_width = 250
        pad_hv = 18
        if w > 600:
            possible_cols = max(2, min(5, w // (min_box_width + pad_hv)))
            cols = possible_cols
        cell_w = (w - (cols - 1) * pad_hv) // cols if cols > 0 else min_box_width
        cell_h = 65

        self.canvas.delete("placeholder")
        if not self.folders:
            self.draw_placeholder()

        max_name_length = 22
        for idx, folder in enumerate(self.folders):
            row = idx // cols
            col = idx % cols
            cell = tk.Frame(
                self.items_frame,
                bg="#181818",
                height=cell_h,
                width=cell_w,
            )
            cell.grid(row=row, column=col, padx=(0 if col == 0 else pad_hv, 0), pady=(0 if row == 0 else pad_hv, 0), sticky="nsew")
            cell.grid_propagate(False)
            self.items_frame.grid_columnconfigure(col, weight=1)
            self.items_frame.grid_rowconfigure(row, weight=1)

            cell.grid_columnconfigure(0, minsize=38, weight=0)
            cell.grid_columnconfigure(1, weight=1, minsize=50)
            cell.grid_columnconfigure(2, minsize=40, weight=0)
            cell.grid_columnconfigure(3, minsize=10, weight=0)

            icon_label = tk.Label(cell, text="📁", bg="#181818", fg="#FDB43B",
                                font=("Segoe UI Emoji", 19), anchor="w")
            icon_label.grid(row=0, column=0, rowspan=2, padx=(14, 12), pady=(10, 10), sticky="nw")

            foldername = os.path.basename(folder)
            shown_name = (foldername[:max_name_length - 2] + "…") if len(foldername) > max_name_length else foldername
            name_label = tk.Label(
                cell, text=shown_name, bg="#181818", fg="#ffffff",
                font=("Helvetica", 12, "bold"), anchor="w"
            )
            name_label.grid(row=0, column=1, sticky="new", padx=(0,12), pady=(10,0))
            name_label.bind("<Enter>", lambda e, i=idx: self._show_tooltip(i, e))
            name_label.bind("<Leave>", lambda e: self._hide_tooltip())

            path_display = folder
            if len(path_display) > 44:
                path_display = path_display[:17] + "…" + path_display[-24:]
            path_label = tk.Label(
                cell, text=path_display, bg="#181818", fg="#cccccc",
                font=("Helvetica", 8), anchor="w"
            )
            path_label.grid(row=1, column=1, sticky="sw", padx=(0,12), pady=(0,16))
            path_label.bind("<Enter>", lambda e, i=idx: self._show_tooltip(i, e))
            path_label.bind("<Leave>", lambda e: self._hide_tooltip())

            # --- CLOSE BUTTON ---
            close_btn = tk.Label(cell, text="✕", fg="#d9534f", bg="#181818",
                                font=("Helvetica", 13, "bold"), cursor="hand2")
            # Reduce right padding
            close_btn.grid(row=0, column=2, sticky="ne", padx=(8,0), pady=(10,0))
            close_btn.bind("<Button-1>", lambda e, i=idx: self.remove_folder(i))

            # --- LOOP BUTTON ---
            # Create a unique BooleanVar for each folder (default unchecked)
            loop_var = tk.BooleanVar(value=self.folder_loops.get(folder, False))
            self.folder_loops[folder] = loop_var.get()

            def make_loop_toggle_handler(lvar, btn, fldr):
                def handler():
                    lvar.set(not lvar.get())
                    self.folder_loops[fldr] = lvar.get()
                    btn.config(
                        text="➰ Loop" if lvar.get() else "〰 Loop",
                        fg="#8b06c4" if lvar.get() else "#aaaaaa"
                    )
                return handler

            loop_btn = tk.Button(
                cell,
                text="➰ Loop" if loop_var.get() else "〰 Loop",
                bg="#181818",
                fg="#8b06c4" if loop_var.get() else "#aaaaaa",
                activebackground="#222",
                activeforeground="#8b06c4",
                font=("Helvetica", 10, "bold"),
                borderwidth=0,
                relief="flat",
                cursor="hand2",
                command=None  # Set below
            )
            # Reduce right padding on loop
            loop_btn.grid(row=1, column=2, sticky="ne", padx=(8,0), pady=(0,10))

            # Attach unique command handler after creation
            loop_btn.config(command=make_loop_toggle_handler(loop_var, loop_btn, folder))

        self._drawing = False
        self._update_scroll_region()

    def get_folder_loops(self):
        return {f: self.folder_loops.get(f, True) for f in self.folders}

    def _on_frame_configure(self, event):
        if not self._drawing:
            self._update_scroll_region()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        self._update_scroll_region()
        if not self.folders:
            self.draw_placeholder()

    def _update_scroll_region(self):
        self.items_frame.update_idletasks()
        bbox = self.items_frame.bbox()
        frame_height = self.items_frame.winfo_height()
        canvas_height = self.canvas.winfo_height()
        if bbox and frame_height > canvas_height:
            self.v_scroll.pack(side="right", fill="y", padx=(0, 0))
            self.canvas.configure(yscrollcommand=self.v_scroll.set)
        else:
            self.v_scroll.pack_forget()
            self.canvas.configure(yscrollcommand=lambda *args: None)
        self.canvas.config(scrollregion=(0, 0, bbox[2], bbox[3]) if bbox else (0, 0, 0, 0))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _show_tooltip(self, idx, event):
        folder = self.folders[idx]
        x = event.widget.winfo_rootx() + event.x + 18
        y = event.widget.winfo_rooty() + event.y + 12
        self.tooltip.geometry(f"+{x}+{y}")
        self.tooltip.deiconify()
        if hasattr(self, "_ttlabel"):
            self._ttlabel.destroy()
        self._ttlabel = tk.Label(self.tooltip, text=folder, background="#222", foreground="#fff", borderwidth=1, relief="solid", font=("Helvetica", 9))
        self._ttlabel.pack()
        self.hover_idx = idx

    def _hide_tooltip(self, event=None):
        self.tooltip.withdraw()
        if hasattr(self, "_ttlabel"):
            self._ttlabel.destroy()
        self.hover_idx = None

    def _on_hover(self, event):
        if self.hover_idx is not None:
            pass

class WebPConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PNG to Animated WebP Converter")
        self.root.geometry("700x500")
        self.root.configure(bg="#1e1e1e")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#1e1e1e", foreground="#ffffff", font=("Helvetica", 10))
        style.configure("TButton", background="#2a2a2a", foreground="#ffffff", font=("Helvetica", 10), padding=6, relief="flat")
        style.map("TButton", background=[("active", "#3c3c3c")])
        style.configure("TCheckbutton", background="#1e1e1e", foreground="#ffffff", font=("Helvetica", 10))
        style.configure("TEntry", fieldbackground="#2a2a2a", foreground="#ffffff", bordercolor="#2a2a2a", insertcolor="#ffffff", lightcolor="#2a2a2a",  relief="flat", padding=8, borderwidth=0)
        style.configure("TSpinbox", arrowsize=15, fieldbackground="#2a2a2a", foreground="#ffffff", bordercolor="#2a2a2a",  lightcolor="#2a2a2a", relief="flat")
        style.configure("Horizontal.TScale", background="#1e1e1e", troughcolor="#444444", bordercolor="#2a2a2a")
        style.configure("Horizontal.TProgressbar", background="#4caf50", troughcolor="#1e1e1e", bordercolor="#2a2a2a")
        style.configure("TFrame", background="#1e1e1e", bordercolor="#2a2a2a")
        style.configure("Drop.TFrame", background="#1e1e1e")

        self.stop_conversion = False
        self.thread = None
        self.process = None

        self.center_frame = ttk.Frame(self.root, style="TFrame")
        self.center_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        header_frame = ttk.Frame(self.center_frame, style="TFrame")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 0))
        header_frame.grid_columnconfigure(0, weight=1)
        ttk.Label(header_frame, text="Select PNG Folders:").grid(row=0, column=0, sticky="w")
        self.folder_add_btn = ttk.Button(header_frame, text="Add Folder(s)", command=lambda: self.folder_drop.select_folders())
        self.folder_add_btn.grid(row=0, column=1, sticky="e")

        self.folder_drop = FolderDropFrame(self.center_frame, on_folders_changed=self.on_folders_changed)
        self.folder_drop.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=(5, 10), columnspan=2)
        self.center_frame.grid_rowconfigure(1, minsize=170)
        self.center_frame.grid_columnconfigure(0, weight=1)
        self.center_frame.grid_columnconfigure(1, weight=0)

        self.output_entry = ttk.Entry(self.center_frame)
        self.output_entry.grid(row=3, column=0, sticky="ew", padx=(10, 5), pady=(5, 10))
        self.browse_output_btn = ttk.Button(self.center_frame, text="Browse Output", command=self.browse_output)
        self.browse_output_btn.grid(row=3, column=1, sticky="w", padx=(5, 10), pady=(5, 10))
        self.output_entry.insert(0, "")

        # --- FPS & Quality: now side by side in same row ---
        fps_quality_frame = ttk.Frame(self.center_frame, style="TFrame")
        fps_quality_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(20, 20))
        fps_quality_frame.columnconfigure(1, weight=1)
        fps_quality_frame.columnconfigure(3, weight=1)

        # FPS
        ttk.Label(fps_quality_frame, text="FPS:").grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.fps_spinbox = ttk.Spinbox(fps_quality_frame, from_=1, to=60, width=5, justify="center")
        self.fps_spinbox.set("25")
        self.fps_spinbox.grid(row=0, column=1, padx=(0, 24), sticky="w")

        # Quality
        ttk.Label(fps_quality_frame, text="Quality (0=low, 100=lossless):").grid(row=0, column=2, padx=(0,10), sticky="w")
        self.quality_value = tk.IntVar(value=100)
        self.quality_slider = ttk.Scale(
            fps_quality_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=220,
            command=lambda val: self.update_quality_entry(val)
        )
        self.quality_slider.set(self.quality_value.get())
        self.quality_slider.grid(row=0, column=3, sticky="ew", padx=(0,8))
        self.quality_entry = ttk.Entry(fps_quality_frame, textvariable=self.quality_value, width=5)
        self.quality_entry.grid(row=0, column=4)
        self.quality_entry.bind("<KeyRelease>", self.update_quality_slider)

        self.button_frame = ttk.Frame(self.center_frame, style="TFrame")
        self.button_frame.grid(row=6, column=0, columnspan=2, padx=5, pady=(1, 5), sticky="ew")
        self.button_frame.columnconfigure(0, weight=1)
        self.button_frame.columnconfigure(1, weight=1)
        self.button_frame.columnconfigure(2, weight=4)
        self.button_frame.rowconfigure(0, weight=1)
        self.convert_btn = ttk.Button(self.button_frame, text="Convert", command=self.start_conversion)
        self.convert_btn.grid(row=0, column=0, sticky="nsew", padx=5)
        self.cancel_btn = ttk.Button(self.button_frame, text="Cancel", command=self.cancel_conversion, state="disabled")
        self.cancel_btn.grid(row=0, column=1, sticky="nsew", padx=5)
        self.progress_container = ttk.Frame(self.button_frame, style="TFrame")
        self.progress_container.grid(row=0, column=2, sticky="nsew", padx=5)
        self.progress_container.grid_propagate(True)
        self.progress_container.columnconfigure(0, weight=1)
        self.progress_container.rowconfigure(0, weight=1)
        self.progress = ttk.Progressbar(
            self.progress_container,
            orient="horizontal",
            mode="determinate",
            style="Horizontal.TProgressbar"
        )
        self.progress.grid(row=0, column=0, sticky="nsew")
        self.status_label = ttk.Label(
            self.progress_container,
            text="Ready",
            background="",
            foreground="#ffffff",
            anchor="center"
        )
        self.status_label.place(relx=0.5, rely=0.5, anchor="center")
        # Footer
        footer_label = ttk.Label(
            self.root,
            text="Created by Rishab Kiran",
            background="#1e1e1e",
            foreground="#888888",
            font=("Helvetica", 9),   
        )
        footer_label.place(relx=0.5, rely=1.0, anchor="s", y=-5)

        self.on_folders_changed([])  # Set initial state

    def on_folders_changed(self, folders):
        if len(folders) == 1:
            folder = folders[0]
            folder_name = os.path.basename(folder.rstrip("/\\"))
            parent_folder = os.path.dirname(folder.rstrip("/\\"))
            default_output = os.path.join(parent_folder, f"{folder_name}.webp")
            self.output_entry.configure(state="normal")
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, default_output)
            self.browse_output_btn.config(text="Browse Output")
        elif len(folders) > 1:
            self.output_entry.configure(state="normal")
            self.output_entry.delete(0, tk.END)
            self.output_entry.configure(state="readonly")
            self.browse_output_btn.config(text="Browse Output Folder")
        else:
            self.output_entry.configure(state="normal")
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, "")
            self.browse_output_btn.config(text="Browse Output")

    def update_quality_entry(self, val):
        self.quality_value.set(int(float(val)))

    def update_quality_slider(self, event):
        try:
            val = int(self.quality_entry.get())
            if 0 <= val <= 100:
                self.quality_slider.set(val)
        except ValueError:
            pass

    def browse_output(self):
        folders = self.folder_drop.folders
        if len(folders) <= 1:
            folder = folders[0] if folders else ""
            if folder and os.path.isdir(folder):
                folder_name = os.path.basename(folder.rstrip("/\\"))
                parent_folder = os.path.dirname(folder.rstrip("/\\"))
                initialfile = f"{folder_name}.webp"
                initialdir = parent_folder
            else:
                initialfile = "output.webp"
                initialdir = os.getcwd()
            file = filedialog.asksaveasfilename(
                defaultextension=".webp",
                filetypes=[("WebP files", "*.webp")],
                initialfile=initialfile,
                initialdir=initialdir
            )
            if file:
                self.output_entry.configure(state="normal")
                self.output_entry.delete(0, tk.END)
                self.output_entry.insert(0, file)
        else:
            folder = filedialog.askdirectory(title="Select Output Folder")
            if folder:
                self.output_entry.configure(state="normal")
                self.output_entry.delete(0, tk.END)
                self.output_entry.insert(0, folder)
                self.output_entry.configure(state="readonly")

    def start_conversion(self):
        if self.thread and self.thread.is_alive():
            messagebox.showinfo("Info", "Conversion is already running.")
            return
        self.stop_conversion = False
        self.process = None
        self.convert_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.status_label.config(text="Starting...")
        self.progress["value"] = 0
        self.thread = threading.Thread(target=self.convert_to_webp)
        self.thread.start()

    def cancel_conversion(self):
        self.stop_conversion = True
        self.status_label.config(text="Cancelling...")
        if self.process:
            try:
                self.process.terminate()
            except Exception as e:
                print(f"Failed to terminate process: {e}")

    def convert_to_webp(self):
        folders = self.folder_drop.folders
        output_path = self.output_entry.get().strip()
        fps_str = self.fps_spinbox.get()
        quality = int(round(self.quality_slider.get()))
        folder_loops = self.folder_drop.get_folder_loops()

        if not os.path.isfile(IMG2WEBP_PATH):
            self.show_error(f"img2webp.exe not found:\n{IMG2WEBP_PATH}")
            return self.finish_conversion()

        try:
            fps = int(fps_str)
            if fps <= 0:
                raise ValueError
        except ValueError:
            self.show_error("FPS must be a positive integer")
            return self.finish_conversion()

        if not folders:
            self.show_error("Please select at least one folder.")
            return self.finish_conversion()

        if len(folders) > 1:
            if not output_path or not os.path.isdir(output_path):
                self.show_error("Please select an output folder for multi-folder mode.")
                return self.finish_conversion()
            total = len(folders)
            completed = [0]
            failures = []

            self.start_smooth_progress(total)
            self.status_label.config(text=f"Converting (0/{total})")
            self.progress["value"] = 1

            def process_folder(idx, folder_path):
                print(f"STARTING: (idx={idx})")
                if self.stop_conversion:
                    return (idx, folder_path, False)
                png_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(".png")])
                if not png_files:
                    print(f"NO PNGs: {os.path.basename(folder_path)}")
                    return (idx, folder_path, "no_pngs")
                delay = int(1000 / fps)
                folder_name = os.path.basename(folder_path.rstrip("/\\"))
                output_file = os.path.join(output_path, f"{folder_name}.webp")
                loop = folder_loops.get(folder_path, True)
                success = self.run_img2webp(folder_path, png_files, delay, quality, loop, output_file)
                print(f"FINISHED: (idx={idx}, Success={success})")
                return (idx, folder_path, success)

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = []
                for idx, folder_path in enumerate(folders):
                    futures.append(executor.submit(process_folder, idx, folder_path))
                results = []
                for fut in concurrent.futures.as_completed(futures):
                    idx, folder_path, result = fut.result()
                    completed[0] += 1
                    self.update_progress_target(completed[0])
                    self.status_label.config(text=f"Converting ({completed[0]}/{total})")
                    if result == "no_pngs":
                        failures.append(f"({idx+1}) No PNGs")
                    elif not result:
                        failures.append(f"({idx+1}) Failed")
                    self.root.update_idletasks()
                    results.append((idx, folder_path, result))

            self._target_progress = 100
            self._current_progress = 100
            self.progress["value"] = 100
            self._smooth_progress_running = False
            self.status_label.config(text=f"Done ({total})")
            if not self.stop_conversion:
                if failures:
                    messagebox.showwarning("Some folders failed",
                        f"Some folders failed to convert:\n" + "\n".join(failures))
                else:
                    messagebox.showinfo("Success", f"Converted {total} folders to WebP!\nSaved in: {output_path}")

        else:
            folder_path = folders[0]
            png_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(".png")])
            if not png_files:
                self.show_error("No PNG files found in the folder")
                return self.finish_conversion()
            delay = int(1000 / fps)
            if not output_path:
                self.show_error("Please specify an output file.")
                return self.finish_conversion()
            loop = folder_loops.get(folder_path, True)
            self.status_label.config(text="Converting (1/1)")
            self.progress["value"] = 1
            self.root.update_idletasks()
            success = self.run_img2webp(folder_path, png_files, delay, quality, loop, output_path)
            if success:
                self.progress["value"] = 100
                self.status_label.config(text="Done (1)")
                messagebox.showinfo("Success", f"Animated WebP saved as:\n{output_path}")
            else:
                self.show_error("Conversion failed.")
        self.finish_conversion()

    def run_img2webp(self, folder_path, png_files, delay, quality, loop, output_file):
        # Always overwrite any old file
        if os.path.isfile(output_file):
            try:
                os.remove(output_file)
            except Exception:
                pass
        command = [IMG2WEBP_PATH]
        if quality == 100:
            command += ["-lossless", "-q", "100"]
        else:
            command += ["-lossy", "-q", str(quality)]
        for f in png_files:
            command += ["-d", str(delay), f]
        command += ["-loop", "0" if loop else "1"]
        command += ["-o", output_file]

        try:
            process = subprocess.Popen(command, cwd=folder_path, creationflags=subprocess.CREATE_NO_WINDOW)
            while process.poll() is None:
                if self.stop_conversion:
                    process.terminate()
                    return False
                time.sleep(0.1)
            return process.returncode == 0 and not self.stop_conversion
        except Exception as e:
            print("run_img2webp error:", e)
            return False

    def start_smooth_progress(self, total_folders):
        self._target_progress = 0
        self._current_progress = 0
        self._total_folders = total_folders
        self._done_folders = 0
        self._smooth_progress_running = True
        self._smooth_progress_update()

    def update_progress_target(self, done_folders):
        self._done_folders = done_folders
        self._target_progress = int((done_folders / self._total_folders) * 100)

    def _smooth_progress_update(self):
        if not getattr(self, "_smooth_progress_running", False):
            return
        if self._current_progress < self._target_progress:
            self._current_progress += min(1, self._target_progress - self._current_progress)
            self.progress["value"] = self._current_progress
        if self._current_progress < 100:
            self.root.after(20, self._smooth_progress_update)
        else:
            self._smooth_progress_running = False

    def show_error(self, msg):
        messagebox.showerror("Error", msg)
        self.status_label.config(text="Error")

    def finish_conversion(self):
        self.convert_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.progress["value"] = 100 if not self.stop_conversion else 0
        if not self.stop_conversion:
            self.status_label.config(text="Done")
        else:
            self.status_label.config(text="Cancelled")

def create_root_window():
    if DND_AVAILABLE:
        return TkinterDnD.Tk()
    else:
        return tk.Tk()


if __name__ == "__main__":
    root = create_root_window()
    root.withdraw()   # Hide window immediately

    import os, sys
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_path, "app_icon.ico")
    try:
        root.iconbitmap(icon_path)
    except Exception:
        pass

    app = WebPConverterApp(root)
    root.deiconify()  # Show window only after fully configured
    root.mainloop()


