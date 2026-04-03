import tkinter as tk
import os
from pathlib import Path
from typing import List, Union
from picture import Picture


class Page(tk.Frame):
    def __init__(self, parent: Union[tk.Widget, tk.Tk], image_paths: List[Path], rows: int = 3, columns: int = 4):
        super().__init__(parent)
        self.image_paths = image_paths
        self.rows = rows
        self.columns = columns
        self.pictures: List[Picture] = []

        # Create a canvas and scrollbar
        self.canvas = tk.Canvas(self, borderwidth=0, background="#ffffff")
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Create a frame inside the canvas to hold the grid
        self.inner_frame = tk.Frame(self.canvas, background="#ffffff")
        self.canvas_window = self.canvas.create_window((4, 4), window=self.inner_frame, anchor="nw", tags="self.inner_frame")

        self.inner_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        # Bind mousewheel for scrolling only when mouse is over the widget
        self.bind("<Enter>", self._bound_to_mousewheel)
        self.bind("<Leave>", self._unbound_to_mousewheel)

        self.create_grid()

    def _bound_to_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbound_to_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def on_frame_configure(self, event):
        if event:
            pass
        """Reset the scroll region to encompass the inner frame"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        if event:
            pass
        """When canvas is resized, resize the inner frame to match width (optional, mostly for full-width lists)"""
        # For a grid, we might not want to force width, but let it grow naturally.
        # However, updating scrollregion is critical.
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        # Prevent scrolling the canvas if the mouse is over a Combobox dropdown
        # (which uses a Listbox) or the Combobox itself.
        try:
            widget = event.widget
            # If widget is a string (rare but possible in some Tk versions/contexts), ignore class check
            if not isinstance(widget, str):
                w_class = widget.winfo_class()
                # 'Listbox' is used by Combobox dropdowns. 'TCombobox' is the box itself.
                if w_class == 'Listbox' or w_class == 'TCombobox':
                    return
        except Exception:
            pass

        if event.num == 5 or (event.delta and event.delta < 0):
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or (event.delta and event.delta > 0):
            self.canvas.yview_scroll(-1, "units")

    @staticmethod
    def if_file_data_available_from_dropbox(file):
        try:
            if os.stat(file).st_size == 0:
                # print(f"File: {file} is empty")
                return False
        except FileNotFoundError:
            try:
                if os.stat(f"{file.stem}.jpg").st_size == 0:
                    return False
            except FileNotFoundError:
                print(f"File listed but not found by App: {file.stem} .png or .jpg")
                return False
        return True

    def create_grid(self):
        # Clear existing pictures if any
        for pic in self.pictures:
            pic.destroy()
        self.pictures = []

        # We will display ALL images, arranging them in the specified number of columns.
        total_images_available = 0
        for i, img_path in enumerate(self.image_paths):
            if not self.if_file_data_available_from_dropbox(img_path):
                continue

            # Calculate row and column
            r = total_images_available // self.columns
            c = total_images_available % self.columns
            print(".", end="\n" if (total_images_available + 1) % 25 == 0 else "")

            # Create Picture instance attached to the inner_frame
            pic = Picture(self.inner_frame, img_path, display_height=240)
            pic.grid(row=r, column=c, padx=5, pady=5)
            self.pictures.append(pic)
            total_images_available += 1

        # Update scrollregion immediately after creation
        self.inner_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Image Grid Test")

    # Set a reasonable default size
    root.geometry("1700x900")

    # Setup test images path
    current_dir = Path(__file__).parent
    image_dir = current_dir / "images"
    # Get all jpg images
    image_files: List[Path] = sorted(list(image_dir.glob("*.jpg")))

    if not image_files:
        print(f"No .jpg images found in {image_dir}")
        lbl = tk.Label(root, text=f"No .jpg images found in {image_dir}")
        lbl.pack()
    else:
        print(f"Found {len(image_files)} images.")
        # Create Page
        # We pass all files. With 31 images and 4 columns, we expect ~8 rows.
        # This will easily demonstrate the scrollbar.
        page = Page(root, image_files, rows=3, columns=4)
        page.pack(fill="both", expand=True)

    root.mainloop()
