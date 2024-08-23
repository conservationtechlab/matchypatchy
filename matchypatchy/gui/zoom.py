import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageTk

class ImageBox(tk.Tk):
    def __init__(self, image_path):
        super().__init__()

        self.title("Image Zoom")
        self.geometry("1600x800")

        # Create a frame to hold the canvases side by side
        self.frame = tk.Frame(self)
        self.frame.pack(fill=tk.BOTH, expand=tk.YES)

        # Create canvases for both images
        self.canvas1 = Canvas(self.frame, width=800, height=800)
        self.canvas1.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

        # Load the images
        self.image = Image.open(image_path)
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.image_id1 = self.canvas1.create_image(0, 0, anchor=tk.NW, image=self.tk_image1)


        # Bind the mouse wheel to the zoom function
        self.canvas1.bind("<MouseWheel>", self.zoom1)
        self.canvas2.bind("<MouseWheel>", self.zoom2)

        # Set initial zoom levels
        self.zoom_level1 = 1

    def zoom(self, event):
        # Determine the scale factor for the first image
        if event.delta > 0:
            self.zoom_level1 *= 1.1
        else:
            self.zoom_level1 /= 1.1

        # Resize the first image
        new_size1 = (int(self.image1.width * self.zoom_level1), int(self.image1.height * self.zoom_level1))
        resized_image1 = self.image1.resize(new_size1, Image.ANTIALIAS)
        
        # Update the first image on the canvas
        self.tk_image1 = ImageTk.PhotoImage(resized_image1)
        self.canvas1.itemconfig(self.image_id1, image=self.tk_image1)
        self.canvas1.config(scrollregion=self.canvas1.bbox(tk.ALL))
