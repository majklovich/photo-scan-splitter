import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk


class PhotoSplitter:
    PREVIEW_PADDING = 12

    def __init__(self, root):
        self.root = root
        self.root.title("Rozdělení skenu na fotografie")
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
            text="Rozdělení skenu na 4 fotografie",
            font=("TkDefaultFont", 16, "bold"),
        )
        heading.grid(row=0, column=0, sticky="w")

        top_bar = ttk.Frame(container)
        top_bar.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        self.open_button = ttk.Button(
            top_bar, text="Vybrat sken...", command=self.open_image
        )
        self.open_button.pack(side="left")
        self.file_label = ttk.Label(top_bar, text="Není vybraný žádný obrázek")
        self.file_label.pack(side="left", padx=(12, 0))

        self.canvas = tk.Canvas(
            container,
            background="#e8e8e8",
            highlightthickness=1,
            highlightbackground="#c7c7c7",
        )
        self.canvas.grid(row=2, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self._draw_preview)

        controls = ttk.Frame(container)
        controls.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Svislý řez").grid(row=0, column=0, sticky="w")
        ttk.Label(controls, text="Vodorovný řez").grid(row=0, column=1, sticky="w")
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
            text="Rozdělit a uložit 4 fotografie...",
            command=self.save_photos,
            state="disabled",
        )
        self.save_button.grid(row=4, column=0, sticky="e", pady=(14, 0))

    def open_image(self):
        path = filedialog.askopenfilename(
            title="Vyberte naskenovanou fotografii",
            filetypes=[
                ("Obrázky", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp"),
                ("Všechny soubory", "*"),
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
            messagebox.showerror("Nelze otevřít obrázek", str(error))
            return

        self.image = image
        self.image_path = path
        self.file_label.configure(text=os.path.basename(path))
        self.save_button.configure(state="normal")
        self._draw_preview()

    def _draw_preview(self, _value=None):
        if self.image is None:
            return

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

        self.canvas.delete("all")
        self.canvas.create_image(left, top, image=self.preview_photo, anchor="nw")
        cut_x = left + preview.width * self.vertical_position.get() / 100
        cut_y = top + preview.height * self.horizontal_position.get() / 100
        self.canvas.create_line(cut_x, top, cut_x, bottom, fill="#d8342a", width=2)
        self.canvas.create_line(left, cut_y, right, cut_y, fill="#d8342a", width=2)

    def save_photos(self):
        if self.image is None or self.image_path is None:
            return

        output_dir = filedialog.askdirectory(
            title="Vyberte složku pro uložené fotografie",
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
        paths = [os.path.join(output_dir, "fotografie_{}.png".format(i)) for i in range(1, 5)]

        existing = [path for path in paths if os.path.exists(path)]
        if existing and not messagebox.askyesno(
            "Soubory už existují",
            "Některé výstupní soubory už existují. Chcete je přepsat?",
        ):
            return

        try:
            for box, path in zip(boxes, paths):
                self.image.crop(box).save(path, format="PNG")
        except OSError as error:
            messagebox.showerror("Uložení se nezdařilo", str(error))
            return

        messagebox.showinfo(
            "Hotovo", "Uloženy 4 fotografie do složky:\n{}".format(output_dir)
        )


def main():
    root = tk.Tk()
    PhotoSplitter(root)
    root.mainloop()


if __name__ == "__main__":
    main()