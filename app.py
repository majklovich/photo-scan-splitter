import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk


class PhotoSplitter:
    PREVIEW_PADDING = 12
    MAX_GRID_DIMENSION = 20
    SYSTEM_BACKGROUND = "systemWindowBackgroundColor"
    SYSTEM_TEXT = "systemTextColor"
    SYSTEM_ACCENT = "systemControlAccentColor"

    def __init__(self, root):
        self.root = root
        self.root.title("Split Scan into Photos")
        self.root.geometry("1000x720")
        self.root.minsize(760, 560)

        self.scan_paths = []
        self.gallery_selected_index = None
        self.gallery_thumbnails = []
        self.gallery_cards = []
        self.image = None
        self.image_path = None
        self.preview_photo = None
        self.preview_box = None
        self.dragging_line = None

        self.grid_columns = 2
        self.grid_rows = 2
        self.vertical_cuts = [50.0]
        self.horizontal_cuts = [50.0]
        self.grid_columns_var = tk.IntVar(value=self.grid_columns)
        self.grid_rows_var = tk.IntVar(value=self.grid_rows)

        self._configure_theme()
        self._build_ui()

    def _configure_theme(self):
        self.root.configure(background=self.SYSTEM_BACKGROUND)
        self.style = ttk.Style(self.root)
        if "aqua" in self.style.theme_names():
            self.style.theme_use("aqua")

    def _build_ui(self):
        self.gallery_frame = ttk.Frame(self.root)
        self.gallery_frame.pack(fill="both", expand=True)
        self.gallery_frame.columnconfigure(0, weight=1)
        self.gallery_frame.rowconfigure(2, weight=1)

        gallery_heading = ttk.Label(
            self.gallery_frame,
            text="Scan Gallery",
            font=("TkDefaultFont", 18, "bold"),
        )
        gallery_heading.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 0))

        gallery_toolbar = ttk.Frame(self.gallery_frame)
        gallery_toolbar.grid(
            row=1, column=0, sticky="ew", padx=16, pady=(12, 12)
        )
        ttk.Button(
            gallery_toolbar,
            text="Add Scans...",
            command=self.add_images,
        ).pack(side="left")
        self.open_selected_button = ttk.Button(
            gallery_toolbar,
            text="Open Selected",
            command=self.open_selected,
            state="disabled",
        )
        self.open_selected_button.pack(side="left", padx=(8, 0))
        self.remove_selected_button = ttk.Button(
            gallery_toolbar,
            text="Remove Selected",
            command=self.remove_selected,
            state="disabled",
        )
        self.remove_selected_button.pack(side="left", padx=(8, 0))
        self.gallery_status = ttk.Label(gallery_toolbar, text="No scans added")
        self.gallery_status.pack(side="right")

        gallery_area = ttk.Frame(self.gallery_frame)
        gallery_area.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        gallery_area.columnconfigure(0, weight=1)
        gallery_area.rowconfigure(0, weight=1)
        self.gallery_canvas = tk.Canvas(
            gallery_area,
            background=self.SYSTEM_BACKGROUND,
            highlightthickness=1,
        )
        self.gallery_canvas.grid(row=0, column=0, sticky="nsew")
        self.gallery_scrollbar = ttk.Scrollbar(
            gallery_area, orient="vertical", command=self.gallery_canvas.yview
        )
        self.gallery_scrollbar.grid(row=0, column=1, sticky="ns")
        self.gallery_canvas.configure(yscrollcommand=self.gallery_scrollbar.set)
        self.gallery_inner = ttk.Frame(self.gallery_canvas)
        self.gallery_window = self.gallery_canvas.create_window(
            0, 0, window=self.gallery_inner, anchor="nw"
        )
        self.gallery_inner.bind("<Configure>", self._update_gallery_scroll)
        self.gallery_canvas.bind("<Configure>", self._resize_gallery_inner)
        self.gallery_canvas.bind("<Double-Button-1>", self._open_gallery_item)
        self._draw_gallery()

        self.editor_frame = ttk.Frame(self.root, padding=16)
        self.editor_frame.columnconfigure(0, weight=1)
        self.editor_frame.rowconfigure(2, weight=1)
        editor_toolbar = ttk.Frame(self.editor_frame)
        editor_toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 0))
        ttk.Button(
            editor_toolbar, text="Back to Gallery", command=self.show_gallery
        ).pack(side="left")
        self.open_button = ttk.Button(
            editor_toolbar,
            text="Add More Scans...",
            command=self.add_images,
        )
        self.open_button.pack(side="left", padx=(8, 0))
        self.file_label = ttk.Label(editor_toolbar, text="No image selected")
        self.file_label.pack(side="left", padx=(12, 0))

        self.canvas = tk.Canvas(
            self.editor_frame,
            background=self.SYSTEM_BACKGROUND,
            highlightthickness=1,
        )
        self.canvas.grid(
            row=2, column=0, sticky="nsew", padx=16, pady=(12, 0)
        )
        self.canvas.bind("<Configure>", self._draw_preview)
        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag_line)
        self.canvas.bind("<ButtonRelease-1>", self._stop_drag)
        self.canvas.bind("<Motion>", self._update_cursor)
        self.canvas_open_button = ttk.Button(
            self.canvas,
            text="Choose Scan...",
            command=self.add_images,
        )
        self.canvas_open_button_window = self.canvas.create_window(
            0, 0, window=self.canvas_open_button, state="hidden"
        )

        action_bar = ttk.Frame(self.editor_frame)
        action_bar.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 0))
        action_bar.columnconfigure(1, weight=1)
        grid_selector = ttk.Frame(action_bar)
        grid_selector.grid(row=0, column=0, sticky="w")
        ttk.Label(grid_selector, text="Grid:").pack(side="left", padx=(0, 6))
        self.columns_spinbox = ttk.Spinbox(
            grid_selector,
            from_=1,
            to=self.MAX_GRID_DIMENSION,
            width=3,
            textvariable=self.grid_columns_var,
            command=self._grid_dimensions_changed,
            justify="center",
        )
        self.columns_spinbox.pack(side="left")
        ttk.Label(grid_selector, text="×").pack(side="left", padx=5)
        self.rows_spinbox = ttk.Spinbox(
            grid_selector,
            from_=1,
            to=self.MAX_GRID_DIMENSION,
            width=3,
            textvariable=self.grid_rows_var,
            command=self._grid_dimensions_changed,
            justify="center",
        )
        self.rows_spinbox.pack(side="left")
        self.columns_spinbox.bind("<Return>", self._grid_dimensions_changed)
        self.columns_spinbox.bind("<FocusOut>", self._grid_dimensions_changed)
        self.rows_spinbox.bind("<Return>", self._grid_dimensions_changed)
        self.rows_spinbox.bind("<FocusOut>", self._grid_dimensions_changed)
        self.hint_label = ttk.Label(
            action_bar, text="Drag the red cut lines to adjust the grid."
        )
        self.hint_label.grid(row=0, column=1, sticky="w", padx=(16, 0))
        self.save_as_button = ttk.Button(
            action_bar, text="Save As...", command=self.save_as, state="disabled"
        )
        self.save_as_button.grid(row=0, column=2, padx=(8, 0))
        self.save_button = ttk.Button(
            self.editor_frame,
            text="Save",
            command=self.save_default,
            state="disabled",
        )
        self.save_button.grid(
            row=4, column=0, sticky="e", padx=16, pady=(8, 16)
        )

    def add_images(self):
        paths = filedialog.askopenfilenames(
            title="Choose scanned pages",
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp"),
                ("All files", "*"),
            ],
        )
        if not paths:
            return

        added = 0
        invalid = []
        for path in paths:
            if path in self.scan_paths:
                continue
            try:
                with Image.open(path) as source:
                    source.verify()
            except (OSError, ValueError):
                invalid.append(os.path.basename(path))
                continue
            self.scan_paths.append(path)
            added += 1

        self._draw_gallery()
        if invalid:
            messagebox.showerror(
                "Some files could not be added",
                "Could not open:\n{}".format("\n".join(invalid)),
            )
        if added and self.gallery_selected_index is None:
            self._select_gallery_item(0)

    def open_selected(self):
        if self.gallery_selected_index is not None:
            self._open_path(self.gallery_selected_index)

    def _open_gallery_item(self, event):
        item = self.gallery_canvas.find_withtag("current")
        if not item:
            return
        index = self.gallery_canvas.itemcget(item[0], "tags")
        if index.startswith("gallery-item-"):
            self._open_path(int(index.rsplit("-", 1)[1]))

    def _open_path(self, index):
        path = self.scan_paths[index]
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

        self.gallery_selected_index = index
        self.image = image
        self.image_path = path
        self._reset_grid_cuts()
        self.file_label.configure(text=os.path.basename(path))
        self.save_button.configure(state="normal")
        self.save_as_button.configure(state="normal")
        self.gallery_frame.pack_forget()
        self.editor_frame.pack(fill="both", expand=True)
        self._draw_preview()

    def remove_selected(self):
        if self.gallery_selected_index is None:
            return
        del self.scan_paths[self.gallery_selected_index]
        self.gallery_selected_index = None
        self._draw_gallery()

    def show_gallery(self):
        self.editor_frame.pack_forget()
        self.gallery_frame.pack(fill="both", expand=True)
        self._draw_gallery()

    def _select_gallery_item(self, index):
        self.gallery_selected_index = index
        for card_index, card in enumerate(self.gallery_cards):
            card.configure(
                highlightbackground=(
                    self.SYSTEM_ACCENT if card_index == index else self.SYSTEM_BACKGROUND
                ),
                highlightthickness=2 if card_index == index else 1,
            )
        state = "normal" if self.gallery_selected_index is not None else "disabled"
        self.open_selected_button.configure(state=state)
        self.remove_selected_button.configure(state=state)

    def _draw_gallery(self):
        for child in self.gallery_inner.winfo_children():
            child.destroy()
        self.gallery_thumbnails = []
        self.gallery_cards = []
        if not self.scan_paths:
            ttk.Label(
                self.gallery_inner,
                text="No scans added. Choose Add Scans... to begin.",
                padding=30,
            ).grid(row=0, column=0, padx=20, pady=20)
        else:
            for index, path in enumerate(self.scan_paths):
                try:
                    with Image.open(path) as source:
                        thumbnail = ImageOps.contain(source.convert("RGB"), (190, 140))
                        thumbnail = ImageTk.PhotoImage(thumbnail.copy())
                except (OSError, ValueError):
                    continue
                card = tk.Frame(
                    self.gallery_inner,
                    background=self.SYSTEM_BACKGROUND,
                    highlightbackground=self.SYSTEM_BACKGROUND,
                    highlightthickness=1,
                    padx=8,
                    pady=8,
                )
                card.grid(row=index // 4, column=index % 4, padx=8, pady=8, sticky="n")
                image_label = tk.Label(
                    card, image=thumbnail, background=self.SYSTEM_BACKGROUND
                )
                image_label.pack()
                name_label = tk.Label(
                    card,
                    text=os.path.basename(path),
                    background=self.SYSTEM_BACKGROUND,
                    foreground=self.SYSTEM_TEXT,
                    wraplength=190,
                )
                name_label.pack(pady=(6, 0))
                tag = "gallery-item-{}".format(index)
                for widget in (card, image_label, name_label):
                    widget.bind("<Button-1>", lambda _event, i=index: self._select_gallery_item(i))
                    widget.bind("<Double-Button-1>", lambda _event, i=index: self._open_path(i))
                self.gallery_thumbnails.append(thumbnail)
                self.gallery_cards.append(card)
                self.gallery_canvas.create_rectangle(
                    0, 0, 0, 0, tags=tag
                )
            if self.gallery_selected_index is not None and self.gallery_selected_index < len(self.scan_paths):
                self._select_gallery_item(self.gallery_selected_index)
        self.gallery_status.configure(
            text="{} scan{}".format(len(self.scan_paths), "" if len(self.scan_paths) == 1 else "s")
        )
        self._update_gallery_scroll()

    def _update_gallery_scroll(self, _event=None):
        self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox("all"))
        if self.gallery_inner.winfo_reqheight() > self.gallery_canvas.winfo_height():
            self.gallery_scrollbar.grid()
        else:
            self.gallery_scrollbar.grid_remove()

    def _resize_gallery_inner(self, event):
        self.gallery_canvas.itemconfigure(self.gallery_window, width=event.width)

    def _reset_grid_cuts(self):
        self.vertical_cuts = [
            index * 100.0 / self.grid_columns
            for index in range(1, self.grid_columns)
        ]
        self.horizontal_cuts = [
            index * 100.0 / self.grid_rows
            for index in range(1, self.grid_rows)
        ]

    def _grid_dimensions_changed(self, _event=None):
        try:
            columns = int(self.grid_columns_var.get())
            rows = int(self.grid_rows_var.get())
        except (TypeError, ValueError, tk.TclError):
            return

        columns = max(1, min(self.MAX_GRID_DIMENSION, columns))
        rows = max(1, min(self.MAX_GRID_DIMENSION, rows))
        self.grid_columns = columns
        self.grid_rows = rows
        self.grid_columns_var.set(columns)
        self.grid_rows_var.set(rows)
        self._reset_grid_cuts()
        self._draw_preview()

    def _draw_preview(self, _value=None):
        self.canvas.delete("preview")
        self.canvas.delete("cut-line")
        self.canvas.delete("empty-message")
        if self.image is None:
            center_x = max(self.canvas.winfo_width(), 1) / 2
            center_y = max(self.canvas.winfo_height(), 1) / 2
            self.canvas.create_text(
                center_x,
                center_y - 26,
                text="Choose a scanned page",
                fill=self.SYSTEM_TEXT,
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
        for index, position in enumerate(self.vertical_cuts):
            cut_x = left + preview.width * position / 100
            self.canvas.create_line(
                cut_x,
                top,
                cut_x,
                bottom,
                fill=self.SYSTEM_ACCENT,
                width=4,
                tags=("preview", "cut-line", "vertical-line", "vertical-{}".format(index)),
            )
        for index, position in enumerate(self.horizontal_cuts):
            cut_y = top + preview.height * position / 100
            self.canvas.create_line(
                left,
                cut_y,
                right,
                cut_y,
                fill=self.SYSTEM_ACCENT,
                width=4,
                tags=("preview", "cut-line", "horizontal-line", "horizontal-{}".format(index)),
            )

    def _start_drag(self, event):
        if self.image is None or self.preview_box is None:
            return

        left, top, right, bottom = self.preview_box
        tolerance = 12
        nearby_lines = []
        if top <= event.y <= bottom:
            for index, position in enumerate(self.vertical_cuts):
                coordinate = left + (right - left) * position / 100
                distance = abs(event.x - coordinate)
                if distance <= tolerance:
                    nearby_lines.append((distance, "vertical", index))
        if left <= event.x <= right:
            for index, position in enumerate(self.horizontal_cuts):
                coordinate = top + (bottom - top) * position / 100
                distance = abs(event.y - coordinate)
                if distance <= tolerance:
                    nearby_lines.append((distance, "horizontal", index))
        self.dragging_line = None
        if nearby_lines:
            _, direction, index = min(nearby_lines)
            self.dragging_line = (direction, index)

    def _drag_line(self, event):
        if self.dragging_line is None or self.preview_box is None:
            return

        left, top, right, bottom = self.preview_box
        direction, index = self.dragging_line
        if direction == "vertical":
            position = (event.x - left) / max(right - left, 1) * 100
            cuts = self.vertical_cuts
            dimension = self.grid_columns
        else:
            position = (event.y - top) / max(bottom - top, 1) * 100
            cuts = self.horizontal_cuts
            dimension = self.grid_rows
        gap = min(2.0, 100.0 / dimension / 2)
        minimum = cuts[index - 1] + gap if index > 0 else gap
        maximum = cuts[index + 1] - gap if index + 1 < len(cuts) else 100 - gap
        cuts[index] = max(minimum, min(maximum, position))
        self._draw_preview()

    def _stop_drag(self, _event):
        self.dragging_line = None

    def _update_cursor(self, event):
        if self.image is None or self.preview_box is None:
            self.canvas.configure(cursor="")
            return

        left, top, right, bottom = self.preview_box
        tolerance = 12
        on_vertical = top <= event.y <= bottom and any(
            abs(event.x - (left + (right - left) * position / 100)) <= tolerance
            for position in self.vertical_cuts
        )
        on_horizontal = left <= event.x <= right and any(
            abs(event.y - (top + (bottom - top) * position / 100)) <= tolerance
            for position in self.horizontal_cuts
        )
        if on_vertical and on_horizontal:
            cursor = "crosshair"
        elif on_vertical:
            cursor = "sb_h_double_arrow"
        elif on_horizontal:
            cursor = "sb_v_double_arrow"
        else:
            cursor = ""
        try:
            self.canvas.configure(cursor=cursor)
        except tk.TclError:
            self.canvas.configure(cursor="crosshair" if cursor else "")

    def _crop_boxes(self):
        width, height = self.image.size
        x_edges = [0] + [round(width * cut / 100) for cut in self.vertical_cuts] + [width]
        y_edges = [0] + [round(height * cut / 100) for cut in self.horizontal_cuts] + [height]
        return tuple(
            (x_edges[column], y_edges[row], x_edges[column + 1], y_edges[row + 1])
            for row in range(self.grid_rows)
            for column in range(self.grid_columns)
        )

    def _next_number(self, output_dir, prefix):
        pattern = re.compile(r"^{}_(\d+)(?:\.jpg|\.jpeg|\.png)$".format(re.escape(prefix)), re.IGNORECASE)
        numbers = []
        for filename in os.listdir(output_dir):
            match = pattern.match(filename)
            if match:
                numbers.append(int(match.group(1)))
        return max(numbers, default=0) + 1

    def _save_crops(self, output_dir, prefix, extension):
        number = self._next_number(output_dir, prefix)
        image_format = "JPEG" if extension.lower() in (".jpg", ".jpeg") else "PNG"
        crop_boxes = self._crop_boxes()
        paths = [
            os.path.join(output_dir, "{}_{}{}".format(prefix, number + index, extension))
            for index in range(len(crop_boxes))
        ]
        try:
            for box, path in zip(crop_boxes, paths):
                crop = self.image.crop(box)
                if image_format == "JPEG" and crop.mode == "RGBA":
                    crop = crop.convert("RGB")
                crop.save(path, format=image_format)
        except OSError as error:
            messagebox.showerror("Could not save photos", str(error))
            return False

        messagebox.showinfo(
            "Done", "{} photos were saved to:\n{}".format(len(crop_boxes), output_dir)
        )
        return True

    def save_default(self):
        if self.image is None or self.image_path is None:
            return

        output_dir = os.path.dirname(self.image_path)
        self._save_crops(output_dir, "IMG", ".png")

    def save_as(self):
        if self.image is None or self.image_path is None:
            return

        path = filedialog.asksaveasfilename(
            title="Save photos as",
            initialdir=os.path.dirname(self.image_path),
            initialfile="IMG",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("JPEG image", "*.jpg *.jpeg")],
        )
        if not path:
            return

        output_dir = os.path.dirname(path) or os.getcwd()
        filename = os.path.basename(path)
        prefix, extension = os.path.splitext(filename)
        if not prefix:
            prefix = "IMG"
        if extension.lower() not in (".png", ".jpg", ".jpeg"):
            extension = ".png"
        self._save_crops(output_dir, prefix, extension.lower())


def main():
    root = tk.Tk()
    PhotoSplitter(root)
    root.mainloop()


if __name__ == "__main__":
    main()