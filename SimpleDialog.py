import sys
import os

if sys.version_info[0] == 3:
#    pass
    import tkinter as tk
    import tkinter.ttk as ttk

else:
    #   noinspection PyPep8Naming
    import Tkinter as tk
    import ttk as ttk

#from Tkinter import *

#import tkFont
#import ttk

class Dialog(tk.Toplevel):
    def __init__(self, parent, title = None):
#        # type: (object, object) -> object

        tk.Toplevel.__init__(self, parent)
        self.transient(parent)

#        if title:
#            self.title(title)
        self.frame_height = "800"
        self.frame_width = "480"

        self.parent = parent

        self.result = None

        self.bind("<FocusIn>", self.dialog_got_focus)



     #   body = ttk.Frame(self, width=self.get_frame_width(), height=self.get_frame_height())
        self.body_frm = ttk.Frame(self)

        self.headerbox("None")

        self.initial_focus = self.body(self.body_frm)
        self.body_frm.pack(padx=1, pady=1)

        self.buttonbox()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.set_geometry(self)

        self.initial_focus.focus_set()
        self.lift()
        self.update_idletasks()
        self.wait_window(self)

    #
    # construction hooks
    def dialog_got_focus(self, event):
        pass

    def set_geometry(self, win):
        win.geometry("+%d+%d" % (win.parent.winfo_rootx() + 50,
                                  win.parent.winfo_rooty() + 50))

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden
        pass

    def headerbox(self, s):
        # box = ttk.Frame(self)
        # appDialogNameFont = tkFont.Font(family='Helvetica', size=16, weight='bold')
        # ttk.Label(box, text=self.e.getFullName(), font=appDialogNameFont).pack()
        pass

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons
        box = ttk.Frame(self)
        w = ttk.Button(box, text=self.get_apply_text(), width=10, command=self.apply)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = ttk.Button(box, text=self.get_cancel_text(), width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = ttk.Button(box, text=self.get_done_text(), width=self.get_done_width(), command=self.submit, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.submit)
        self.bind("<Escape>", self.cancel)
        box.pack()

    # standard button semantics
    @staticmethod
    def get_apply_text():
        return "Apply"

    @staticmethod
    def get_cancel_text():
        return "Cancel"

    @staticmethod
    def get_done_text():
        return "Done"

    @staticmethod
    def get_done_width():
        return 10

    def get_frame_height(self):
        return self.frame_height

    def get_frame_width(self):
        return self.frame_width

    def set_frame_width(self, w):
        self.frame = w

    def set_frame_height(self,h):
        self.frame = h

    def submit(self, event=None):
        if not self.validate():
            self.initial_focus.focus_set() # put focus back
            return
        self.withdraw()
        self.update_idletasks()
        self.apply()
        self.cancel()

    def cancel(self, event=None):
        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()
    #
    # command hooks

    @staticmethod
    def validate():
        return 1  # override

    @staticmethod
    def apply():
        pass  # override