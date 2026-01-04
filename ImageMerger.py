import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import os
import subprocess
from datetime import datetime
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk
import math
import threading
import tempfile

class ImageMagickMerger:
    def __init__(self, root):
        self.root = root
        self.root.title("ImageMagick ImageMerger")
        self.root.geometry("900x650")
        self.root.configure(bg="#f5f5f5")
        ttk.Style().theme_use('xpnative')
        
        self.image_paths = []
        self.preview_timer = None
        self.preview_thread = None
        self.preview_cancel = False
        
        self.vars = {
            'mode': tk.StringVar(value="horizontal"), 'format': tk.StringVar(value="jpg"),
            'quality': tk.IntVar(value=94), 'spacing': tk.IntVar(value=0),
            'grid_cols': tk.IntVar(value=0), 'grid_fit': tk.StringVar(value="crop"),
            'use_smallest': tk.BooleanVar(value=False), 'canvas_w': tk.IntVar(value=0),
            'canvas_h': tk.IntVar(value=0), 'border': tk.IntVar(value=0),
            'best_fit': tk.BooleanVar(value=False), 'show_labels': tk.BooleanVar(value=False),
            'normalize_size': tk.BooleanVar(value=False), 'target_size': tk.IntVar(value=800),
            'match_size': tk.BooleanVar(value=False), 'match_smallest': tk.BooleanVar(value=True)
        }
        self.setup_ui()

    def setup_ui(self):
        left = ttk.Frame(self.root, padding=15)
        left.pack(side=tk.LEFT, fill='both', expand=False)
        right = ttk.Frame(self.root, padding=15)
        right.pack(side=tk.RIGHT, fill='both', expand=True)

        # Drop area
        self.drop_area = tk.Label(left, text="Drop images here\n(JPG, PNG, GIF, WEBP, etc.)", 
                                  bg='#e6e6e6', font=('Arial Nova', 12), bd=2, relief='groove', height=6, width=40)
        self.drop_area.pack(fill='x', pady=10)
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind('<<Drop>>', self.handle_drop)

        # Status
        status_frame = ttk.Frame(left)
        status_frame.pack(fill='x', pady=5)
        self.status_label = tk.Label(status_frame, text="Waiting for images...", 
                                     font=('Arial Nova', 10), bg="#f5f5f5", fg="#555555")
        self.status_label.pack(side=tk.LEFT)
        ttk.Button(status_frame, text="Browse", command=self.browse_files).pack(side=tk.RIGHT)

        # Options
        opts = ttk.LabelFrame(left, text="Options", padding=10)
        opts.pack(fill='x', pady=10)

        # Mode
        self.add_radio(opts, "Layout:", 'mode', 
                      [("Horizontal", "horizontal"), ("Vertical", "vertical"), ("Grid", "grid"), ("Ashlar", "ashlar")])

        # H/V options
        self.hvmode_frame = ttk.LabelFrame(opts, text="Horizontal/Vertical", padding=5)
        ttk.Checkbutton(self.hvmode_frame, text="Match image sizes", 
                       variable=self.vars['match_size'], command=self.on_change).pack(fill='x', pady=2)
        self.add_radio(self.hvmode_frame, "Match to:", 'match_smallest', [("Smallest", True), ("Largest", False)])

        # Grid options
        self.grid_frame = ttk.LabelFrame(opts, text="Grid", padding=5)
        self.add_entry(self.grid_frame, "Columns (0=auto):", 'grid_cols', 5)
        self.add_radio(self.grid_frame, "Fit:", 'grid_fit', 
                      [("Crop", "crop"), ("Scale", "scale"), ("Original", "original")])
        ttk.Checkbutton(self.grid_frame, text="Use smallest dimensions", 
                       variable=self.vars['use_smallest'], command=self.on_change).pack(fill='x', pady=2)

        # Ashlar options
        self.ashlar_frame = ttk.LabelFrame(opts, text="Ashlar", padding=5)
        canvas_row = ttk.Frame(self.ashlar_frame)
        canvas_row.pack(fill='x', pady=2)
        ttk.Label(canvas_row, text="Canvas (0=auto):").pack(side=tk.LEFT, padx=(0,10))
        ttk.Entry(canvas_row, textvariable=self.vars['canvas_w'], width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(canvas_row, text="×").pack(side=tk.LEFT, padx=2)
        ttk.Entry(canvas_row, textvariable=self.vars['canvas_h'], width=6).pack(side=tk.LEFT, padx=2)
        self.add_scale(self.ashlar_frame, "Border:", 'border', 0, 20, "px")
        norm_row = ttk.Frame(self.ashlar_frame)
        norm_row.pack(fill='x', pady=2)
        ttk.Checkbutton(norm_row, text="Normalize to:", variable=self.vars['normalize_size'], 
                       command=self.on_change).pack(side=tk.LEFT)
        ttk.Entry(norm_row, textvariable=self.vars['target_size'], width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(norm_row, text="px").pack(side=tk.LEFT)
        cb_row = ttk.Frame(self.ashlar_frame)
        cb_row.pack(fill='x', pady=2)
        for text, var in [("Best Fit", 'best_fit'), ("Labels", 'show_labels')]:
            ttk.Checkbutton(cb_row, text=text, variable=self.vars[var], 
                           command=self.on_change).pack(side=tk.LEFT, padx=5)

        # Common options
        self.add_scale(opts, "Spacing:", 'spacing', 0, 20, "px")
        
        fmt_row = ttk.Frame(opts)
        fmt_row.pack(fill='x', pady=2)
        ttk.Label(fmt_row, text="Format:").pack(side=tk.LEFT, padx=(0,5))
        fmt = ttk.Combobox(fmt_row, textvariable=self.vars['format'], 
                          values=["jpg","png","webp","gif"], width=8, state="readonly")
        fmt.pack(side=tk.LEFT, padx=(0,20))
        fmt.bind('<<ComboboxSelected>>', lambda e: self.on_change())
        ttk.Label(fmt_row, text="Quality:").pack(side=tk.LEFT, padx=(0,5))
        quality_scale = ttk.Scale(fmt_row, from_=50, to=100, variable=self.vars['quality'], 
                 command=lambda v: self.on_change())
        quality_scale.pack(side=tk.LEFT, expand=True, fill='x', padx=(0,10))
        self.quality_label = ttk.Label(fmt_row, text="94%")
        self.quality_label.pack(side=tk.LEFT)
        self.vars['quality'].trace('w', lambda *_: self.quality_label.config(text=f"{self.vars['quality'].get()}%"))
        for event in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            quality_scale.bind(event, lambda e: self.wheel_scale(e, 'quality', 50, 100))

        # Buttons
        btn_frame = ttk.Frame(left)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Clear", command=self.clear_images).pack(side=tk.LEFT, padx=5)
        self.merge_btn = ttk.Button(btn_frame, text="Merge Images", 
                                    command=self.merge_images, state=tk.DISABLED)
        self.merge_btn.pack(side=tk.LEFT, padx=5)

        # Preview
        preview_frame = ttk.LabelFrame(right, text="Preview", padding=10)
        preview_frame.pack(expand=True, fill='both')
        self.preview_canvas = tk.Canvas(preview_frame, bg='#2a2a2a', highlightthickness=0)
        self.preview_canvas.pack(expand=True, fill='both')
        self.preview_status = tk.Label(preview_frame, text="Add images to see preview", 
                                       font=('Arial Nova', 10), bg="#f5f5f5", fg="#888888")
        self.preview_status.pack(pady=5)
        self.toggle_mode_options()

    def add_radio(self, parent, label, var_name, options):
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=2)
        ttk.Label(row, text=label).pack(side=tk.LEFT, padx=(0,10))
        for text, value in options:
            ttk.Radiobutton(row, text=text, variable=self.vars[var_name], 
                          value=value, command=self.on_change).pack(side=tk.LEFT, padx=5)

    def add_entry(self, parent, label, var_name, width):
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=2)
        ttk.Label(row, text=label).pack(side=tk.LEFT, padx=(0,10))
        ttk.Entry(row, textvariable=self.vars[var_name], width=width).pack(side=tk.LEFT)

    def add_scale(self, parent, label, var_name, from_, to, unit):
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=2)
        ttk.Label(row, text=label).pack(side=tk.LEFT, padx=(0,10))
        scale = ttk.Scale(row, from_=from_, to=to, variable=self.vars[var_name], 
                         command=lambda v: self.on_change())
        scale.pack(side=tk.LEFT, expand=True, fill='x', padx=(0,10))
        lbl = ttk.Label(row, text=f"{self.vars[var_name].get()}{unit}")
        lbl.pack(side=tk.LEFT)
        self.vars[var_name].trace('w', lambda *_: lbl.config(text=f"{self.vars[var_name].get()}{unit}"))
        for event in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            scale.bind(event, lambda e, v=var_name, f=from_, t=to: self.wheel_scale(e, v, f, t))

    def wheel_scale(self, event, var_name, from_, to):
        delta = 1 if event.delta > 0 else -1
        self.vars[var_name].set(max(from_, min(to, self.vars[var_name].get() + delta)))
        self.on_change()

    def toggle_mode_options(self):
        for f in (self.grid_frame, self.ashlar_frame, self.hvmode_frame):
            f.pack_forget()
        mode = self.vars['mode'].get()
        if mode == "grid":
            self.grid_frame.pack(fill='x', pady=5)
        elif mode == "ashlar":
            self.ashlar_frame.pack(fill='x', pady=5)
        elif mode in ["horizontal", "vertical"]:
            self.hvmode_frame.pack(fill='x', pady=5)

    def on_change(self):
        self.toggle_mode_options()
        if self.preview_timer:
            self.root.after_cancel(self.preview_timer)
        if len(self.image_paths) >= 2:
            self.preview_status.config(text="Preview updating...")
            self.preview_timer = self.root.after(300, self.generate_preview)

    def browse_files(self):
        paths = filedialog.askopenfilenames(title="Select Images", 
                filetypes=(("Images", "*.jpg *.jpeg *.png *.gif *.webp *.bmp *.tiff"), ("All", "*.*")))
        if paths:
            self.image_paths.extend(paths)
            self.update_status()
            self.on_change()

    def handle_drop(self, event):
        # Handle different path formats from drag-and-drop
        data = event.data
        if not data:
            return
        
        # Handle curly brace wrapped paths (Windows with spaces)
        if data.startswith('{'):
            paths = [p.strip('{}').strip() for p in data.split('} {')]
        else:
            # Split by whitespace, but handle quoted paths
            paths = []
            current = ""
            in_quotes = False
            for char in data:
                if char == '"':
                    in_quotes = not in_quotes
                elif char in (' ', '\n', '\r', '\t') and not in_quotes:
                    if current:
                        paths.append(current)
                        current = ""
                else:
                    current += char
            if current:
                paths.append(current)
        
        # Clean and validate paths
        valid_paths = []
        for path in paths:
            path = path.strip().strip('"').strip("'")
            if path and os.path.isfile(path):
                valid_paths.append(path)
        
        if valid_paths:
            self.image_paths.extend(valid_paths)
            self.update_status()
            self.on_change()
        else:
            messagebox.showwarning("Warning", "No valid image files found in drop")

    def update_status(self):
        count = len(self.image_paths)
        self.status_label.config(text=f"{count} images loaded")
        self.merge_btn['state'] = tk.NORMAL if count >= 2 else tk.DISABLED

    def clear_images(self):
        self.image_paths = []
        self.status_label.config(text="Waiting for images...")
        self.merge_btn['state'] = tk.DISABLED
        self.preview_canvas.delete('all')
        self.preview_status.config(text="Add images to see preview")
        if self.preview_timer:
            self.root.after_cancel(self.preview_timer)

    def get_dimensions(self):
        dims = []
        for path in self.image_paths:
            try:
                with Image.open(path) as img:
                    dims.append(img.size)
            except:
                dims.append((0, 0))
        return dims

    def build_command(self, output_path, preview=False):
        paths = [p.replace('\\', '/') for p in self.image_paths]
        # Escape special characters for ImageMagick (# is special, needs \#)
        paths = [p.replace('#', '\\#') for p in paths]
        output_path = output_path.replace('\\', '/').replace('#', '\\#')
        
        mode = self.vars['mode'].get()
        scale = 0.5 if preview else 1.0
        v = self.vars  # Shorthand

        if mode == "ashlar":
            dims = self.get_dimensions()
            if not dims:
                return None
            
            cw, ch = v['canvas_w'].get(), v['canvas_h'].get()
            if cw == 0 or ch == 0:
                area = sum(w * h for w, h in dims)
                side = max(int(math.sqrt(area * 1.5)), 1000, int(max(w for w,h in dims) * 1.2))
                cw = ch = side
            if scale < 1:
                cw, ch = int(cw * scale), int(ch * scale)
            
            cmd = ['magick'] + paths + ['-depth', '8']
            if v['normalize_size'].get():
                cmd.extend(['-resize', f'{int(v["target_size"].get() * scale)}x{int(v["target_size"].get() * scale)}'])
            if v['format'].get() in ['jpg', 'jpeg']:
                cmd.extend(['-sampling-factor', '4:4:4', '-quality', str(85 if scale < 1 else v['quality'].get())])
            border = v['border'].get() or 1
            if v['border'].get() == 0:
                cmd.extend(['-bordercolor', 'transparent'])
            if v['best_fit'].get():
                cmd.extend(['-define', 'ashlar:best-fit=true'])
            if v['show_labels'].get():
                cmd.extend(['-label', '%f'])
            cmd.append(f"ashlar:{output_path}[{cw}x{ch}+{border}+{border}]")
            return cmd

        elif mode == "grid":
            cols = v['grid_cols'].get() or int(math.ceil(math.sqrt(len(paths))))
            cmd = ['magick', 'montage'] + paths + ['-depth', '8']
            
            if v['grid_fit'].get() in ["crop", "scale"]:
                dims = [d for d in self.get_dimensions() if d[0] > 0 and d[1] > 0]
                if dims:
                    if v['use_smallest'].get():
                        tw, th = min(dims, key=lambda d: d[0] * d[1])
                    else:
                        tw = sum(w for w,h in dims) // len(dims)
                        th = sum(h for w,h in dims) // len(dims)
                    if scale < 1:
                        tw, th = int(tw * scale), int(th * scale)
                    if v['grid_fit'].get() == "crop":
                        cmd.extend(['-resize', f'{tw}x{th}^', '-gravity', 'center', '-extent', f'{tw}x{th}'])
                    else:
                        cmd.extend(['-resize', f'{tw}x{th}' if v['use_smallest'].get() else f'{tw}x{th}!'])
            
            bg = 'white' if v['format'].get() in ['jpg', 'jpeg'] else 'transparent'
            sp = v['spacing'].get()
            cmd.extend(['-background', bg, '-tile', f'{cols}x', '-geometry', f'+{sp}+{sp}'])
            if v['format'].get() in ['jpg', 'jpeg']:
                cmd.extend(['-sampling-factor', '4:4:4', '-quality', str(85 if scale < 1 else v['quality'].get()), 
                        '-alpha', 'remove', '-alpha', 'off'])
            cmd.append(output_path)
            return cmd

        else:  # horizontal/vertical
            cmd = ['magick'] + paths
            if scale < 1:
                cmd.extend(['-resize', '25%'])
            
            if v['match_size'].get():
                dims = self.get_dimensions()
                if dims:
                    func = min if v['match_smallest'].get() else max
                    if mode == "vertical":
                        w = func(w for w,h in dims if w > 0)
                        if w > 0:
                            cmd.extend(['-resize', f'{int(w * scale)}x'])
                    else:
                        h = func(h for w,h in dims if h > 0)
                        if h > 0:
                            cmd.extend(['-resize', f'x{int(h * scale)}'])
            
            if v['spacing'].get() > 0:
                cmd.extend(['-bordercolor', 'transparent', '-border', 
                           f'{v["spacing"].get()}x{v["spacing"].get()}'])
            cmd.append('+append' if mode == "horizontal" else '-append')
            if v['format'].get() in ['jpg', 'jpeg']:
                cmd.extend(['-sampling-factor', '4:4:4', '-quality', str(85 if scale < 1 else v['quality'].get())])
            cmd.append(output_path)
            return cmd

    def generate_preview(self):
        if len(self.image_paths) < 2:
            return
        self.preview_cancel = True
        if self.preview_thread and self.preview_thread.is_alive():
            self.preview_thread.join(timeout=0.5)
        self.preview_cancel = False
        self.preview_status.config(text="Generating...")
        self.preview_thread = threading.Thread(target=self._preview_worker, daemon=True)
        self.preview_thread.start()

    def _preview_worker(self):
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                temp_path = f.name
            
            cmd = self.build_command(temp_path.replace('\\', '/'), preview=True)
            if not cmd or self.preview_cancel:
                if not cmd:
                    self.root.after(0, lambda: self.preview_status.config(text="Command build failed"))
                return
            
            si = subprocess.STARTUPINFO() if os.name == 'nt' else None
            if si:
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, startupinfo=si, shell=False)
            
            if self.preview_cancel:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return
            
            if result.returncode != 0:
                error_msg = result.stderr[:100] if result.stderr else "Unknown error"
                self.root.after(0, lambda: self.preview_status.config(text=f"Error: {error_msg}"))
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return
            
            self.root.after(0, lambda: self.display_preview(temp_path))
        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self.preview_status.config(text="Preview timeout (30s)"))
        except Exception as e:
            self.root.after(0, lambda: self.preview_status.config(text=f"Error: {str(e)[:50]}"))

    def display_preview(self, path):
        try:
            img = Image.open(path)
            w, h = self.preview_canvas.winfo_width(), self.preview_canvas.winfo_height()
            if w <= 1 or h <= 1:
                self.root.after(100, lambda: self.display_preview(path))
                return
            
            img.thumbnail((w - 20, h - 20), Image.Resampling.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(img)
            self.preview_canvas.delete('all')
            self.preview_canvas.create_image(w // 2, h // 2, image=self.preview_image, anchor='center')
            self.preview_status.config(text=f"{img.width}×{img.height} (scaled)")
            self.root.after(5000, lambda: os.path.exists(path) and os.unlink(path))
        except Exception as e:
            self.preview_status.config(text=f"Display error: {str(e)[:50]}")

    def merge_images(self):
        if len(self.image_paths) < 2:
            messagebox.showerror("Error", "Need at least 2 images!")
            return

        try:
            source_dir = os.path.dirname(self.image_paths[0]) or os.getcwd()
            
            # Use first 60 chars of first filename, add count if multiple images
            base = os.path.splitext(os.path.basename(self.image_paths[0]))[0][:60]
            count = len(self.image_paths)
            suffix = f"_plus{count-1}" if count > 1 else ""
            mode = self.vars['mode'].get()
            fmt = self.vars['format'].get()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{base}{suffix}_{timestamp}_{mode}.{fmt}"
            
            output_path = os.path.join(source_dir, filename)
            
            cmd = self.build_command(output_path.replace('\\', '/'))
            if not cmd:
                raise Exception("Failed to build command")
            
            si = subprocess.STARTUPINFO() if os.name == 'nt' else None
            if si:
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, startupinfo=si, shell=False)
            if result.returncode != 0:
                raise Exception(f"ImageMagick error: {result.stderr}")
            
            # Preserve timestamp
            try:
                ts = os.stat(self.image_paths[0]).st_mtime
                os.utime(output_path, (ts, ts))
                if os.name == 'nt':
                    self.set_windows_creation_time(output_path, ts)
            except:
                pass
            
            if messagebox.askyesno("Done", "Open the merged image?"):
                opener = 'startfile' if os.name == 'nt' else 'open' if 'darwin' in os.uname().sysname.lower() else 'xdg-open'
                if opener == 'startfile':
                    os.startfile(output_path)
                else:
                    subprocess.call([opener, output_path])
            
            self.clear_images()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def set_windows_creation_time(self, path, ts):
        try:
            import ctypes
            from ctypes import wintypes
            k = ctypes.WinDLL('kernel32', use_last_error=True)
            class FT(ctypes.Structure):
                _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]
            ns = int(ts * 10000000) + 116444736000000000
            ft = FT(dwLowDateTime=ns & 0xFFFFFFFF, dwHighDateTime=ns >> 32)
            h = k.CreateFileW(path, 0x100, 0, None, 3, 0, None)
            if h != -1:
                k.SetFileTime(h, ctypes.byref(ft), None, None)
                k.CloseHandle(h)
        except:
            pass

def main():
    root = TkinterDnD.Tk()
    ImageMagickMerger(root)
    root.mainloop()

if __name__ == "__main__":
    main()
