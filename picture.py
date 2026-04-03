import tkinter as tk
from tkinter import ttk, messagebox
import piexif
import re
from PIL import Image, ImageTk, ImageOps
from pathlib import Path
from typing import List, Optional, Union
from image_file_object import IFile
from config import YEAR_DATES, HOMEDIR

MAX_IMAGE_WIDTH = 470
MAX_IMAGE_HEIGHT = 270

RESIZE_VAL = 6
group_patterns = ['group-name']
DATE_MATCH_RE = re.compile(r"([12][0-9]+):([0-9]+):([0-9]+)")


class Picture(tk.Frame):
    def __init__(self, parent: tk.Widget, full_name_w_path: Union[str, Path], group_name: str = "group-name",
                 display_height: Optional[int] = None):
        super().__init__(parent)
        self.file_name = IFile(full_name_w_path)
        # Use IFile properties directly, removed redundant local paths
        self.group_name = group_name
        self.display_height = display_height

        self.image_create_year: Optional[str] = None
        self.image_create_month: str = ""
        self.image_create_day: str = ""
        self.rotation_angle: int = 0

        # This will hold the thumbnail image for display
        self.pil_thumbnail: Optional[Image.Image] = None

        # Hash for finding duplicates
        self.dhash_value: Optional[str] = None

        # Load image, extract info, generate thumbnail, and then release the full image
        self.load_and_process_initial_image()

        self.tk_image: Optional[ImageTk.PhotoImage] = None
        self.img_pict_label: Optional[tk.Label] = None
        self.img_order_number: Optional[tk.Entry] = None
        self.img_year: Optional[tk.Spinbox] = None
        self.image_group_name: Optional[ttk.Combobox] = None
        self.fullname_label: Optional[tk.Label] = None

        self.image_fullname_wo_ext = tk.StringVar(value=self.file_name.stem)

        self.name_frame = tk.Frame(self)

        self.sel_year = tk.IntVar(value=1990)
        self.sel_group_name = tk.StringVar(value="group-name")
        self.sel_image_order_number = tk.StringVar(value="00000")

        self.img_rotate_btn: Optional[tk.Button] = None

        self.checkbutton: Optional[tk.Checkbutton] = None
        self.CheckVar = tk.IntVar(value=0)
        self.config_image()

    def load_and_process_initial_image(self) -> None:
        try:
            with Image.open(self.file_name.filename_w_path) as full_img:
                self.extract_exif_data(full_img)
                # Bake orientation into a fresh image copy
                upright_img = ImageOps.exif_transpose(full_img)

                # Compute dHash
                self.dhash_value = self.compute_dhash(upright_img)

                # Generate thumbnail from the upright image
                self.pil_thumbnail = self.size_raw_image(upright_img)
        except IOError:
            print(f"file not found: {self.file_name.filename_w_path}")
            self.pil_thumbnail = None

    def extract_exif_data(self, img: Image.Image) -> None:
        if 'exif' not in img.info:
            return

        try:
            exif_dict = piexif.load(img.info['exif'])
        except (ValueError, TypeError) as e:
            print(f"Exif Error Ignore exif data: {self.file_name.stem}\n{e}")
            return

        for ifd in ("0th", "Exif", "GPS", "1st"):
            if ifd not in exif_dict: continue
            for tag in exif_dict[ifd]:
                if ifd not in piexif.TAGS or tag not in piexif.TAGS[ifd]:
                    continue
                tag_name = piexif.TAGS[ifd][tag]["name"]

                if tag_name in ('DateTime', 'DateTimeOriginal'):
                    val = exif_dict[ifd][tag]
                    if isinstance(val, bytes):
                        try:
                            val_str = val.decode('utf-8')
                        except Exception:
                            val_str = str(val)
                    else:
                        val_str = str(val)

                    if val_str and val_str.strip():
                        try:
                            date_time = self.get_date_parts(val_str.split()[0])
                            self.image_create_year = date_time[0]
                            self.image_create_month = date_time[1]
                            self.image_create_day = date_time[2]
                        except IndexError as e:
                            print(f"Failed to parse date from EXIF for {self.file_name.stem} with val_str {val_str}: {e}")
                        # Prefer DateTimeOriginal, but keep going
                        if tag_name == 'DateTimeOriginal':
                            pass  # We have what we need, but loop continues

    @staticmethod
    def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
        """
        Compute the difference hash (dHash) of an image.
        1. Resize to (width, height) = (hash_size + 1, hash_size).
        2. Convert to grayscale.
        3. Compare adjacent pixels.
        """
        try:
            # Resize to (width, height) = (hash_size + 1, hash_size)
            resized = image.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            # Convert to grayscale
            gray = resized.convert("L")

            pixels = list(gray.getdata())

            decimal_value = 0
            hex_string = []

            for row in range(hash_size):
                for col in range(hash_size):
                    pixel_left = pixels[row * (hash_size + 1) + col]
                    pixel_right = pixels[row * (hash_size + 1) + col + 1]
                    if pixel_left > pixel_right:
                        decimal_value |= 1 << (col % 8)

                # After each row (8 bits), append to hex string
                hex_string.append(f'{decimal_value:02x}')
                decimal_value = 0

            return "".join(hex_string)
        except Exception as e:
            print(f"Error computing dhash: {e}")
            return ""

    def config_image(self) -> None:
        if self.image_create_year:
            self.file_name.year = self.image_create_year

        if self.pil_thumbnail:
            self.tk_image = ImageTk.PhotoImage(self.pil_thumbnail)
        else:
            self.tk_image = None

        self.checkbutton = tk.Checkbutton(self.name_frame, text="", variable=self.CheckVar)

        # Create a container frame for the image to prevent layout shifts on rotation
        square_dim = self.display_height if self.display_height else MAX_IMAGE_HEIGHT
        if self.pil_thumbnail:
            square_dim = max(self.pil_thumbnail.size)

        self.img_container = tk.Frame(self, width=square_dim, height=square_dim)
        self.img_container.pack_propagate(False)  # Fixed size

        self.img_pict_label = tk.Label(self.img_container, image=self.tk_image, text=self.file_name.filename)
        self.img_pict_label.image = self.tk_image
        self.img_pict_label.bind('<ButtonPress-1>', self.selection_image)
        self.img_pict_label.place(relx=0.5, rely=0.5, anchor="center")

        self.fullname_label = tk.Label(self, textvariable=self.image_fullname_wo_ext)
        self.fullname_label.bind('<ButtonPress-1>', self.selection_name)

        self.img_order_number = tk.Entry(self.name_frame, width=6, textvariable=self.sel_image_order_number)
        self.img_year = tk.Spinbox(self.name_frame, values=self.get_date_set(), textvariable=self.sel_year, wrap=True)
        self.img_year.config(width=6)

        # Updated to Combobox to allow editing
        self.image_group_name = ttk.Combobox(self.name_frame, textvariable=self.sel_group_name, values=group_patterns)
        self.image_group_name.config(width=25)
        self.image_group_name.bind('<Enter>', self.update_combo)

        rotate_path = Path(__file__).parent / 'rotation.jpg'

        try:
            with Image.open(rotate_path) as rotate_image:
                rotate_btn = ImageTk.PhotoImage(rotate_image.resize((rotate_image.size[0] // 8, rotate_image.size[1] // 8),
                                                                    Image.Resampling.LANCZOS))
                self.img_rotate_btn = tk.Button(self.name_frame, width=30, image=rotate_btn, command=lambda: self.rotate(), pady=10)
                self.img_rotate_btn.image = rotate_btn
        except IOError:
            # Fallback text button if image missing
            self.img_rotate_btn = tk.Button(self.name_frame, text="Rotate", command=lambda: self.rotate(), pady=10)

        # Set values AFTER widget creation to prevent Spinbox reset bug
        if self.file_name.group_name:
            self.sel_group_name.set(self.file_name.group_name)
            self.add_group_name_list(self.file_name.group_name)

        if self.file_name.year:
            try:
                self.sel_year.set(int(self.file_name.year))
            except (ValueError, TypeError):
                # If year is not an integer (e.g. "0000" or garbage), default to 1990
                self.sel_year.set(1990)

        if self.file_name.order:
            self.sel_image_order_number.set(self.file_name.order)

        if self.img_container: self.img_container.pack(side="top")
        self.name_frame.pack(side="top")
        if self.checkbutton: self.checkbutton.pack(side="left")
        if self.image_group_name: self.image_group_name.pack(side="left")
        if self.img_year: self.img_year.pack(side="left")
        if self.img_order_number: self.img_order_number.pack(side="left")
        if self.img_rotate_btn: self.img_rotate_btn.pack(side="left")
        if self.fullname_label: self.fullname_label.pack(side="top")

    def update_combo(self, event=None) -> None:
        if event:
            pass
        if not self.image_group_name: return

        # With Combobox, we update 'values' instead of menu
        # And let's make sure we include the current value if it's new
        current = self.sel_group_name.get()
        combo_values = list(group_patterns)  # Copy
        if current and current not in combo_values:
            combo_values.append(current)
            combo_values.sort()

        self.image_group_name['values'] = combo_values

    def save_image(self) -> None:
        # Re-load from disk, apply ops, save, release
        try:
            exif_bytes = b""
            with Image.open(self.file_name.filename_w_path) as full_img:
                # 1. Bake orientation (removes orientation tag from EXIF)
                img_to_save = ImageOps.exif_transpose(full_img)

                # 2. Capture the clean EXIF from the transposed image
                # This ensures we have the metadata (date, etc) but NO orientation tag.
                exif_bytes = img_to_save.info.get('exif', b"")

                # 3. Apply manual rotation if any
                if self.rotation_angle != 0:
                    img_to_save = img_to_save.rotate(self.rotation_angle, expand=True)

                # Ensure we have a copy in memory and file is closed before saving
                img_to_save.load()

            # 4. Save with the captured EXIF bytes
            # Note: If rotate() preserved EXIF, passing it again is harmless.
            # If rotate() dropped it, we are restoring the one from exif_transpose.
            img_to_save.save(str(self.file_name.filename_w_path), "JPEG", exif=exif_bytes)
            # Reset rotation angle since we baked it in
            self.rotation_angle = 0

        except Exception as e:
            print(f"Failed to save image: {e}")
            messagebox.showerror("Save Error", f"Failed to save image {self.file_name.filename}:\n{e}")

    @staticmethod
    def add_group_name_list(group_str: str) -> None:
        if group_str not in group_patterns:
            group_patterns.append(group_str)

    @staticmethod
    def get_date_set() -> List[str]:
        return YEAR_DATES

    @staticmethod
    def get_group_set() -> List[str]:
        return group_patterns

    def size_raw_image(self, img: Image.Image) -> Image.Image:
        if not img: return img
        if self.display_height:
            h_percent = (self.display_height / float(img.size[1]))
            w_size = int((float(img.size[0]) * float(h_percent)))
            return img.resize((w_size, self.display_height), Image.Resampling.LANCZOS)
        return img.resize((img.size[0] // RESIZE_VAL, img.size[1] // RESIZE_VAL), Image.Resampling.LANCZOS)

    def selection_name(self, event) -> None:
        if event:
            pass
        if not self.fullname_label: return
        self.tkraise()

    def selection_image(self, evt) -> None:
        widget = evt.widget
        if widget.cget("text") != "":
            # print(f"Reloading Selected Image: {widget.cget('text')}")
            # For showing the image, we now need to re-load it temporarily
            try:
                with Image.open(self.file_name.filename_w_path) as full_img:
                    # Apply view transformations
                    view_img = ImageOps.exif_transpose(full_img)
                    if self.rotation_angle != 0:
                        view_img = view_img.rotate(self.rotation_angle, expand=True)
                    view_img.show()
            except IOError:
                pass

    def rotate(self) -> None:
        if not self.pil_thumbnail:
            return

        # Rotate the thumbnail in memory
        self.pil_thumbnail = self.pil_thumbnail.rotate(-90, expand=True)
        self.tk_image = ImageTk.PhotoImage(self.pil_thumbnail)

        if self.img_pict_label:
            self.img_pict_label.configure(image=self.tk_image)
            self.img_pict_label.image = self.tk_image

        # Accumulate the rotation angle for when we eventually save
        self.rotation_angle -= 90

    def rename_file(self) -> None:
        if self.CheckVar.get() == 1:
            group = self.sel_group_name.get()
            year = str(self.sel_year.get())
            order = self.sel_image_order_number.get()

            try:
                # Perform the rename on the file object
                self.file_name.update_and_rename(group, year, order)

                # Update UI elements
                self.image_fullname_wo_ext.set(self.file_name.stem)
                if self.img_pict_label:
                    self.img_pict_label.config(text=self.file_name.filename)
            except Exception as e:
                print(f"Error renaming {self.file_name.filename_w_path}: {e}")

    @staticmethod
    def get_date_parts(d: Union[str, bytes]) -> List[str]:
        if isinstance(d, bytes):
            try:
                d_str = d.decode('utf-8')
            except UnicodeDecodeError:
                d_str = str(d)
        else:
            d_str = str(d)

        m = DATE_MATCH_RE.match(d_str)
        if m:
            return [m.group(1), m.group(2), m.group(3)]
        else:
            return ["1990", "", ""]


if __name__ == '__main__':
    from pathlib import Path

    root = tk.Tk()
    test_path = Path(HOMEDIR) / "Desktop" / "test.jpg"
    image_frame = Picture(root, test_path)
    image_frame.pack()
    tk.mainloop()
