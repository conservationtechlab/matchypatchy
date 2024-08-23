import tkinter as tk
from PIL import Image, ImageTk
from .hoverlist import HoverListbox


class DisplayComparison:
    def __init__(self, master):
        self.master = master
        self.master.title("Image Display")
        
        
        self.master.columnconfigure([0,1,2], minsize=100)
        self.master.rowconfigure(0, minsize=400)



        '''
        CREATE IMAGE WINDOW CLASS
        # Load images
        self.image1 = Image.open("/mnt/machinelearning/Uniqorn/Jaguar/Images/1/AABP 7_20050913_1220.jpg")  # Change "image1.jpg" to your first image file path
        self.image2 = Image.open("/mnt/machinelearning/Uniqorn/Jaguar/Images/1/AABP 9_20051024_0559.jpg")  # Change "image2.jpg" to your second image file path

        # Resize images to fit the window
        width, height = self.image1.size
        new_width = width // 2  # Resize to half width
        new_height = height // 2  # Resize to half height
        self.image1 = self.image1.resize((new_width, new_height))
        self.image2 = self.image2.resize((new_width, new_height))

        # Convert images to Tkinter PhotoImage objects
        self.photo1 = ImageTk.PhotoImage(self.image1)
        self.photo2 = ImageTk.PhotoImage(self.image2)
        '''
        
        # Create labels to display images
        self.label1 = tk.Label(self.master, text="Query")
        self.label2 = tk.Label(self.master, text="Match")
        # Place labels on the window
        self.label1.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.label2.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")


        self.listbox = HoverListbox(self.master)
        #self.listbox.pack(fill=tk.BOTH, expand=True)
                # Add some items to the listbox
        items = ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"]
        for item in items:
            self.listbox.insert(tk.END, item)
            
        self.listbox.grid(row=0, column=2, padx=5, pady=5, sticky="ns")
        
         # Create buttons
        self.button1 = tk.Button(self.master, text="Button 1", command=self.button1_action)
        self.button2 = tk.Button(self.master, text="Button 2", command=self.button2_action)
        self.button3 = tk.Button(self.master, text="Button 3", command=self.button3_action)

        # Place buttons on the window
        self.button1.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.button2.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.button3.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

    def button1_action(self):
        # Define the action for Button 1
        print("Button 1 clicked")

    def button2_action(self):
        # Define the action for Button 2
        print("Button 2 clicked")

    def button3_action(self):
        # Define the action for Button 3
        print("Button 3 clicked")
        

def main():
    image_path1 = "/mnt/machinelearning/Uniqorn/Jaguar/Images/1/AABP 7_20050913_1220.jpg"
    image_path2 = "/mnt/machinelearning/Uniqorn/Jaguar/Images/1/AABP 9_20051024_0559.jpg"
    root = tk.Tk()
    app = DisplayComparison(root)
    root.mainloop()

if __name__ == "__main__":
    main()