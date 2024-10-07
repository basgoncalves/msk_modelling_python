#%% import libraries
import tkinter as tk
from msk_modelling_python.ui import *

#%% Functions
def on_button_click(root):
    print("Button clicked!")
    close_button = tk.Button(root, text="Close", command=root.destroy)
    close_button.pack(pady=20)

def change_button_functionality(button):
    if type(button) is not tk.Button:
        print("Error: button is not a Button object")
    else:
        print("Button functionality changed!")
        button.config(command=lambda: print("New functionality!"))
    
#%% Test create UI
def create_ui():
    # Create the main window
    root = tk.Tk()
    root.title("Basic UI")

    # Create a button and add it to the window
    button = tk.Button(root, text="Click Me", command=lambda: on_button_click(root))
    button.pack(pady=20)
    
    button2 = 'test'
    button_change = tk.Button(root, text="Change functionality", command=lambda: change_button_functionality(button2))
    button_change.pack(pady=20)

    # Start the Tkinter event loop
    root.mainloop()
# create_ui()   



#%% Test create UI with Element class
# Create the main window
root = tk.Tk()
gui = GUI(root) # Create GUI object
# Create a button and add it to the window
button = Element(object=tk.Button(gui.root, text="Click Me", command=lambda: on_button_click(gui.root)))

# Add button to GUI
print(button.object.pack())

# Add button to GUI
gui.start()
exit()

gui.add(button, x=50, y=50, width=100, height=50)


# %%
