import tkinter as tk
from tkinter import Canvas, Button
from PIL import Image, ImageTk
import cv2

from screenread import GameWindowHandler
from ocr_processor import OCRProcessor

class ScreenshotTool:
    def __init__(self, root, game_window_handler):
        self.root = root
        self.root.title("Screenshot Tool")

        self.game_window_handler = game_window_handler
        self.ocr = OCRProcessor(self.game_window_handler, 2)

        # Create buttons
        self.capture_button = Button(root, text="Capture New Screenshot", command=self.capture_new_screenshot)
        self.capture_button.pack()

        self.finish_button = Button(root, text="Finish", command=self.finish)
        self.finish_button.pack()

        # Create a canvas for displaying the screenshot
        self.canvas = Canvas(root)
        self.canvas.pack()

        # Variables for rectangle selection
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.h = None
        self.w = None

        # Capture the initial screenshot
        self.capture_new_screenshot()

    def capture_new_screenshot(self):
        self.screenshot = self.game_window_handler.capture_window()
        if self.screenshot is None:
            raise Exception("Failed to capture the game window")

        # Convert the screenshot to a format that tkinter can handle
        self.img = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(self.screenshot, cv2.COLOR_BGR2RGB)))
        self.h, self.w = self.screenshot.shape[:2] # type: ignore

        # Update the canvas
        self.canvas.config(width=self.img.width(), height=self.img.height())
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.img)

        # Bind mouse events to canvas
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

        # Create a rectangle if it doesn't exist
        if not self.rect:
            self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline='red')

    def on_mouse_drag(self, event):
        self.end_x, self.end_y = (event.x, event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, self.end_x, self.end_y)

    def on_button_release(self, event):
        self.end_x = event.x
        self.end_y = event.y
        self.log_coordinates()
        self.ocr_coordinates()

    def log_coordinates(self):
        print(f"Coordinates: ({self.start_x}, {self.end_x}), ({self.start_y}, {self.end_y})")

    def ocr_coordinates(self):
        roi = (self.start_x/self.w, self.end_x/self.w, self.start_y/self.h, self.end_y/self.h)
        ocr_data, roi_coords = self.ocr.perform_ocr_for_text(invert=True, roi=roi)
        print(roi, roi_coords)
        print(self.w, self.h)

        n_boxes = len(ocr_data['level'])
        for i in range(n_boxes):
            text = ocr_data['text'][i].strip()
            if len(text) > 2:
                print(text)
        self.save_roi()

    def save_roi(self):
        image = self.screenshot[round(self.start_y):round(self.end_y), round(self.start_x):round(self.end_x)]
        cv2.imwrite('test.png', image)

    def finish(self):
        self.root.quit()

if __name__ == "__main__":
    game_window_handler = GameWindowHandler()

    root = tk.Tk()
    app = ScreenshotTool(root, game_window_handler)
    root.mainloop()