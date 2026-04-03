import tkinter as tk
import tkinter.simpledialog as sd


class EditGroupNamesDialog(sd.Dialog):
    def __init__(self, parent, group_name_list):
        self.parent = parent
        # Ensure unique and sorted list
        self.glist = sorted(list(set(group_name_list))) if group_name_list else []
        self.gpn_textbox = None
        super().__init__(parent, "Edit Group Names")

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Ensure minimum size
        if width < 400: width = 400
        if height < 300: height = 300
        
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        self.minsize(400, 300)

    @staticmethod
    def format_names(glist):
        return "\n".join(map(str, glist)).strip()

    def allow_newline(self, event):
        """Allow the Enter key to insert a newline instead of triggering the default OK button."""
        self.gpn_textbox.insert("insert", "\n")
        return "break"

    def on_mousewheel(self, event):
        """Handle mousewheel scrolling for the text widget and prevent propagation."""
        if self.gpn_textbox:
            if event.num == 5 or (event.delta and event.delta < 0):
                self.gpn_textbox.yview_scroll(1, "units")
            elif event.num == 4 or (event.delta and event.delta > 0):
                self.gpn_textbox.yview_scroll(-1, "units")
        return "break"

    def body(self, master):
        # Create container frame for text and scrollbar
        container = tk.Frame(master)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        lbl_frame = tk.LabelFrame(container, text="Group Names")
        lbl_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = tk.Scrollbar(lbl_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Text Area
        self.gpn_textbox = tk.Text(lbl_frame, height=15, width=30, yscrollcommand=scrollbar.set)
        self.gpn_textbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.gpn_textbox.yview)

        # Insert content
        self.gpn_textbox.insert(tk.END, self.format_names(self.glist))

        # Bindings
        self.gpn_textbox.bind("<Return>", self.allow_newline)

        # Bind mousewheel events to the dialog window AND the text widget to catch all scrolling
        # and prevent it from propagating to the main window (which uses bind_all).
        self.bind("<MouseWheel>", self.on_mousewheel)
        self.bind("<Button-4>", self.on_mousewheel)
        self.bind("<Button-5>", self.on_mousewheel)
        
        self.gpn_textbox.bind("<MouseWheel>", self.on_mousewheel)
        self.gpn_textbox.bind("<Button-4>", self.on_mousewheel)
        self.gpn_textbox.bind("<Button-5>", self.on_mousewheel)

        # Center the dialog after creation
        self.center_window()

        return self.gpn_textbox # Initial focus

    def apply(self):
        """Process the data when the user clicks OK."""
        raw_text = self.gpn_textbox.get("1.0", tk.END)
        # Split lines and filter out empty strings
        lines = [line.strip() for line in raw_text.split('\n')]
        self.glist = sorted(list(set(line for line in lines if line)))


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Edit Group Names Test")
    
    # Setup test window size/position
    root.geometry("600x400")
    
    group_list = ['Group1', 'Group1', 'Group2', 'Group3', 'Group4', 'Group5']
    
    def open_dialog():
        dlg = EditGroupNamesDialog(root, group_list)
        print(f"Resulting Group List: {dlg.glist}")
        
    tk.Button(root, text="Open Dialog", command=open_dialog).pack(expand=True)
    
    root.mainloop()
