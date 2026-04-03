class ImageItem:
    def __init__(self, name):
        self.image_index = None
        self.image_name = name
        self.in_memory = False

    def get_in_memory(self):
        return self.in_memory

    def set_in_memory(self, value):
        self.in_memory = value

    def get_image_index(self):
        return self.image_index

    def set_image_index(self, value):
        self.image_index = value

    def get_image_name(self):
        return self.image_name


class ImageArray:
    def __init__(self):
        self.image_array = []       # List of ImageItem objects
        self.image_count = 0
        self.current_image_index = 0
        self.deleted = False

    def add_image_item(self, name):
        self.image_array.append(ImageItem(name))
        self.image_count += 1

    def delete_image_item(self, image_i):
        idx = image_i.image_index
        self.image_array.pop(idx)
        self.image_count -= 1
        # Update indices for all subsequent items
        for i in range(idx, len(self.image_array)):
            self.image_array[i].set_image_index(i)
