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
        self.root.title("photo-scan-splitter")
        self.root.geometry("1000x720")
        self.root.minsize(760, 560)

        self.scan_paths = []
        self.gallery_selected_index = None
        self.gallery_selected_indices = set()
        self.gallery_thumbnails = []
        self.gallery_cards = []
        self.gallery_item_boxes = []
        self.marquee_start = None
        self.marquee_item = None
        self.marquee_base_selection = set()
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
        self.gallery_canvas.bind("<Configure>", self._draw_gallery)
        self.gallery_canvas.bind("<ButtonPress-1>", self._gallery_mouse_down)
        self.gallery_canvas.bind(
            "<Command-ButtonPress-1>",
            lambda event: self._gallery_mouse_down(event, toggle=True),
        )
        self.gallery_canvas.bind(
            "<Control-ButtonPress-1>",
            lambda event: self._gallery_mouse_down(event, toggle=True),
        )
        self.gallery_canvas.bind("<B1-Motion>", self._gallery_mouse_drag)
        self.gallery_canvas.bind("<ButtonRelease-1>", self._gallery_mouse_up)
        self.gallery_canvas.bind("<Double-Button-1>", self._open_gallery_item)
        self.gallery_canvas.bind("<MouseWheel>", self._scroll_gallery)
        self.gallery_canvas.bind("<TouchpadScroll>", self._scroll_gallery_touchpad)
        self.root.bind_all("<MouseWheel>", self._scroll_gallery)
        self.root.bind_all("<TouchpadScroll>", self._scroll_gallery_touchpad)
        self.root.bind_all(
            "<Button-4>", lambda _event: self._scroll_gallery_by(-1)
        )
        self.root.bind_all(
            "<Button-5>", lambda _event: self._scroll_gallery_by(1)
        )
        self.root.bind_all("<Command-BackSpace>", self._remove_selected_key)
        self.root.bind_all("<Delete>", self._remove_selected_key)
        self.root.bind_all("<BackSpace>", self._remove_selected_key)
        self._draw_gallery()
        ttk.Label(
            self.gallery_frame,
            text="photo-scan-splitter 1.0 © Michal G 2026",
            font=("TkDefaultFont", 9),
        ).grid(row=3, column=0, pady=(0, 10))

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
        ttk.Label(
            self.editor_frame,
            text="photo-scan-splitter 1.0 © Michal G 2026",
            font=("TkDefaultFont", 9),
        ).grid(row=5, column=0, pady=(0, 4))

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
        if len(self.gallery_selected_indices) == 1:
            self._open_path(self.gallery_selected_index)

    def _open_gallery_item(self, event):
        index = self._gallery_item_at(event.x, event.y)
        if index is not None:
            self._open_path(index)

    def _gallery_item_at(self, x, y):
        canvas_x = self.gallery_canvas.canvasx(x)
        canvas_y = self.gallery_canvas.canvasy(y)
        for item in reversed(
            self.gallery_canvas.find_overlapping(canvas_x, canvas_y, canvas_x, canvas_y)
        ):
            for tag in self.gallery_canvas.gettags(item):
                if tag.startswith("gallery-item-"):
                    return int(tag.rsplit("-", 1)[1])
        return None

    def _gallery_mouse_down(self, event, toggle=False):
        index = self._gallery_item_at(event.x, event.y)
        if index is not None:
            self.marquee_start = None
            self._select_gallery_item(index, toggle=toggle)
            return "break"

        self.marquee_start = (
            self.gallery_canvas.canvasx(event.x),
            self.gallery_canvas.canvasy(event.y),
        )
        self.marquee_base_selection = (
            set(self.gallery_selected_indices) if toggle else set()
        )
        if not toggle:
            self._set_gallery_selection(set())
        if self.marquee_item is not None:
            self.gallery_canvas.delete(self.marquee_item)
        self.marquee_item = self.gallery_canvas.create_rectangle(
            self.marquee_start[0],
            self.marquee_start[1],
            self.marquee_start[0],
            self.marquee_start[1],
            outline=self.SYSTEM_ACCENT,
            dash=(3, 2),
            width=1,
            tags="marquee",
        )
        return "break"

    def _gallery_mouse_drag(self, event):
        if self.marquee_start is None or self.marquee_item is None:
            return
        current_x = self.gallery_canvas.canvasx(event.x)
        current_y = self.gallery_canvas.canvasy(event.y)
        start_x, start_y = self.marquee_start
        x1, x2 = sorted((start_x, current_x))
        y1, y2 = sorted((start_y, current_y))
        self.gallery_canvas.coords(self.marquee_item, x1, y1, x2, y2)
        if abs(current_x - start_x) < 4 and abs(current_y - start_y) < 4:
            return "break"

        enclosed = {
            index
            for index, (left, top, right, bottom) in self.gallery_item_boxes
            if left <= x2 and right >= x1 and top <= y2 and bottom >= y1
        }
        self._set_gallery_selection(self.marquee_base_selection | enclosed)
        return "break"

    def _gallery_mouse_up(self, _event):
        if self.marquee_start is None:
            return
        if self.marquee_item is not None:
            self.gallery_canvas.delete(self.marquee_item)
        self.marquee_item = None
        self.marquee_start = None
        self.marquee_base_selection.clear()
        return "break"

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
        self._set_gallery_selection({index})
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
        if not self.gallery_selected_indices:
            return
        for index in sorted(self.gallery_selected_indices, reverse=True):
            del self.scan_paths[index]
        self.gallery_selected_indices.clear()
        self.gallery_selected_index = None
        self._draw_gallery()

    def _remove_selected_key(self, _event=None):
        if not self.gallery_frame.winfo_ismapped() or not self.gallery_selected_indices:
            return
        self.remove_selected()
        return "break"

    def show_gallery(self):
        self.editor_frame.pack_forget()
        self.gallery_frame.pack(fill="both", expand=True)
        self._draw_gallery()

    def _select_gallery_item(self, index, toggle=False):
        selection = set(self.gallery_selected_indices)
        if toggle and index in selection:
            selection.remove(index)
        elif toggle:
            selection.add(index)
        else:
            selection = {index}
        active = index if index in selection else None
        self._set_gallery_selection(selection, active)

    def _set_gallery_selection(self, indices, active=None):
        self.gallery_selected_indices = {
            index for index in indices if 0 <= index < len(self.scan_paths)
        }
        if active in self.gallery_selected_indices:
            self.gallery_selected_index = active
        elif self.gallery_selected_indices:
            self.gallery_selected_index = min(self.gallery_selected_indices)
        else:
            self.gallery_selected_index = None

        for index, card in self.gallery_cards:
            selected = index in self.gallery_selected_indices
            self.gallery_canvas.itemconfigure(
                card,
                outline=self.SYSTEM_ACCENT if selected else self.SYSTEM_BACKGROUND,
                width=2 if selected else 1,
            )
        self.open_selected_button.configure(
            state="normal" if len(self.gallery_selected_indices) == 1 else "disabled"
        )
        self.remove_selected_button.configure(
            state="normal" if self.gallery_selected_indices else "disabled"
        )

    def _draw_gallery(self, _event=None):
        self.gallery_canvas.delete("all")
        self.gallery_thumbnails = []
        self.gallery_cards = []
        self.gallery_item_boxes = []
        if not self.scan_paths:
            window_center_x = (
                self.root.winfo_rootx()
                + self.root.winfo_width() / 2
                - self.gallery_canvas.winfo_rootx()
            )
            window_center_y = (
                self.root.winfo_rooty()
                + self.root.winfo_height() / 2
                - self.gallery_canvas.winfo_rooty()
            )
            self.gallery_canvas.create_text(
                self.gallery_canvas.canvasx(window_center_x),
                self.gallery_canvas.canvasy(window_center_y),
                text="No scans added. Choose Add Scans... to begin.",
                fill=self.SYSTEM_TEXT,
                tags="empty-gallery",
            )
        else:
            canvas_width = max(self.gallery_canvas.winfo_width(), 1)
            card_width = 220
            card_height = 190
            spacing = 16
            margin = 16
            column_count = max(
                1,
                (canvas_width - 2 * margin + spacing) // (card_width + spacing),
            )
            for index, path in enumerate(self.scan_paths):
                try:
                    with Image.open(path) as source:
                        thumbnail = ImageOps.contain(source.convert("RGB"), (190, 140))
                        thumbnail = ImageTk.PhotoImage(thumbnail.copy())
                except (OSError, ValueError):
                    continue
                column = index % column_count
                row = index // column_count
                left = margin + column * (card_width + spacing)
                top = margin + row * (card_height + spacing)
                right = left + card_width
                bottom = top + card_height
                tags = ("gallery-item", "gallery-item-{}".format(index))
                card = self.gallery_canvas.create_rectangle(
                    left,
                    top,
                    right,
                    bottom,
                    fill="systemControlBackgroundColor",
                    outline=(
                        self.SYSTEM_ACCENT
                        if index in self.gallery_selected_indices
                        else self.SYSTEM_BACKGROUND
                    ),
                    width=2 if index in self.gallery_selected_indices else 1,
                    tags=tags,
                )
                self.gallery_canvas.create_image(
                    left + card_width / 2,
                    top + 12,
                    image=thumbnail,
                    anchor="n",
                    tags=tags,
                )
                self.gallery_canvas.create_text(
                    left + card_width / 2,
                    top + 158,
                    text=os.path.basename(path),
                    fill=self.SYSTEM_TEXT,
                    width=card_width - 20,
                    justify="center",
                    anchor="n",
                    tags=tags,
                )
                self.gallery_thumbnails.append(thumbnail)
                self.gallery_cards.append((index, card))
                self.gallery_item_boxes.append((index, (left, top, right, bottom)))
        self._set_gallery_selection(
            self.gallery_selected_indices, self.gallery_selected_index
        )
        self.gallery_status.configure(
            text="{} scan{}".format(len(self.scan_paths), "" if len(self.scan_paths) == 1 else "s")
        )
        self._update_gallery_scroll()

    def _update_gallery_scroll(self, _event=None):
        self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox("all"))
        bounds = self.gallery_canvas.bbox("all")
        content_height = bounds[3] if bounds else 0
        if content_height > self.gallery_canvas.winfo_height():
            self.gallery_scrollbar.grid()
        else:
            self.gallery_scrollbar.grid_remove()

    def _scroll_gallery(self, event):
        if not self.gallery_frame.winfo_ismapped():
            return
        delta = event.delta
        if not delta:
            return
        if abs(delta) >= 120:
            steps = int(-delta / 120)
        else:
            steps = -int(delta)
            if steps == 0 and delta:
                steps = -1 if delta > 0 else 1
        return self._scroll_gallery_by(steps)

    def _scroll_gallery_touchpad(self, event):
        if not self.gallery_frame.winfo_ismapped():
            return

        delta_y = event.delta & 0xFFFF
        if delta_y & 0x8000:
            delta_y -= 0x10000
        if not delta_y:
            return "break"

        bounds = self.gallery_canvas.bbox("all")
        if not bounds:
            return "break"
        content_height = bounds[3] - bounds[1]
        if content_height > 0:
            current_position = self.gallery_canvas.yview()[0]
            self.gallery_canvas.yview_moveto(
                current_position - delta_y / content_height
            )
        return "break"

    def _scroll_gallery_by(self, steps):
        if steps and self.gallery_frame.winfo_ismapped():
            self.gallery_canvas.yview_scroll(steps, "units")
            return "break"

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