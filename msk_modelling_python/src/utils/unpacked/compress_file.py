from PIL import Image
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilenames

def compress_tiff(filepath):
    im = Image.open(filepath)

    # Compress the image by saving it with a lower quality
    if extension == '.tiff':
        im.save((savedir + "\\" + filename + "_compressed" + extension), compression="tiff_lzw")
        

current_script_path = os.path.dirname(os.path.realpath(__file__)) 
filepaths = askopenfilenames(initialdir=current_script_path)

for i in range(len(filepaths)):
    current_file_path = filepaths[i]
    extension = os.path.splitext(current_file_path)[1]
    filename = os.path.basename(current_file_path).replace(extension,'')
    savedir = os.path.dirname(current_file_path)
    compress_tiff(current_file_path)