import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk


class PhotoSplitter:
    PREVIEW_PADDING = 12

    def __init__(self, root):
        self.root = root
        self.root.title("Split Scan into Photos")
        self.root.geometry("900x700")
        self.root.minsize(680, 560)

        self.image = None
        self.image_path = None
        self.preview_photo = None
        self.preview_box = None

        self.vertical_position = tk.IntVar(value=50)
        self.horizontal_position = tk.IntVar(value=50)

        self._build_ui()

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        heading = ttk.Label(
            container,
            text="Split a Scan into 4 Photos",
            font=("TkDefaultFont", 16, "bold"),
        )
        heading.grid(row=0, column=0, sticky="w")

        top_bar = ttk.Frame(container)
        top_bar.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        self.open_button = ttk.Button(
            top_bar, text="Choose Scan...", command=self.open_image
        )
        self.open_button.pack(side="left")
        self.file_label = ttk.Label(top_bar, text="No image selected")
        self.file_label.pack(side="left", padx=(12, 0))

        self.canvas = tk.Canvas(
            container,
            background="#e8e8e8",
            highlightthickness=1,
            highlightbackground="#c7c7c7",
        )
        self.canvas.grid(row=2, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self._draw_preview)
        self.canvas_open_button = ttk.Button(
            self.canvas,
            text="Choose Scan...",
            command=self.open_image,
        )
        self.canvas_open_button_window = self.canvas.create_window(
            0, 0, window=self.canvas_open_button, state="hidden"
        )

        controls = ttk.Frame(container)
        controls.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Vertical cut").grid(row=0, column=0, sticky="w")
        ttk.Label(controls, text="Horizontal cut").grid(row=0, column=1, sticky="w")
        self.vertical_scale = ttk.Scale(
            controls,
            from_=10,
            to=90,
            variable=self.vertical_position,
            command=self._draw_preview,
        )
        self.vertical_scale.grid(row=1, column=0, sticky="ew", padx=(0, 12))
        self.horizontal_scale = ttk.Scale(
            controls,
            from_=10,
            to=90,
            variable=self.horizontal_position,
            command=self._draw_preview,
        )
        self.horizontal_scale.grid(row=1, column=1, sticky="ew")

        self.save_button = ttk.Button(
            container,
            text="Split and Save 4 Photos...",
            command=self.save_photos,
            state="disabled",
        )
        self.save_button.grid(row=4, column=0, sticky="e", pady=(14, 0))

    def open_image(self):
        path = filedialog.askopenfilename(
            title="Choose a scanned page",
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp"),
                ("All files", "*"),
            ],
        )
        if not path:
            return

        try:
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source)
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGB")
                else:
                    image = image.copy()
        except (OSError, ValueError) as error:
            messagebox.showerror("Cannot open image", str(error))
            return

        self.image = image
        self.image_path = path
        self.file_label.configure(text=os.path.basename(path))
        self.save_button.configure(state="normal")
        self._draw_preview()

    def _draw_preview(self, _value=None):
        self.canvas.delete("preview")
        self.canvas.delete("empty-message")
        if self.image is None:
            center_x = max(self.canvas.winfo_width(), 1) / 2
            center_y = max(self.canvas.winfo_height(), 1) / 2
            self.canvas.create_text(
                center_x,
                center_y - 26,
                text="Choose a scanned page",
                fill="#333333",
                font=("TkDefaultFont", 13, "bold"),
                tags="empty-message",
            )
            self.canvas.coords(self.canvas_open_button_window, center_x, center_y + 18)
            self.canvas.itemconfigure(self.canvas_open_button_window, state="normal")
            return

        self.canvas.itemconfigure(self.canvas_open_button_window, state="hidden")
        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)
        available = (
            max(canvas_width - 2 * self.PREVIEW_PADDING, 1),
            max(canvas_height - 2 * self.PREVIEW_PADDING, 1),
        )
        preview = ImageOps.contain(self.image, available)
        self.preview_photo = ImageTk.PhotoImage(preview)

        left = (canvas_width - preview.width) // 2
        top = (canvas_height - preview.height) // 2
        right = left + preview.width
        bottom = top + preview.height
        self.preview_box = (left, top, right, bottom)

        self.canvas.create_image(
            left, top, image=self.preview_photo, anchor="nw", tags="preview"
        )
        cut_x = left + preview.width * self.vertical_position.get() / 100
        cut_y = top + preview.height * self.horizontal_position.get() / 100
        self.canvas.create_line(
            cut_x, top, cut_x, bottom, fill="#d8342a", width=2, tags="preview"
        )
        self.canvas.create_line(
            left, cut_y, right, cut_y, fill="#d8342a", width=2, tags="preview"
        )

    def save_photos(self):
        if self.image is None or self.image_path is None:
            return

        output_dir = filedialog.askdirectory(
            title="Choose a folder for the saved photos",
            initialdir=os.path.dirname(self.image_path),
        )
        if not output_dir:
            return

        width, height = self.image.size
        cut_x = round(width * self.vertical_position.get() / 100)
        cut_y = round(height * self.horizontal_position.get() / 100)
        boxes = (
            (0, 0, cut_x, cut_y),
            (cut_x, 0, width, cut_y),
            (0, cut_y, cut_x, height),
            (cut_x, cut_y, width, height),
        )
        paths = [os.path.join(output_dir, "photo_{}.png".format(i)) for i in range(1, 5)]

        existing = [path for path in paths if os.path.exists(path)]
        if existing and not messagebox.askyesno(
            "Files already exist",
            "Some output files already exist. Do you want to overwrite them?",
        ):
            return

        try:
            for box, path in zip(boxes, paths):
                self.image.crop(box).save(path, format="PNG")
        except OSError as error:
            messagebox.showerror("Could not save photos", str(error))
            return

        messagebox.showinfo(
            "Done", "4 photos were saved to:\n{}".format(output_dir)
        )


def main():
    root = tk.Tk()
    PhotoSplitter(root)
    root.mainloop()


if __name__ == "__main__":
    main()