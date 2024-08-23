import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageTk

class ImageZoom(tk.Tk):
    def __init__(self, image_path):
        super().__init__()

        self.title("Image Zoom")
        self.geometry("800x600")
        
        self.canvas = Canvas(self, width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=tk.YES)

        # Load the image
        self.image = Image.open(image_path)
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        # Bind the mouse wheel to the zoom function
        self.canvas.bind("<MouseWheel>", self.zoom)

        # Set initial zoom level
        self.zoom_level = 1

    def zoom(self, event):
        # Determine the scale factor
        if event.delta > 0:
            self.zoom_level *= 1.1
        else:
            self.zoom_level /= 1.1

        # Resize the image
        new_size = (int(self.image.width * self.zoom_level), int(self.image.height * self.zoom_level))
        resized_image = self.image.resize(new_size, Image.ANTIALIAS)
        
        # Update the image on the canvas
        self.tk_image = ImageTk.PhotoImage(resized_image)
        self.canvas.itemconfig(self.image_id, image=self.tk_image)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

if __name__ == "__main__":
    # Path to your image
    image_path = "/mnt/machinelearning/Uniqorn/Jaguar/Images/1/AABP 7_20050913_1220.jpg"
    app = ImageZoom(image_path)
    app.mainloop()
