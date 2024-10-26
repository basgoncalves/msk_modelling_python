import tkinter as tk
import traceback

class Element:
        def __init__(self, root=None, type='', location=[], size=[], name="element", value=None, command=None, text=""):
           
            if not root:
                root = tk.Tk()
            
            if type == '':
                type = tk.Button(root, text=name)
                return
            
            self.name = name
            
            self.type = type
            
            
            try:
                self.type.config(command=command)
            except:
                print("Error: command could not added to type")
            try:
                self.type.config(text=text)
            except:
                print("Error: text could not added to type")
                
            try: 
                self.type.size = size
            except:
                print("Error: size could not added to type")
                
            self.type = type.__class__.__name__
            self.location = location
            self.size = size
            self.value = value
                 
        def delete(self):
            self.value.destroy()

        def change_command(self, command: callable):
            self.command = command
            print(f"Function added to {self.name}")
        
        def call_command(self):
            if self.command:
                self.command()
                
        def add_to_ui(self, root):
            self.type.pack()  # Adjust layout method as needed
            root.update()
            
class list:
        def __init__(self, elements: list = []):
            for _, element in enumerate(elements):
                setattr(self, element.name, element.value)

class GUI:
    def __init__(self, root="", elements_list: list = []):
        # if not window exists, create one
        if not root:
            root = tk.Tk()
        setattr(self, 'root', root)

        # Set the title of the window
        if not self.root.title():
            self.root.title("Major App GUI")
        
        # If elements are passed, add them to the GUI
        self.elements = []
        if len(elements_list)>0:
            for element in elements_list:
                setattr(self, element.name, element.command)
                element.type.pack()
                self.elements.append(element)

    def change_command(self, element, command):
        if type(element.type) is not tk.Button:
            print("Error: button is not a Button type")
        else:
            print("Button functionality changed!")
            element.type.config(command=command)
        return self

    def on_button_click(self, root):
        print("Button clicked!")
        close_button = tk.Button(root, text="Close", command=root.destroy)
        close_button.pack(pady=20)
    
    
    def add(self, element: Element):
        
        if element.lower() == 'button':
            element = Element(type=tk.Button(self.root, text="Click Me", command=lambda: self.on_button_click(self.root)))
        
        self.root.update()
        print(f"Element added to GUI: {element.name}")
        
        return element

    def get_elements(self):
        return self.elements
    
    def get_elements_names(self):
        return [element.name for element in self.elements]

    def change_size(self, width, height, unit="percent"):
        if unit == "inch":
            width_pixels = int(width * self.root.winfo_fpixels('1i'))
            height_pixels = int(height * self.root.winfo_fpixels('1i'))
        elif unit == "m":
            width_pixels = int(width * self.root.winfo_fpixels('1m'))
            height_pixels = int(height * self.root.winfo_fpixels('1m'))
        elif unit == "percent":
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            width_pixels = int(screen_width * width)
            height_pixels = int(screen_height * height)
        else:
            raise ValueError("Unsupported unit. Use 'inch', 'm', or 'percent'.")

        self.root.geometry(f"{width_pixels}x{height_pixels}")
    
    def start(self):
        # usage:
        #   ui = msk.ui.GUI() 
        #   ui.start()
        
        print("GUI started")
        pass

def main_gui(size_window= "800x600"):

    gui = GUI()
    gui.change_size(0.8, 0.6, "percent")
    
    
    gui.add("button")
    # gui.add("label", x=0.1, y=0.3, width=0.2, height=0.1, text="Let's start simulating!")
    
    # element = Element(type=tk.Button(gui.root, text="Close", command=gui.root.quit),
    #                   size=(0.2, 0.1), location=(0.1, 0.1), name="close")
    # close_button = gui.__add__(element)
    
    gui.start()
    
    return gui

def quit(self):
    self.quit()

def create():
    gui = main_gui()
    print("Generic UI created")
    return gui

def input_text_box(root, text=""):
    element = Element(type=tk.Entry(root))
    
    entry = tk.Entry(root)
    entry.pack()
    entry.insert(0, text)
    return entry

def select_from_list(options=[]):
    
    root = tk.Tk()
    root.withdraw()
    
    element = Element(type=tk.Listbox(root))
    listbox = tk.Listbox(root)
    listbox.pack()
    
    for option in options:
        listbox.insert(tk.END, option)
    
    return listbox

# Run when the module is called
if __name__ == "__main__":
    
    # test code 
    try:
        create()
        
        pass
    except Exception as e:
        print(f"An error occurred: {e}")
        raise e


# END