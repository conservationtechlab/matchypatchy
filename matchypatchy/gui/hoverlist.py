import tkinter as tk

class HoverListbox(tk.Listbox):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind('<Motion>', self.on_hover)
        self.bind('<Leave>', self.on_leave)
        self.current_selection = None

    def on_hover(self, event):
        # Get the index of the item under the cursor
        index = self.nearest(event.y)
        
        # If hovering over a new item, update the selection
        if self.current_selection != index:
            self.selection_clear(0, tk.END)
            self.selection_set(index)
            self.current_selection = index

    def on_leave(self, event):
        # Clear the selection when the cursor leaves the Listbox
        self.selection_clear(0, tk.END)
        self.current_selection = None
     
    #replace list   
    #def fill_options(self, event):

class HoverListboxApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Hover to Select Listbox")
        self.geometry("300x300")
        
        self.listbox = HoverListbox(self)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        
        # Add some items to the listbox
        items = ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"]
        for item in items:
            self.listbox.insert(tk.END, item)
        
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

    def on_select(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            value = widget.get(index)
            print(f"Selected: {value}")

if __name__ == "__main__":
    app = HoverListboxApp()
    app.mainloop()
