import csv
import os
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}
MAX_DISPLAY_SIZE = (900, 650)
BASE_BG = "#0b1224"
CARD_BG = "#0f1c33"
TEXT_PRIMARY = "#e4ecff"
TEXT_MUTED = "#b7c4e0"
ACCENT_GRADIENT = ["#ff6b6b", "#fcbf49", "#7ee0c3", "#6fa3ff", "#c77dff", "#ff7ab5"]


def read_labels_file(path: Path) -> list[str]:
    lines = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            cleaned = line.strip()
            if cleaned:
                lines.append(cleaned)
    return lines


def shade_color(color: str, factor: float) -> str:
    """Darken or lighten a hex color by factor (0..1 darker, >1 lighter)."""
    color = color.lstrip("#")
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


class ImageLabelerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Image Labeller")
        self.root.geometry("1300x900")
        self.root.configure(bg=BASE_BG)

        if Image is None or ImageTk is None:
            messagebox.showerror(
                "Missing dependency",
                "Pillow is required to display images.\nInstall it with:\n\npip install pillow",
            )
            self.root.destroy()
            return

        self.image_paths: list[str] = []
        self.labels: list[str] = []
        self.annotations: dict[str, tuple[str, str]] = {}
        self.label_counts: dict[str, int] = {}
        self.current_index: int = 0
        self.csv_path: Path | None = None
        self.photo_ref = None

        self.folder_var = tk.StringVar()
        self.labels_var = tk.StringVar()
        self.csv_var = tk.StringVar()
        self.progress_var = tk.StringVar(value="No images loaded")
        self.caption_var = tk.StringVar(value="Pick a folder to get started")
        self.current_label_var = tk.StringVar(value="Label: —")

        self.label_buttons: dict[str, ttk.Button] = {}
        self.count_badges: dict[str, tk.Label] = {}
        self.label_styles: Dict[str, Dict[str, str]] = {}

        self._build_styles()
        self._build_layout()
        self._bind_keys()

    def _build_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("Card.TFrame", background=CARD_BG)
        style.configure(
            "Header.TLabel",
            background=BASE_BG,
            foreground=TEXT_PRIMARY,
            font=("Futura", 20, "bold"),
        )
        style.configure(
            "Body.TLabel",
            background=CARD_BG,
            foreground=TEXT_MUTED,
            font=("Helvetica Neue", 12),
        )
        style.configure(
            "Badge.TLabel",
            background=CARD_BG,
            foreground=TEXT_PRIMARY,
            font=("Helvetica Neue", 12, "bold"),
        )
        style.configure(
            "Accent.TButton",
            font=("Helvetica Neue", 12, "bold"),
            foreground=BASE_BG,
            background="#7ee0c3",
            padding=10,
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#66c8ac")],
            foreground=[("active", BASE_BG)],
        )
        style.configure(
            "Nav.TButton",
            font=("Helvetica Neue", 12, "bold"),
            foreground=TEXT_PRIMARY,
            background="#22345b",
            padding=10,
        )
        style.map("Nav.TButton", background=[("active", "#2e4a83")])
        style.configure(
            "Input.TEntry",
            fieldbackground=BASE_BG,
            background=BASE_BG,
            foreground=TEXT_PRIMARY,
            padding=6,
        )
        style.configure(
            "Caption.TLabel",
            background=CARD_BG,
            foreground="#9ad3ff",
            font=("Futura", 13, "bold"),
        )

    def _build_layout(self) -> None:
        gradient_bar = tk.Canvas(
            self.root, height=10, highlightthickness=0, bd=0, relief="flat", bg=BASE_BG
        )
        gradient_bar.pack(fill="x")
        self._draw_gradient_bar(gradient_bar)

        top_frame = ttk.Frame(self.root, style="Card.TFrame", padding=16)
        top_frame.pack(fill="x", padx=18, pady=(16, 8))

        ttk.Label(
            top_frame, text="Image Labeller", style="Header.TLabel"
        ).grid(row=0, column=0, sticky="w", columnspan=6, pady=(0, 8))
        ttk.Label(
            top_frame,
            text="",
            style="Caption.TLabel",
        ).grid(row=0, column=1, sticky="w", pady=(0, 8), padx=(12, 0))

        ttk.Label(top_frame, text="Images folder", style="Body.TLabel").grid(
            row=1, column=0, sticky="w", pady=4
        )
        folder_entry = ttk.Entry(
            top_frame, textvariable=self.folder_var, width=60, style="Input.TEntry"
        )
        folder_entry.grid(row=1, column=1, sticky="we", pady=4, padx=(8, 8))
        ttk.Button(
            top_frame,
            text="Browse",
            style="Nav.TButton",
            command=self._choose_folder,
        ).grid(row=1, column=2, sticky="e", pady=4)

        ttk.Label(top_frame, text="Labels file", style="Body.TLabel").grid(
            row=2, column=0, sticky="w", pady=4
        )
        labels_entry = ttk.Entry(
            top_frame, textvariable=self.labels_var, width=60, style="Input.TEntry"
        )
        labels_entry.grid(row=2, column=1, sticky="we", pady=4, padx=(8, 8))
        ttk.Button(
            top_frame,
            text="Browse",
            style="Nav.TButton",
            command=self._choose_labels_file,
        ).grid(row=2, column=2, sticky="e", pady=4)

        ttk.Label(top_frame, text="CSV output", style="Body.TLabel").grid(
            row=3, column=0, sticky="w", pady=4
        )
        csv_entry = ttk.Entry(
            top_frame, textvariable=self.csv_var, width=60, style="Input.TEntry"
        )
        csv_entry.grid(row=3, column=1, sticky="we", pady=4, padx=(8, 8))
        ttk.Button(
            top_frame,
            text="Set",
            style="Nav.TButton",
            command=self._choose_csv_file,
        ).grid(row=3, column=2, sticky="e", pady=4)

        ttk.Button(
            top_frame,
            text="Load project",
            style="Accent.TButton",
            command=self.initialize_project,
        ).grid(row=1, column=3, rowspan=3, padx=(16, 0))

        top_frame.columnconfigure(1, weight=1)

        body_frame = ttk.Frame(self.root, style="Card.TFrame", padding=16)
        body_frame.pack(fill="both", expand=True, padx=18, pady=8)
        body_frame.columnconfigure(0, weight=3)
        body_frame.columnconfigure(1, weight=1)
        body_frame.rowconfigure(0, weight=1)

        # Image viewer
        viewer_frame = ttk.Frame(body_frame, style="Card.TFrame", padding=12)
        viewer_frame.grid(row=0, column=0, sticky="nsew")
        viewer_frame.rowconfigure(1, weight=1)
        viewer_frame.columnconfigure(0, weight=1)

        ttk.Label(viewer_frame, textvariable=self.caption_var, style="Body.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        self.image_panel = tk.Label(
            viewer_frame,
            bg="#0a0f1f",
            bd=0,
            highlightthickness=3,
            highlightbackground="#1f2e4f",
            relief="flat",
        )
        self.image_panel.grid(row=1, column=0, sticky="nsew")

        progress_bar = ttk.Frame(viewer_frame, style="Card.TFrame")
        progress_bar.grid(row=2, column=0, sticky="we", pady=(10, 0))

        ttk.Label(
            progress_bar, textvariable=self.progress_var, style="Body.TLabel"
        ).pack(side="left")
        ttk.Label(
            progress_bar, textvariable=self.current_label_var, style="Body.TLabel"
        ).pack(side="right")

        # Controls + stats
        side_frame = ttk.Frame(body_frame, style="Card.TFrame", padding=12)
        side_frame.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        side_frame.columnconfigure(0, weight=1)

        ttk.Label(side_frame, text="Labels", style="Header.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.labels_container = ttk.Frame(side_frame, style="Card.TFrame")
        self.labels_container.grid(row=1, column=0, sticky="we", pady=(8, 12))
        self.labels_container.columnconfigure(0, weight=1)

        ttk.Label(side_frame, text="Counts", style="Header.TLabel").grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        self.counts_container = ttk.Frame(side_frame, style="Card.TFrame")
        self.counts_container.grid(row=3, column=0, sticky="we", pady=(8, 12))
        self.counts_container.columnconfigure(0, weight=1)

        nav_frame = ttk.Frame(side_frame, style="Card.TFrame")
        nav_frame.grid(row=4, column=0, sticky="we", pady=(10, 0))
        nav_frame.columnconfigure((0, 1), weight=1)

        ttk.Button(
            nav_frame, text="◀ Previous", style="Nav.TButton", command=self.prev_image
        ).grid(row=0, column=0, sticky="we", padx=(0, 6))
        ttk.Button(
            nav_frame, text="Next ▶", style="Nav.TButton", command=self.next_image
        ).grid(row=0, column=1, sticky="we", padx=(6, 0))

    def _bind_keys(self) -> None:
        self.root.bind("<Left>", lambda event: self.prev_image())
        self.root.bind("<Right>", lambda event: self.next_image())

    def _choose_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Select images folder")
        if chosen:
            self.folder_var.set(chosen)
            if not self.csv_var.get():
                self.csv_var.set(str(Path(chosen) / "labels.csv"))

    def _choose_labels_file(self) -> None:
        chosen = filedialog.askopenfilename(
            title="Select labels text file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if chosen:
            self.labels_var.set(chosen)

    def _choose_csv_file(self) -> None:
        chosen = filedialog.asksaveasfilename(
            title="Save CSV as",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if chosen:
            self.csv_var.set(chosen)

    def initialize_project(self) -> None:
        folder = Path(self.folder_var.get()).expanduser()
        labels_file = Path(self.labels_var.get()).expanduser()

        if not folder.is_dir():
            messagebox.showwarning("Invalid folder", "Pick a valid images folder.")
            return
        if not labels_file.is_file():
            messagebox.showwarning("Missing labels", "Pick a valid labels text file.")
            return

        self.labels = read_labels_file(labels_file)
        if not self.labels:
            messagebox.showwarning(
                "Empty labels file", "Add at least one label to your text file."
            )
            return

        images = []
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
                images.append(str(path.resolve()))
        images.sort()

        if not images:
            messagebox.showwarning(
                "No images found",
                "The selected folder (and subfolders) has no supported image files.",
            )
            return

        self.image_paths = images
        self.label_counts = {label: 0 for label in self.labels}
        self.annotations = {}
        self.current_index = 0

        csv_candidate = self.csv_var.get().strip()
        if csv_candidate:
            self.csv_path = Path(csv_candidate).expanduser()
        else:
            self.csv_path = folder / "labels.csv"
            self.csv_var.set(str(self.csv_path))

        self._render_label_buttons()
        self._render_count_badges()
        self._load_existing_annotations()
        self._show_image()

    def _render_label_buttons(self) -> None:
        for widget in self.labels_container.winfo_children():
            widget.destroy()
        self.label_buttons.clear()
        self.label_styles.clear()

        palette = ACCENT_GRADIENT
        for idx, label in enumerate(self.labels):
            base_color = palette[idx % len(palette)]
            darker = shade_color(base_color, 0.9)
            lighter = shade_color(base_color, 1.15)
            style_name = f"Label{idx}.TButton"
            selected_style = f"Label{idx}.Selected.TButton"
            style = ttk.Style()
            style.configure(
                style_name,
                font=("Helvetica Neue", 12, "bold"),
                foreground=BASE_BG,
                background=base_color,
                padding=12,
                borderwidth=0,
                focuscolor=BASE_BG,
            )
            style.map(
                style_name,
                background=[("active", lighter), ("pressed", darker)],
                foreground=[("active", BASE_BG)],
            )
            style.configure(
                selected_style,
                font=("Helvetica Neue", 12, "bold"),
                foreground=BASE_BG,
                background=lighter,
                padding=12,
                borderwidth=0,
            )

            self.label_styles[label] = {
                "style": style_name,
                "selected": selected_style,
                "color": base_color,
            }

        for idx, label in enumerate(self.labels):
            btn = ttk.Button(
                self.labels_container,
                text=label,
                style=self.label_styles[label]["style"],
                command=lambda l=label: self._set_label(l),
            )
            btn.grid(row=idx, column=0, sticky="we", pady=4)
            self.label_buttons[label] = btn
        self._highlight_label_buttons(None)

    def _render_count_badges(self) -> None:
        for widget in self.counts_container.winfo_children():
            widget.destroy()
        self.count_badges.clear()

        for idx, label in enumerate(self.labels):
            frame = ttk.Frame(self.counts_container, style="Card.TFrame")
            frame.grid(row=idx, column=0, sticky="we", pady=2)
            frame.columnconfigure(1, weight=1)
            name = ttk.Label(frame, text=label, style="Body.TLabel")
            name.grid(row=0, column=0, sticky="w")
            badge_color = (
                self.label_styles[label]["color"]
                if label in self.label_styles
                else "#7ee0c3"
            )
            badge = tk.Label(
                frame,
                text="0",
                fg=BASE_BG,
                bg=badge_color,
                font=("Helvetica Neue", 11, "bold"),
                padx=10,
                pady=3,
            )
            badge.grid(row=0, column=1, sticky="e")
            self.count_badges[label] = badge

    def _load_existing_annotations(self) -> None:
        if not self.csv_path or not self.csv_path.exists():
            self._refresh_counts()
            return

        try:
            with self.csv_path.open("r", newline="", encoding="utf-8") as handle:
                reader = csv.reader(handle)
                for row in reader:
                    if len(row) != 3 or row[0] == "timestamp":
                        continue
                    timestamp, image_path, label = row
                    if image_path in self.image_paths:
                        previous = self.annotations.get(image_path)
                        if previous and previous[1] in self.label_counts:
                            self.label_counts[previous[1]] = max(
                                0, self.label_counts[previous[1]] - 1
                            )
                        self.annotations[image_path] = (timestamp, label)
                        if label in self.label_counts:
                            self.label_counts[label] += 1
        except Exception as exc:
            messagebox.showwarning(
                "CSV load issue", f"Could not read existing CSV: {exc}"
            )

        self._refresh_counts()

    def _refresh_counts(self) -> None:
        total_labeled = sum(self.label_counts.values())
        for label, badge in self.count_badges.items():
            badge.configure(text=str(self.label_counts.get(label, 0)))
        self.progress_var.set(
            f"Labeled {total_labeled} / {len(self.image_paths)} images"
            if self.image_paths
            else "No images loaded"
        )
        self._update_current_label_text()

    def _show_image(self) -> None:
        if not self.image_paths:
            self.caption_var.set("No images loaded")
            self.image_panel.configure(image="", text="")
            return

        path = Path(self.image_paths[self.current_index])
        self.caption_var.set(f"{path.name} — {self.current_index + 1}/{len(self.image_paths)}")

        try:
            image = Image.open(path)
            image.thumbnail(MAX_DISPLAY_SIZE, Image.LANCZOS)
            self.photo_ref = ImageTk.PhotoImage(image)
            self.image_panel.configure(image=self.photo_ref, text="")
        except Exception as exc:
            self.image_panel.configure(
                image="",
                text=f"Could not load image:\n{exc}",
                fg="#e86b6b",
                bg="#0b1326",
            )
            self.photo_ref = None
        self._update_current_label_text()

    def _set_label(self, label: str) -> None:
        if not self.image_paths or label not in self.labels:
            return
        image_path = self.image_paths[self.current_index]
        timestamp = datetime.now().isoformat(timespec="seconds")
        previous = self.annotations.get(image_path)
        previous_label = previous[1] if previous else None

        if previous_label == label:
            self.annotations[image_path] = (timestamp, label)
        else:
            if previous_label and previous_label in self.label_counts:
                self.label_counts[previous_label] = max(
                    0, self.label_counts[previous_label] - 1
                )
            if label in self.label_counts:
                self.label_counts[label] += 1
            self.annotations[image_path] = (timestamp, label)

        self._write_csv()
        self._refresh_counts()
        self._update_current_label_text()
        self.next_image()

    def _write_csv(self) -> None:
        if not self.csv_path:
            return
        try:
            with self.csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["timestamp", "image_path", "label"])
                for path in self.image_paths:
                    if path in self.annotations:
                        timestamp, label = self.annotations[path]
                        writer.writerow([timestamp, path, label])
        except Exception as exc:
            messagebox.showwarning("CSV write issue", f"Could not write CSV: {exc}")

    def _update_current_label_text(self) -> None:
        if not self.image_paths:
            self.current_label_var.set("Label: —")
            return
        image_path = self.image_paths[self.current_index]
        if image_path in self.annotations:
            self.current_label_var.set(f"Label: {self.annotations[image_path][1]}")
            self._highlight_label_buttons(self.annotations[image_path][1])
        else:
            self.current_label_var.set("Label: Unlabeled")
            self._highlight_label_buttons(None)

    def _highlight_label_buttons(self, selected_label: str | None) -> None:
        for label, button in self.label_buttons.items():
            styles = self.label_styles.get(label)
            if not styles:
                continue
            new_style = (
                styles["selected"] if selected_label and label == selected_label else styles["style"]
            )
            button.configure(style=new_style)

    def next_image(self) -> None:
        if not self.image_paths:
            return
        self.current_index = (self.current_index + 1) % len(self.image_paths)
        self._show_image()

    def prev_image(self) -> None:
        if not self.image_paths:
            return
        self.current_index = (self.current_index - 1) % len(self.image_paths)
        self._show_image()

    def _draw_gradient_bar(self, canvas: tk.Canvas) -> None:
        if not ACCENT_GRADIENT:
            return
        width = canvas.winfo_screenwidth()
        steps = len(ACCENT_GRADIENT)
        segment = max(1, int(width / steps))
        for idx, color in enumerate(ACCENT_GRADIENT):
            canvas.create_rectangle(
                idx * segment,
                0,
                (idx + 1) * segment,
                12,
                fill=color,
                outline="",
            )


def main() -> None:
    root = tk.Tk()
    app = ImageLabelerApp(root)
    if Image is None or ImageTk is None:
        return
    root.mainloop()


if __name__ == "__main__":
    main()
