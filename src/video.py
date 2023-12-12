import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import cv2

class VideoPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Player")

        self.video_frame = ttk.LabelFrame(self.root, text="Video")
        self.video_frame.grid(row=0, column=0, padx=10, pady=10)

        self.play_button = ttk.Button(self.root, text="Play", command=self.play_video)
        self.play_button.grid(row=1, column=0, padx=10, pady=10)

        self.video_path = None
        self.video_capture = None
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.grid(row=0, column=0)

        self.isPlaying = False

    def play_video(self):
        if not self.isPlaying:
            if not self.video_path:
                messagebox.showerror("Error", "No video selected. Please choose a video.")
                return

            self.video_capture = cv2.VideoCapture(self.video_path)
            self.isPlaying = True

        ret, frame = self.video_capture.read()
        if ret:
            self.update_video_frame(frame)
            self.root.after(10, self.play_video)
        else:
            self.isPlaying = False
            self.video_capture.release()

    def update_video_frame(self, frame):
        if frame is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = Image.fromarray(frame)
            frame = ImageTk.PhotoImage(frame)
            self.video_label.config(image=frame)
            self.video_label.image = frame
        else:
            messagebox.showerror("Error", "Error reading frame from video.")

    def select_video_file(self):
        self.video_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mkv *.mov *.mpg")])

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoPlayerApp(root)

    select_video_button = ttk.Button(root, text="Select Video", command=app.select_video_file)
    select_video_button.grid(row=2, column=0, padx=10, pady=10)

    root.mainloop()
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk

class VideoPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Player")

        self.video_frame = ttk.LabelFrame(self.root, text="Video")
        self.video_frame.grid(row=0, column=0, padx=10, pady=10)

        self.play_button = ttk.Button(self.root, text="Play", command=self.play_video)
        self.play_button.grid(row=1, column=0, padx=10, pady=10)

        self.video_path = None
        self.video_capture = None
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.grid(row=0, column=0)

        self.isPlaying = False

    def play_video(self):
        if not self.isPlaying:
            if not self.video_path:
                messagebox.showerror("Error", "No video selected. Please choose a video.")
                return

            self.video_capture = cv2.VideoCapture(self.video_path)
            self.isPlaying = True

        ret, frame = self.video_capture.read()
        if ret:
            self.update_video_frame(frame)
            self.root.after(10, self.play_video)
        else:
            self.isPlaying = False
            self.video_capture.release()

    def update_video_frame(self, frame):
        if frame is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = Image.fromarray(frame)
            frame = ImageTk.PhotoImage(frame)
            self.video_label.config(image=frame)
            self.video_label.image = frame
        else:
            messagebox.showerror("Error", "Error reading frame from video.")

    def select_video_file(self):
        self.video_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mkv *.mov *.mpg")])

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoPlayerApp(root)

    select_video_button = ttk.Button(root, text="Select Video", command=app.select_video_file)
    select_video_button.grid(row=2, column=0, padx=10, pady=10)

    root.mainloop()
