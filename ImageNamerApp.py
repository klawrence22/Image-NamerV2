import tkinter as tk
from tkinter import ttk
import tkinter.filedialog
import tkinter.messagebox
import itertools
from pathlib import Path
from image_pages import Page
from editgroupnames import EditGroupNamesDialog
from picture import group_patterns, Picture
from config import RUN, si
from image_file_object import NAME_MATCH_RE


class DuplicateReviewDialog(tk.Toplevel):
    def __init__(self, parent, duplicate_groups, app=None):
        super().__init__(parent)
        self.app = app
        self.title("Review Duplicates")
        self.geometry("1600x800")
        self.duplicate_groups = duplicate_groups
        self.current_index = 0

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Main container
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)

        # Image area - scrollable in case of many duplicates? 
        # For now, just a frame, assuming 2-3 duplicates fit on screen.
        self.image_frame = ttk.Frame(self.container)
        self.image_frame.pack(fill="both", expand=True)

        # Navigation area
        self.nav_frame = ttk.Frame(self.container)
        self.nav_frame.pack(fill="x", pady=10)

        self.lbl_info = ttk.Label(self.nav_frame, text="")
        self.lbl_info.pack(side="left")

        self.btn_delete = ttk.Button(self.nav_frame, text="Delete Selected", command=self.delete_selected)
        self.btn_delete.pack(side="left", padx=20)

        self.btn_next = ttk.Button(self.nav_frame, text="Next", command=self.next_group)
        self.btn_next.pack(side="right")

        self.show_current_group()

    def show_current_group(self):
        # Clear existing images
        for widget in self.image_frame.winfo_children():
            widget.destroy()

        self.current_new_pics = []

        group = self.duplicate_groups[self.current_index]
        self.lbl_info.config(text=f"Group {self.current_index + 1} of {len(self.duplicate_groups)}")

        # Display images side-by-side
        for original_pic in group:
            # Create a new Picture instance for display
            # We pass self.image_frame as parent
            try:
                # We need to ensure we're passing the Path object
                fpath = original_pic.file_name.filename_w_path
                new_pic = Picture(self.image_frame, fpath, display_height=500)
                new_pic.pack(side="left", padx=10, pady=10)
                
                self.current_new_pics.append(new_pic)

                # Link check state
                # Initial state from original
                new_pic.CheckVar.set(original_pic.CheckVar.get())

                # Update original when this one is toggled
                def update_original(var_name, index, mode, orig=original_pic, new=new_pic):
                    orig.CheckVar.set(new.CheckVar.get())

                new_pic.CheckVar.trace_add("write", update_original)
            except Exception as e:
                print(f"Error displaying duplicate image: {e}")

        # Update button text
        if self.current_index == len(self.duplicate_groups) - 1:
            self.btn_next.config(text="Close", command=self.on_close)
        else:
            self.btn_next.config(text="Next", command=self.next_group)

    def next_group(self):
        self.current_index += 1
        if self.current_index < len(self.duplicate_groups):
            self.show_current_group()

    def delete_selected(self):
        pics_to_delete = [pic for pic in getattr(self, 'current_new_pics', []) if pic.CheckVar.get() == 1]

        if not pics_to_delete:
            tkinter.messagebox.showinfo("Info", "No images selected to delete.")
            return

        deleted_count = 0
        for pic in pics_to_delete:
            fpath = pic.file_name.filename_w_path
            filename = pic.file_name.filename

            msg = f"Are you sure you want to delete '{filename}'?\nThis action cannot be undone."
            if tkinter.messagebox.askyesno("Confirm Deletion", msg):
                try:
                    if fpath.exists():
                        fpath.unlink()
                        print(f"Deleted: {fpath}")
                        deleted_count += 1
                        if self.app:
                            self.app.needs_refresh = True
                    
                    # Remove from the dialog UI immediately
                    pic.destroy()
                    if pic in self.current_new_pics:
                        self.current_new_pics.remove(pic)
                except Exception as e:
                    print(f"Error deleting {fpath}: {e}")
                    tkinter.messagebox.showerror("Error", f"Failed to delete {filename}\n{e}")

    def on_close(self):
        if self.app and getattr(self.app, 'needs_refresh', False):
            self.app.load_images_from_current_dir()
            self.app.needs_refresh = False
        self.destroy()


class ImageNamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bulk Photo Rename Tool")
        self.root.geometry("2250x1200")

        if RUN == "dev":
            self.start_path = Path(si.dev_dir).parent
        else:
            self.start_path = Path(si.prod_dir).parent
        # self.start_path = Path(HOMEDIR) / "Dropbox" / "Z" / "Photos"
        self.image_extensions = ["*.jpg", "*.jpeg", "*.JPG", "*.JPEG", "*.png", "*.PNG"]
        self.page = None

        self.setup_ui()
        self.load_initial_images()

    def setup_ui(self):
        # Main layout
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True)

        main.columnconfigure(0, weight=0)  # command palette
        main.columnconfigure(1, weight=1)  # photo grid
        main.rowconfigure(0, weight=1)  # Allow row 0 to expand vertically

        ####################################
        # Command Palette (Left Side)
        ####################################

        palette = ttk.Frame(main, padding=10)
        palette.grid(row=0, column=0, sticky="ns")

        # IMAGE SELECTION
        selection_frame = ttk.LabelFrame(palette, text="Image Selection", padding=10)
        selection_frame.pack(fill="x", pady=5)

        ttk.Button(selection_frame, text="Select All", command=self.select_all).pack(fill="x", pady=2)
        ttk.Button(selection_frame, text="Clear Selected", command=self.clear_selected).pack(fill="x", pady=2)

        # GROUP
        group_frame = ttk.LabelFrame(palette, text="File Name Format", padding=10)
        group_frame.pack(fill="x", pady=5)

        ttk.Label(group_frame, text="Group Name").pack(anchor="w")

        self.use_global_group_name_var = tk.BooleanVar()
        group_frame.pack(pady=5)
        ttk.Checkbutton(group_frame, text="Use Global Group Name", variable=self.use_global_group_name_var).pack(pady=5)

        self.global_group_combo = ttk.Combobox(group_frame, values=group_patterns)
        self.global_group_combo.pack(fill="x", pady=2)
        if group_patterns:
            self.global_group_combo.current(0)

        ttk.Button(group_frame, text="Edit Groups", command=self.edit_groups).pack(fill="x", pady=2)

        # SEQUENCE

        start_frame = ttk.Frame(group_frame, padding=10)
        start_frame.pack(pady=5)
        ttk.Label(start_frame, text="Start Number").pack(side="left")
        self.start_entry = ttk.Entry(start_frame, width=10)
        self.start_entry.insert(0, "00001")
        self.start_entry.pack(side="right", padx=5)

        self.renumber_var = tk.BooleanVar()
        renumber_frame = ttk.Frame(group_frame, padding=10)
        renumber_frame.pack(pady=5)
        ttk.Checkbutton(renumber_frame, text="Renumber Existing Files", variable=self.renumber_var).pack(pady=5)

        # ACTIONS
        action_frame = ttk.LabelFrame(palette, text="Actions", padding=10)
        action_frame.pack(fill="x", pady=5)

        ttk.Button(action_frame, text="Rename Selected", command=self.rename_selected).pack(fill="x", pady=3)
        ttk.Button(action_frame, text="Delete Selected", command=self.delete_selected).pack(fill="x", pady=3)

        # UTILITIES
        util_frame = ttk.LabelFrame(palette, text="Utilities", padding=10)
        util_frame.pack(fill="x", pady=5)

        ttk.Button(util_frame, text="Refresh Images", command=self.load_images_from_current_dir).pack(fill="x", pady=2)
        ttk.Button(util_frame, text="Select Duplicates", command=self.select_duplicates).pack(fill="x", pady=2)
        ttk.Button(util_frame, text="Change Image Folder", command=self.change_image_folder).pack(fill="x", pady=2)

        # SAVE & EXIT
        save_exit_frame = ttk.Frame(palette, padding=10)
        save_exit_frame.pack(side="bottom", fill="x", pady=5)

        ttk.Button(save_exit_frame, text="Exit", command=self.root.destroy).pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(save_exit_frame, text="Save", command=self.rename_selected).pack(side="right", fill="x", expand=True, padx=2)

        ####################################
        # Photo Grid Area (Right Side)
        ####################################

        self.grid_area = ttk.Frame(main, padding=10)
        self.grid_area.grid(row=0, column=1, sticky="nsew")

        # We want the grid area to expand
        self.grid_area.columnconfigure(0, weight=1)
        self.grid_area.rowconfigure(0, weight=1)

    def load_initial_images(self):
        # Find test images
        # Asking for directory on startup might be annoying if it pops up every time during dev,
        # but preserving original logic.
        initial_dir = tkinter.filedialog.askdirectory(initialdir=self.start_path, title="Select Directory with Images")
        if initial_dir:
            self.load_images(Path(initial_dir))

    def change_image_folder(self):
        new_dir = tkinter.filedialog.askdirectory(initialdir=self.start_path, title="Select Directory with Images")
        if new_dir:
            self.load_images(Path(new_dir))

    def load_images_from_current_dir(self):
        if hasattr(self, 'current_image_dir') and self.current_image_dir:
            self.load_images(self.current_image_dir)

    def load_images(self, image_dir: Path):
        self.current_image_dir = image_dir
        # Combine multiple generators into one
        image_files = sorted(list(set(itertools.chain.from_iterable(image_dir.glob(ext) for ext in self.image_extensions))))

        max_seq = -1
        found_groups = set()
        
        self.used_sequences = set()
        self.provisional_orders = {}

        # First pass: find properly formatted files and max seq
        for f in image_files:
            m = NAME_MATCH_RE.match(f.name)
            if m:
                found_groups.add(m.group(1))
                try:
                    seq = int(m.group(3))
                    self.used_sequences.add(m.group(3))
                    if seq > max_seq:
                        max_seq = seq
                except ValueError:
                    pass

        # Update global group_patterns list with found groups
        for g in found_groups:
            if g not in group_patterns:
                group_patterns.append(g)

        group_patterns.sort()

        # Update the combobox values
        if hasattr(self, 'global_group_combo'):
            self.global_group_combo['values'] = group_patterns

        if max_seq == -1:
            next_start = 10000
        else:
            next_start = max_seq + 10

        # Second pass: assign provisional orders to unformatted files
        current_provisional_seq = next_start
        for f in image_files:
            m = NAME_MATCH_RE.match(f.name)
            if not m:
                # Find the next available sequence
                while f"{current_provisional_seq:05d}" in self.used_sequences:
                    current_provisional_seq += 10
                
                prov_str = f"{current_provisional_seq:05d}"
                self.provisional_orders[f] = prov_str
                self.used_sequences.add(prov_str)
                current_provisional_seq += 10

        self.start_entry.delete(0, tk.END)
        self.start_entry.insert(0, f"{current_provisional_seq:05d}")

        # Clear existing page if it exists
        if self.page:
            self.page.destroy()
            self.page = None
            # Also clear any labels in grid_area if they exist (like "No images found")
            for widget in self.grid_area.winfo_children():
                widget.destroy()

        if not image_files:
            # Fallback if no images found
            lbl = tk.Label(self.grid_area, text=f"No .jpg images found in {image_dir}")
            lbl.pack()
        else:
            # Instantiate the Page class
            self.page = Page(self.grid_area, image_files, rows=3, columns=4, provisional_orders=self.provisional_orders)
            # The Page is a Frame, so we grid it to fill the grid_area
            self.page.grid(row=0, column=0, sticky="nsew")

    def edit_groups(self):
        # Pass the current list to the dialog
        dlg = EditGroupNamesDialog(self.root, group_patterns)
        # The dialog is modal, so code resumes here after it closes

        # Update the global list in place so Picture objects see it
        if dlg.glist:
            # Filter out empty strings if any
            new_list = [g for g in dlg.glist if g.strip()]
            if new_list:
                # Update in place using slice assignment
                group_patterns[:] = new_list

            # Update the local combobox
            if hasattr(self, 'global_group_combo'):
                self.global_group_combo['values'] = group_patterns

    def select_all(self):
        if self.page:
            self.page.select_all()

    def clear_selected(self):
        if self.page:
            self.page.clear_selected()

    def rename_selected(self):
        if not self.page:
            return

        renumber = self.renumber_var.get()
        use_global_group = self.use_global_group_name_var.get()
        global_group_str = ""
        if use_global_group and hasattr(self, 'global_group_combo'):
            global_group_str = self.global_group_combo.get().strip()

        # Get start number for autofilling or renumbering
        try:
            current_seq = int(self.start_entry.get())
        except ValueError:
            current_seq = 10000

        seq_modified = False

        # First pass: Validation and Data Collection
        selected_pics = [p for p in self.page.pictures if p.CheckVar.get() == 1]
        if not selected_pics:
            return

        # Collision detection preparation
        proposed_names = set()
        
        for pic in selected_pics:
            if use_global_group:
                g_name = global_group_str
            else:
                g_name = pic.sel_group_name.get().strip()
            
            year = pic.sel_year.get()
            order = pic.sel_image_order_number.get().strip()
            
            # If renumbering or empty order, we'll assign one, so skip order validation
            if renumber or not order or order == '0':
                order = f"{current_seq:05d}"
                current_seq += 10
                seq_modified = True

            if not str(order).isdigit():
                tkinter.messagebox.showerror("Error", f"Invalid number format for {pic.file_name.filename}")
                return

            if not g_name:
                tkinter.messagebox.showerror("Error", f"Group Name is required for {pic.file_name.filename}\n(If using Global Group Name, ensure it is entered)")
                return

            # Simple year validation
            try:
                y = int(year)
                if y < 1900 or y > 2030: raise ValueError
            except:
                tkinter.messagebox.showerror("Error", f"Invalid year for {pic.file_name.filename}")
                return

            # Proposed filename check
            from config import FILE_EXTENSION
            proposed_filename = f"{g_name}-{year}-{order}{FILE_EXTENSION}"
            
            # Check if this rename conflicts with another file in the selection
            if proposed_filename in proposed_names:
                tkinter.messagebox.showerror("Error", f"Duplicate order numbers not allowed.\n\nMultiple images are trying to use the sequence '{order}'.")
                return
            proposed_names.add(proposed_filename)

            # Check if this rename conflicts with a file already on disk (that isn't this very file)
            target_path = pic.file_name.filename_w_path.with_name(proposed_filename)
            if target_path.exists() and target_path != pic.file_name.filename_w_path:
                tkinter.messagebox.showerror("Error", f"Duplicate order numbers not allowed.\n\nThe file '{proposed_filename}' already exists in this directory.")
                return

        # Second pass: Execution
        for pic in selected_pics:
            if use_global_group:
                g_name = global_group_str
                # Update the picture object's group name to reflect the global choice
                pic.sel_group_name.set(g_name)
            else:
                g_name = pic.sel_group_name.get().strip()
            
            # Add to global list if new
            if g_name and g_name not in group_patterns:
                group_patterns.append(g_name)
                group_patterns.sort()

            order = pic.sel_image_order_number.get().strip()

            # Apply Numbering Logic
            if renumber or not order or order == '0':
                # Re-calculate here since we just validated it works above
                order = f"{current_seq_exec:05d}" if 'current_seq_exec' in locals() else f"{int(self.start_entry.get()):05d}"
                if 'current_seq_exec' not in locals():
                    current_seq_exec = int(self.start_entry.get()) + 10
                else:
                    current_seq_exec += 10
                pic.sel_image_order_number.set(order)
            
            # Record it globally so next scan doesn't reuse it
            self.used_sequences.add(str(order))

            # Rename
            pic.rename_file()
            
            # Check for rotation and save if needed
            if pic.rotation_angle % 360 != 0:
                pic.save_image()
                
            pic.CheckVar.set(0)

        # Update global combo values if changed
        if hasattr(self, 'global_group_combo'):
            self.global_group_combo['values'] = group_patterns

        # Update start entry if we used the sequence
        if seq_modified:
            self.start_entry.delete(0, tk.END)
            self.start_entry.insert(0, f"{current_seq:05d}")

        # Always uncheck renumber after batch operation
        if renumber:
            self.renumber_var.set(False)

    def delete_selected(self):
        if not self.page:
            return

        pics_to_delete = [pic for pic in self.page.pictures if pic.CheckVar.get() == 1]

        if not pics_to_delete:
            tkinter.messagebox.showinfo("Info", "No images selected to delete.")
            return

        deleted_count = 0

        for pic in pics_to_delete:
            fpath = pic.file_name.filename_w_path
            filename = pic.file_name.filename

            msg = f"Are you sure you want to delete '{filename}'?\nThis action cannot be undone."
            if tkinter.messagebox.askyesno("Confirm Deletion", msg):
                try:
                    if fpath.exists():
                        fpath.unlink()
                        print(f"Deleted: {fpath}")
                        deleted_count += 1
                except Exception as e:
                    print(f"Error deleting {fpath}: {e}")
                    tkinter.messagebox.showerror("Error", f"Failed to delete {filename}\n{e}")

        if deleted_count > 0:
            # Refresh the view to show remaining images
            self.load_images_from_current_dir()

    def select_duplicates(self):
        if not self.page:
            return

        # Map to store hash -> list of pictures
        hash_map = {}

        # Reset selection first so user starts with a clean slate
        self.clear_selected()

        for pic in self.page.pictures:
            h = pic.dhash_value
            if h:
                if h in hash_map:
                    hash_map[h].append(pic)
                else:
                    hash_map[h] = [pic]

        # Filter groups with > 1 image
        duplicate_groups = [group for group in hash_map.values() if len(group) > 1]

        if duplicate_groups:
            DuplicateReviewDialog(self.root, duplicate_groups, app=self)
        else:
            tkinter.messagebox.showinfo("No Duplicates", "No duplicate images found based on visual hashing.")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageNamerApp(root)
    root.mainloop()
