import re
import os
import filetype
from PIL import Image
from pathlib import Path
from typing import Optional, List, Union
from config import FILE_EXTENSION

NAME_MATCH_RE = re.compile(r"([a-zA-Z0-9 &_\-]+)-([012][0-9]{3})-([0-9]{5})(\.[jJ][pP][gG])")


class IFile:
    def __init__(self, file_path: Union[str, Path], order_number: int = 0, provisional_order: Optional[str] = None):
        if file_path is None:
            raise ValueError("File path cannot be None")

        self._full_filename_w_path = Path(file_path)
        self._order_number = order_number
        self._provisional_order = provisional_order
        self._group_name: Optional[str] = None
        self._year: Optional[str] = None
        self._order: Optional[str] = None
        self._extension: str = FILE_EXTENSION

        self._ensure_jpg_format()
        self._parse_name_components(self._full_filename_w_path.name)

    @property
    def filename_w_path(self) -> Path:
        return self._full_filename_w_path

    @filename_w_path.setter
    def filename_w_path(self, value: Union[str, Path]):
        self._full_filename_w_path = Path(value)
        # We might need to reparse components if path changes entirely,
        # but usually renames happen via update_and_rename. 
        # For simple setter, we assume just updating reference.

    @property
    def group_name(self) -> Optional[str]:
        return self._group_name

    @group_name.setter
    def group_name(self, value: str):
        self._group_name = value

    @property
    def year(self) -> Optional[str]:
        return self._year

    @year.setter
    def year(self, value: str):
        self._year = value

    @property
    def order(self) -> Optional[str]:
        return self._order

    @order.setter
    def order(self, value: str):
        self._order = value

    @property
    def extension(self) -> str:
        return self._full_filename_w_path.suffix

    @property
    def filename(self) -> str:
        """Return the filename with extension (e.g. image.jpg)."""
        return self._full_filename_w_path.name

    @property
    def stem(self) -> str:
        """Return the filename without extension."""
        return self._full_filename_w_path.stem

    @property
    def parent(self) -> Path:
        return self._full_filename_w_path.parent

    def _ensure_jpg_format(self) -> None:
        """Convert png/jpeg to jpg if necessary and update _file_path."""
        suffix = self._full_filename_w_path.suffix.lower()
        if suffix == '.png':
            self._convert_png_to_jpg()
        elif suffix == '.jpeg' or self._full_filename_w_path.suffix == '.JPG':
            self._rename_jpeg_to_jpg()

    def _convert_png_to_jpg(self):
        target = self._full_filename_w_path.with_suffix(FILE_EXTENSION)
        try:
            with Image.open(self._full_filename_w_path) as img:
                rgb_img = img.convert('RGB')
                rgb_img.save(target, 'JPEG')
                os.remove(self._full_filename_w_path)  # remove png
                self._full_filename_w_path = target
        except Exception as e:
            print(f"Error converting {self._full_filename_w_path} to JPEG: {e}")

    def _rename_jpeg_to_jpg(self):
        target = self._full_filename_w_path.with_suffix(FILE_EXTENSION)
        try:
            self._full_filename_w_path.rename(target)
            self._full_filename_w_path = target
        except Exception as e:
            print(f"Error renaming jpeg: {self._full_filename_w_path} with error: {e}")

    def _parse_name_components(self, fname: str) -> None:
        parts = self._get_name_parts(fname)
        self._group_name = parts[0]
        self._year = parts[1]
        self._order = parts[2]

    def _get_name_parts(self, ifname: str) -> List[str]:
        m = NAME_MATCH_RE.match(str(ifname))
        if m:
            return [m.group(1), m.group(2), m.group(3), ".jpg"]
        else:
            default_order = self._provisional_order if self._provisional_order else str(self._order_number)
            return ["group-name", "1990", default_order, FILE_EXTENSION]

    def construct_filename(self) -> str:
        return f"{self._group_name}-{self._year}-{self._order}{FILE_EXTENSION}"

    def update_and_rename(self, group: str, year: str, order: str) -> None:
        self._group_name = group
        self._year = year
        self._order = order

        new_filename = self.construct_filename()
        target = self._full_filename_w_path.with_name(new_filename)

        if target != self._full_filename_w_path:
            try:
                self._full_filename_w_path.rename(target)
                self._full_filename_w_path = target
            except Exception as e:
                print(f"Renamed failed: {e}: {self._full_filename_w_path.stem} was NOT Renamed to: {target.stem}")

    def __str__(self) -> str:
        return f"File: {self._full_filename_w_path} | Group: {self._group_name} | Year: {self._year} | Order: {self._order}"


if __name__ == "__main__":
    imgfile = IFile("group-name-1990-10000.jpg", 10001)
    print(f"TEST ONE: {imgfile}")
    print(f"File w/o Ext: {imgfile.stem}")
    imgfile_path = IFile("path/to/image_file_object.py")
    print(f"\nTEST TWO: {imgfile_path.filename_w_path}")
    print(f"File w/o Ext: {imgfile_path.stem}")
    p = Path(imgfile_path.filename_w_path)
    print(f"P name: {p.name}")
    print(f"P stem: {p.stem}")
    print(f"P parent: {p.parent}")
    print(f"P suffix: {p.suffix}")
