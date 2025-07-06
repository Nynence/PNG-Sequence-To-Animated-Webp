import os
import subprocess
import threading
import tkinter as tk
import ctypes
from tkinter import filedialog, messagebox, ttk
import time
import signal

IMG2WEBP_PATH = os.path.join(os.path.dirname(__file__), "img2webp.exe")

class WebPConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PNG to Animated WebP Converter")
        self.root.geometry("700x400")
        self.root.configure(bg="#1e1e1e")

        self.center_frame = ttk.Frame(self.root, style="TFrame")
        self.center_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

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

        self.stop_conversion = False
        self.thread = None
        self.process = None

        self.create_path_input_row("Select PNG Folder:", 0, self.browse_folder, is_output=False)
        self.create_path_input_row("Output File:", 1, self.browse_output, is_output=True)

        self.center_frame.grid_rowconfigure(2, minsize=20)

        fps_loop_frame = ttk.Frame(self.center_frame, style="TFrame")
        fps_loop_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(20, 20))
        fps_loop_frame.columnconfigure(1, weight=1)
        fps_loop_frame.columnconfigure(3, weight=5)

        ttk.Label(fps_loop_frame, text="FPS:").grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.fps_spinbox = ttk.Spinbox(fps_loop_frame, from_=1, to=60, width=5, justify="center")
        self.fps_spinbox.set("25")
        self.fps_spinbox.grid(row=0, column=1, padx=(0, 20), sticky="w")

        ttk.Label(fps_loop_frame, text="Loop Animation:").grid(row=0, column=2, padx=(0, 5), sticky="w")
        self.loop_var = tk.IntVar(value=1)
        self.loop_check = ttk.Checkbutton(fps_loop_frame, variable=self.loop_var)
        self.loop_check.grid(row=0, column=3, sticky="w")

        quality_frame = ttk.Frame(self.center_frame, style="TFrame")
        quality_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 20))
        quality_frame.columnconfigure(1, weight=1)

        self.quality_value = tk.IntVar(value=100)

        ttk.Label(quality_frame, text="Quality (0=low, 100=lossless):").grid(row=0, column=0, sticky="w")
        self.quality_slider = ttk.Scale(
            quality_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=400,
            command=lambda val: self.update_quality_entry(val)
        )        
        self.quality_slider.set(self.quality_value.get())
        self.quality_slider.grid(row=0, column=1, sticky="ew", padx=10)

        self.quality_entry = ttk.Entry(quality_frame, textvariable=self.quality_value, width=5)
        self.quality_entry.grid(row=0, column=2)
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
                # Footer Label at bottom center
        footer_label = ttk.Label(
            self.root,
            text="Created by Rishab Kiran",
            background="#1e1e1e",
            foreground="#888888",
            font=("Helvetica", 9),
        
        )
        footer_label.place(relx=0.5, rely=1.0, anchor="s", y=-5)


    def create_path_input_row(self, label_text, row, browse_command, is_output=False):
        ttk.Label(self.center_frame, text=label_text).grid(row=row*2, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 0))
        entry = ttk.Entry(self.center_frame)
        entry.grid(row=row*2+1, column=0, sticky="ew", padx=(10, 5), pady=(5, 10))
        button = ttk.Button(self.center_frame, text="Browse", command=browse_command)
        button.grid(row=row*2+1, column=1, sticky="w", padx=(5, 10), pady=(5, 10))

        self.center_frame.grid_columnconfigure(0, weight=1)
        self.center_frame.grid_columnconfigure(1, weight=0)

        if is_output:
            self.output_entry = entry
        else:
            self.folder_entry = entry

    def update_quality_entry(self, val):
        self.quality_value.set(int(float(val)))

    def update_quality_slider(self, event):
        try:
            val = int(self.quality_entry.get())
            if 0 <= val <= 100:
                self.quality_slider.set(val)
        except ValueError:
            pass

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder_selected)

            folder_name = os.path.basename(folder_selected.rstrip("/\\"))
            parent_folder = os.path.dirname(folder_selected.rstrip("/\\"))

            default_output = os.path.join(parent_folder, f"{folder_name}.webp")

            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, default_output)


    def browse_output(self):
        input_folder = self.folder_entry.get().strip()
        
        if input_folder and os.path.isdir(input_folder):
            folder_name = os.path.basename(input_folder.rstrip("/\\"))
            parent_folder = os.path.dirname(input_folder.rstrip("/\\"))
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
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, file)


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
        folder_path = self.folder_entry.get()
        output_path = self.output_entry.get()
        fps_str = self.fps_spinbox.get()
        loop = self.loop_var.get()
        quality = int(round(self.quality_slider.get()))  # Force integer value (0-100)

        if not os.path.isfile(IMG2WEBP_PATH):
            self.show_error(f"img2webp.exe not found:\n{IMG2WEBP_PATH}")
            return self.finish_conversion()

        if not os.path.isdir(folder_path):
            self.show_error("Invalid folder path")
            return self.finish_conversion()

        if not output_path:
            self.show_error("Please specify an output file.")
            return self.finish_conversion()

        try:
            fps = int(fps_str)
            if fps <= 0:
                raise ValueError
        except ValueError:
            self.show_error("FPS must be a positive integer")
            return self.finish_conversion()

        png_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(".png")])
        if not png_files:
            self.show_error("No PNG files found in the folder")
            return self.finish_conversion()

        delay = int(1000 / fps)
        old_cwd = os.getcwd()

        self.process_done = False  # Add before starting process


        try:
            os.chdir(folder_path)
            command = [IMG2WEBP_PATH]
            if quality == 100:
                command += ["-lossless", "-q", "100"]
            else:
                command += ["-lossy", "-q", str(quality)]

            for f in png_files:
                command += ["-d", str(delay), f]

            command += ["-loop", "0" if loop else "1"]

                # optionally add method parameter, e.g.:
                # command += ["-m", "4"]  # default method


            command += ["-o", output_path]
            progress_thread = threading.Thread(target=self.fake_progress)
            progress_thread.start()

            self.process = subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW)
            while self.process.poll() is None:
                if self.stop_conversion:
                    self.status_label.config(text="Cancelled")
                    return self.finish_conversion()
                time.sleep(0.1)

            self.process_done = True  # signal progress thread to stop

            if self.process.returncode == 0 and not self.stop_conversion:
                self.status_label.config(text=f"Saved to: {os.path.basename(output_path)}")
                messagebox.showinfo("Success", f"Animated WebP saved as:\n{output_path}")
            elif not self.stop_conversion:
                self.show_error("Conversion failed.")

        finally:
            os.chdir(old_cwd)
            self.finish_conversion()


    def fake_progress(self):
        progress = 0
        while not self.stop_conversion and not getattr(self, 'process_done', False):
            if progress < 99:
                progress += 0.5  # faster progress increment
                self.progress["value"] = progress
                self.status_label.config(text="Converting...")
                self.root.update_idletasks()
                time.sleep(0.05)
            else:
                time.sleep(0.05)

        # When real process is done or cancelled, immediately set progress to 100 or 0
        if self.stop_conversion:
            self.progress["value"] = 0
            self.status_label.config(text="Cancelled")
        else:
            self.progress["value"] = 100
            self.status_label.config(text="Done")
        self.root.update_idletasks()

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

myappid = 'ADGroup.RishWebpify.Converter.1'  # Choose a unique ID
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

if __name__ == "__main__":
    root = tk.Tk()
    import os, sys

    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    icon_path = os.path.join(base_path, "app_icon.ico")
    root.iconbitmap(icon_path)

    app = WebPConverterApp(root)
    root.mainloop()
