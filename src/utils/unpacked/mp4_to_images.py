
import cv2
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename

def getFrame(sec):
    vidcap.set(cv2.CAP_PROP_POS_MSEC,sec*1000)
    hasFrames,image = vidcap.read()
    save_folder = (video_dir + "\\" + video_name)
    
    if not os.path.isdir(save_folder):          # create a folder for the new images
        os.mkdir(save_folder)
    
    if hasFrames:
        cv2.imwrite(save_folder + "\\image" + str(count) + ".jpg", image)     # save frame as JPG file
    return hasFrames


current_script_path = os.path.dirname(os.path.realpath(__file__)) 
video_path = askopenfilename(initialdir=current_script_path)
extension = os.path.splitext(video_path)[1]
video_name = os.path.basename(video_path).replace(extension,'')
video_dir = os.path.dirname(video_path)

vidcap = cv2.VideoCapture(video_path)

sec = 0
frameRate = 0.5 #//it will capture image in each 0.5 second
count=1
success = getFrame(sec)

while success:
    count = count + 1
    sec = sec + frameRate
    sec = round(sec, 2)
    success = getFrame(sec)
