import math
import tkinter as tk
import os
from pathlib import Path
from typing import List, Union
from picture import Picture


class Page(tk.Frame):
    def __init__(self, parent: Union[tk.Widget, tk.Tk], image_paths: List[Path], rows: int = 3, columns: int = 4, provisional_orders: dict = None):
        super().__init__(parent)
        self.image_paths = image_paths
        self.rows = rows
        self.columns = columns
        self.provisional_orders = provisional_orders or {}

        self.active_widgets = {}  # (row, col) -> Picture
        self.free_pool = []  # List of inactive Picture objects
        self.valid_image_paths = []
        self.image_states = {}  # index -> state dict

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

        self.bind("<Enter>", self._bound_to_mousewheel)
        self.bind("<Leave>", self._unbound_to_mousewheel)

        # To track scroll events properly
        self.scrollbar.config(command=self._on_scrollbar)

        self.create_grid()

    @property
    def pictures(self) -> List[Picture]:
        # Return currently active pictures for ImageNamerApp compatibility
        return list(self.active_widgets.values())

    def select_all(self):
        for pic in self.active_widgets.values():
            pic.CheckVar.set(1)
        for state in self.image_states.values():
            state['checked'] = 1

    def clear_selected(self):
        for pic in self.active_widgets.values():
            pic.CheckVar.set(0)
        for state in self.image_states.values():
            state['checked'] = 0

    def _on_scrollbar(self, *args):
        self.canvas.yview(*args)
        self._check_scroll()

    def _bound_to_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)
        self.canvas.bind_all("<Up>", self._on_arrow)
        self.canvas.bind_all("<Down>", self._on_arrow)

    def _unbound_to_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")
        self.canvas.unbind_all("<Up>")
        self.canvas.unbind_all("<Down>")

    def _on_arrow(self, event):
        if event.keysym == 'Up':
            self.canvas.yview_scroll(-1, "units")
        elif event.keysym == 'Down':
            self.canvas.yview_scroll(1, "units")
        self._check_scroll()

    def on_frame_configure(self, event):
        if event:
            pass
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        if event:
            pass
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._check_scroll()

    def _on_mousewheel(self, event):
        try:
            widget = event.widget
            if not isinstance(widget, str):
                w_class = widget.winfo_class()
                if w_class == 'Listbox' or w_class == 'TCombobox':
                    return
        except Exception:
            pass

        if event.num == 5 or (event.delta and event.delta < 0):
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or (event.delta and event.delta > 0):
            self.canvas.yview_scroll(-1, "units")

        self._check_scroll()

    def _check_scroll(self):
        if not hasattr(self, 'total_rows') or self.total_rows == 0: return

        # Calculate current top visible row
        # canvas.yview()[0] gives the fraction of the top of the canvas
        y_fraction = self.canvas.yview()[0]
        visible_row_start = int(y_fraction * self.total_rows)
        self.update_cache(visible_row_start)

    @staticmethod
    def if_file_data_available_from_dropbox(file):
        try:
            if os.stat(file).st_size == 0:
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
        # 1. Filter valid images
        self.valid_image_paths = []
        for img_path in self.image_paths:
            if self.if_file_data_available_from_dropbox(img_path):
                self.valid_image_paths.append(img_path)

        self.total_images = len(self.valid_image_paths)
        if self.total_images == 0:
            return

        self.total_rows = math.ceil(self.total_images / self.columns)

        # 2. Setup Virtual Grid (fixed height per row)
        for r in range(self.total_rows):
            self.inner_frame.rowconfigure(r, minsize=320)

        # 3. Create pool of exactly min(total_images, 3 * rows * columns) Picture widgets
        pool_size = min(self.total_images, 3 * self.rows * self.columns)
        print(f"Creating pool of {pool_size} Picture widgets for virtualization...")

        for i in range(pool_size):
            # Bootstrap with the first image, but don't grid it
            prov_order = self.provisional_orders.get(self.valid_image_paths[0])
            pic = Picture(self.inner_frame, self.valid_image_paths[0], display_height=240, provisional_order=prov_order)
            pic.page_ref = self
            pic.current_image_index = 0
            self.free_pool.append(pic)

        # 4. Initial cache update
        self.update_cache(0)

        # Force an update so the canvas scrollregion picks up the virtual rows
        self.inner_frame.update_idletasks()
        self.canvas.configure(scrollregion=(0, 0, self.inner_frame.winfo_width(), self.total_rows * 320))

    def destroy(self):
        # Save any unsaved rotations of active widgets before destroying the page
        print("Page.destroy() called. Checking active widgets for pending rotations...")
        if hasattr(self, 'active_widgets'):
            for pic in list(self.active_widgets.values()):
                if pic.rotation_angle % 360 != 0:
                    try:
                        print(f"Saving rotation for active widget: {pic.file_name.filename}")
                        pic.save_image()
                    except Exception as e:
                        print(f"Failed to save rotation during page destroy: {e}")
        super().destroy()

    def update_cache(self, visible_row: int):
        cache_start = max(0, visible_row - self.rows)
        cache_end = min(self.total_rows, visible_row + 2 * self.rows)

        # Identify widgets to recycle
        to_recycle = []
        for (r, c), pic in list(self.active_widgets.items()):
            if r < cache_start or r >= cache_end:
                to_recycle.append((r, c))

        # Recycle
        for (r, c) in to_recycle:
            pic = self.active_widgets.pop((r, c))

            # Save rotation to disk before freeing the widget
            if getattr(pic, 'rotation_angle', 0) % 360 != 0:
                print(f"Evicting row {r}, col {c} - saving rotation for {pic.file_name.filename}")
                pic.save_image()

            pic.grid_remove()

            # Save state
            idx = r * self.columns + c
            self.image_states[idx] = {
                'checked': pic.CheckVar.get(),
                'group': pic.sel_group_name.get(),
                'year': pic.sel_year.get(),
                'order': pic.sel_image_order_number.get(),
                'dhash': pic.dhash_value
            }

            self.free_pool.append(pic)

        # Render new widgets
        for r in range(cache_start, cache_end):
            for c in range(self.columns):
                idx = r * self.columns + c
                if idx >= self.total_images:
                    break

                if (r, c) not in self.active_widgets:
                    if not self.free_pool:
                        print("Warning: Pool exhausted! This shouldn't happen with correct sizing.")
                        continue

                    cached_dhash = None
                    if idx in self.image_states:
                        cached_dhash = self.image_states[idx].get('dhash')

                    pic = self.free_pool.pop()
                    pic.page_ref = self
                    pic.current_image_index = idx
                    prov_order = self.provisional_orders.get(self.valid_image_paths[idx])
                    pic.load_new_image(self.valid_image_paths[idx], cached_dhash=cached_dhash, provisional_order=prov_order)

                    # Restore state if exists
                    if idx in self.image_states:
                        state = self.image_states[idx]
                        pic.CheckVar.set(state['checked'])
                        pic.sel_group_name.set(state['group'])
                        pic.sel_year.set(state['year'])
                        pic.sel_image_order_number.set(state['order'])

                    pic.grid(row=r, column=c, padx=5, pady=5)
                    self.active_widgets[(r, c)] = pic
