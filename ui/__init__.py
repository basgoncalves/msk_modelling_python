import tkinter as tk

def add_function(self, func):
    self.func = func
    return self

class GUI:
    
    class Element:
        def __init__(self, element_type, location, size):
            self.element_type = element_type
            self.location = location
            self.size = size

        def delete(self):
            for element in self.root.winfo_children():
                if element.winfo_class() == self.element_type and element.winfo_x() == self.location[0] and element.winfo_y() == self.location[1]:
                    element.destroy()
                    self.root.update()
                    break 

    class list:
                   
        def __init__(self, elements: list = []):
            for _, element in enumerate(elements):
                setattr(self, element.name, element.value)
                
        def __add__(self, element: Element):
            setattr(self, element.name, element.value)
        
        def delete_list(self, elements):
            if elements == "all":
                elements = range(len(self.elements))
            elif type(elements) == int:
                elements = [elements]
                
            for element, index in enumerate(elements):
                element = self.elements[index]
                element.delete()

        def get_elements(self):
            return self.elements
                
    def __init__(self, root=tk.Tk()):
        setattr(self, 'root', root)
        
        if not self.root.title():
            self.root.title("Major App GUI")
        self.elements = []

    def add(self, element_type, x, y, width, height, text="", command=None):
        if element_type == "button":
            button = tk.Button(self.root, text=text or "Button", command=command)
            button.place(relx=x, rely=y, relwidth=width, relheight=height)
            self.elements.append(button)
        elif element_type == "label":
            label = tk.Label(self.root, text=text or "Label")
            label.place(relx=x, rely=y, relwidth=width, relheight=height)
            self.elements.append(label)
        
        return 
        # Add more element types as needed

    def get_elements(self):
        return [self.object(element.winfo_class(), (element.winfo_x(), element.winfo_y()), (element.winfo_width(), element.winfo_height())) for element in self.elements]

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

def main_gui(size_window= "800x600"):
    
    gui = GUI()
    gui.change_size(0.8, 0.6, "percent")
    gui.add("button", x=0.1, y=0.1, width=0.2, height=0.1, text="Click me!", command=lambda: print("Button clicked!"))
    gui.add("label", x=0.1, y=0.3, width=0.2, height=0.1, text="Let's start simulating!")
    close_button = gui.add("button", x=0.1, y=0.5, width=0.2, height=0.1, text="Close")
    close_button.add_function(lambda: gui.root.quit())

    gui.root.mainloop()
    
    

def run():
    main_gui()
    print("Welcome to the major app!")
    
if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"An error occurred: {e}")
        raise e
