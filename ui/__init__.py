import tkinter as tk
import traceback
class Element:
        def __init__(self, object=None, type='', location='', size='', name="element", value=None, command=None):
            self.name = name
            self.object = object
            self.object.command = command
            object.text = name
            self.type = object.__class__.__name__
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
            self.object.pack()  # Adjust layout method as needed
            root.update()
             
class list:
        def __init__(self, elements: list = []):
            for _, element in enumerate(elements):
                setattr(self, element.name, element.value)

class GUI:
    def __init__(self, root=tk.Tk(), elements_list: list = []):
        setattr(self, 'root', root)

        if not self.root.title():
            self.root.title("Major App GUI")
            
        self.elements = []
        if len(elements_list)>0:
            for element in elements_list:
                setattr(self, element.name, element.command)
                element.object.pack()
                self.elements.append(element)

    def change_command(self, element, command):
        if type(element.object) is not tk.Button:
            print("Error: button is not a Button object")
        else:
            print("Button functionality changed!")
            element.object.config(command=command)
        return self

    def __add__(self, element: Element):
        element.object.pack()  # Adjust layout method as needed
        self.root.update()

    def add(self, element_type, x, y, width, height, text="", command=None):
        print(type(element_type))
        if element_type == Element:
            tkObject = element_type
            tkObject.place(relx=x, rely=y, relwidth=width, relheight=height)
            
        elif element_type == "button":
            tkObject = tk.Button(self.root, text=text or "Button", command=command)
            tkObject.place(relx=x, rely=y, relwidth=width, relheight=height)

        elif element_type == "label":
            tkObject = tk.Label(self.root, text=text or "Label")
            tkObject.place(relx=x, rely=y, relwidth=width, relheight=height)

        elif element_type == "toggle":
            tkObject = tk.Checkbutton(self.root, text=text or "Toggle")
            tkObject.place(relx=x, rely=y, relwidth=width, relheight=height)
        # Add more element types as needed

        element = Element(element_type, (x, y), (width, height), text, command = command)
        GUI.__add__(self, element)
        self.elements.append(element)
        
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
        self.root.mainloop()

def main_gui(size_window= "800x600"):

    gui = GUI()
    gui.change_size(0.8, 0.6, "percent")
    gui.add("button", x=0.1, y=0.1, width=0.2, height=0.1, text="Click me!", command=lambda: print("Button clicked!"))
    gui.add("label", x=0.1, y=0.3, width=0.2, height=0.1, text="Let's start simulating!")
    # close_button = gui.add("button", x=0.1, y=0.5, width=0.2, height=0.1, text="Close", command=lambda: gui.root.quit())
    

    return gui


def quit(self):
    self.quit()

def run():
    print("Welcome to the major app!")
    gui = main_gui()
    gui.add("button", x=0.5, y=0.7, width=0.2, height=0.1, text="New button", command=lambda: print("New button clicked!"))
    gui.elements[-1].command.configure(command= quit)
    gui.root.mainloop()
    
    
# Run when the script is executed
if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"An error occurred: {e}")
        raise e


# END