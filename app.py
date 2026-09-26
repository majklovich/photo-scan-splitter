import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk


class PhotoSplitter:
    PREVIEW_PADDING = 12

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

        self.vertical_position = tk.IntVar(value=50)
        self.horizontal_position = tk.IntVar(value=50)

        self._build_ui()

    def _build_ui(self):
        self.gallery_frame = ttk.Frame(self.root, padding=16)
        self.gallery_frame.pack(fill="both", expand=True)
        self.gallery_frame.columnconfigure(0, weight=1)
        self.gallery_frame.rowconfigure(2, weight=1)

        gallery_heading = ttk.Label(
            self.gallery_frame,
            text="Scan Gallery",
            font=("TkDefaultFont", 18, "bold"),
        )
        gallery_heading.grid(row=0, column=0, sticky="w")

        gallery_toolbar = ttk.Frame(self.gallery_frame)
        gallery_toolbar.grid(row=1, column=0, sticky="ew", pady=(12, 12))
        ttk.Button(
            gallery_toolbar, text="Add Scans...", command=self.add_images
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
        gallery_area.grid(row=2, column=0, sticky="nsew")
        gallery_area.columnconfigure(0, weight=1)
        gallery_area.rowconfigure(0, weight=1)
        self.gallery_canvas = tk.Canvas(
            gallery_area,
            background="#e8e8e8",
            highlightthickness=1,
            highlightbackground="#c7c7c7",
        )
        self.gallery_canvas.grid(row=0, column=0, sticky="nsew")
        gallery_scrollbar = ttk.Scrollbar(
            gallery_area, orient="vertical", command=self.gallery_canvas.yview
        )
        gallery_scrollbar.grid(row=0, column=1, sticky="ns")
        self.gallery_canvas.configure(yscrollcommand=gallery_scrollbar.set)
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
        editor_toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Button(
            editor_toolbar, text="Back to Gallery", command=self.show_gallery
        ).pack(side="left")
        self.open_button = ttk.Button(
            editor_toolbar, text="Add More Scans...", command=self.add_images
        )
        self.open_button.pack(side="left", padx=(8, 0))
        self.file_label = ttk.Label(editor_toolbar, text="No image selected")
        self.file_label.pack(side="left", padx=(12, 0))

        self.canvas = tk.Canvas(
            self.editor_frame,
            background="#e8e8e8",
            highlightthickness=1,
            highlightbackground="#c7c7c7",
        )
        self.canvas.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        self.canvas.bind("<Configure>", self._draw_preview)
        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag_line)
        self.canvas.bind("<ButtonRelease-1>", self._stop_drag)
        self.canvas.bind("<Motion>", self._update_cursor)
        self.canvas_open_button = ttk.Button(
            self.canvas, text="Choose Scan...", command=self.add_images
        )
        self.canvas_open_button_window = self.canvas.create_window(
            0, 0, window=self.canvas_open_button, state="hidden"
        )

        action_bar = ttk.Frame(self.editor_frame)
        action_bar.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        action_bar.columnconfigure(0, weight=1)
        self.hint_label = ttk.Label(
            action_bar, text="Drag the red cut lines to adjust the grid."
        )
        self.hint_label.grid(row=0, column=0, sticky="w")
        self.save_as_button = ttk.Button(
            action_bar, text="Save As...", command=self.save_as, state="disabled"
        )
        self.save_as_button.grid(row=0, column=1, padx=(8, 0))
        self.save_button = ttk.Button(
            self.editor_frame, text="Save", command=self.save_default, state="disabled"
        )
        self.save_button.grid(row=4, column=0, sticky="e", pady=(8, 0))

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
        self.vertical_position.set(50)
        self.horizontal_position.set(50)
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
                highlightbackground="#3478c9" if card_index == index else "#c7c7c7",
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
                    background="#ffffff",
                    highlightbackground="#c7c7c7",
                    highlightthickness=1,
                    padx=8,
                    pady=8,
                )
                card.grid(row=index // 4, column=index % 4, padx=8, pady=8, sticky="n")
                image_label = tk.Label(card, image=thumbnail, background="#ffffff")
                image_label.pack()
                name_label = tk.Label(
                    card,
                    text=os.path.basename(path),
                    background="#ffffff",
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

    def _resize_gallery_inner(self, event):
        self.gallery_canvas.itemconfigure(self.gallery_window, width=event.width)

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
            cut_x,
            top,
            cut_x,
            bottom,
            fill="#d8342a",
            width=4,
            tags=("preview", "cut-line", "vertical-line"),
        )
        self.canvas.create_line(
            left,
            cut_y,
            right,
            cut_y,
            fill="#d8342a",
            width=4,
            tags=("preview", "cut-line", "horizontal-line"),
        )

    def _start_drag(self, event):
        if self.image is None or self.preview_box is None:
            return

        left, top, right, bottom = self.preview_box
        cut_x = left + (right - left) * self.vertical_position.get() / 100
        cut_y = top + (bottom - top) * self.horizontal_position.get() / 100
        tolerance = 12
        if abs(event.x - cut_x) <= tolerance and top <= event.y <= bottom:
            self.dragging_line = "vertical"
        elif abs(event.y - cut_y) <= tolerance and left <= event.x <= right:
            self.dragging_line = "horizontal"
        else:
            self.dragging_line = None

    def _drag_line(self, event):
        if self.dragging_line is None or self.preview_box is None:
            return

        left, top, right, bottom = self.preview_box
        if self.dragging_line == "vertical":
            position = (event.x - left) / max(right - left, 1) * 100
            self.vertical_position.set(round(max(10, min(90, position))))
        else:
            position = (event.y - top) / max(bottom - top, 1) * 100
            self.horizontal_position.set(round(max(10, min(90, position))))
        self._draw_preview()

    def _stop_drag(self, _event):
        self.dragging_line = None

    def _update_cursor(self, event):
        if self.image is None or self.preview_box is None:
            self.canvas.configure(cursor="")
            return

        left, top, right, bottom = self.preview_box
        cut_x = left + (right - left) * self.vertical_position.get() / 100
        cut_y = top + (bottom - top) * self.horizontal_position.get() / 100
        tolerance = 12
        on_vertical = abs(event.x - cut_x) <= tolerance and top <= event.y <= bottom
        on_horizontal = abs(event.y - cut_y) <= tolerance and left <= event.x <= right
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
        cut_x = round(width * self.vertical_position.get() / 100)
        cut_y = round(height * self.horizontal_position.get() / 100)
        return (
            (0, 0, cut_x, cut_y),
            (cut_x, 0, width, cut_y),
            (0, cut_y, cut_x, height),
            (cut_x, cut_y, width, height),
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
        paths = [
            os.path.join(output_dir, "{}_{}{}".format(prefix, number + index, extension))
            for index in range(4)
        ]
        try:
            for box, path in zip(self._crop_boxes(), paths):
                crop = self.image.crop(box)
                if image_format == "JPEG" and crop.mode == "RGBA":
                    crop = crop.convert("RGB")
                crop.save(path, format=image_format)
        except OSError as error:
            messagebox.showerror("Could not save photos", str(error))
            return False

        messagebox.showinfo(
            "Done", "4 photos were saved to:\n{}".format(output_dir)
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