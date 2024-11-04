import os
import tkinter as tk
import customtkinter as ctk
import screeninfo as si
from tkinter import messagebox
from msk_modelling_python.src.bops import bops, osim

class Element:
        def __init__(self, root=None, type='', location=[], size=[], name="element", value=None, command=None, text=""):
           
            if not root:
                root = tk.Tk()
            
            if type == '':
                type = tk.Button(root, text=name)
                print("Type not specified, defaulting to Button")
            elif type == 'button':
                type = tk.Button(root, text=name)
            elif type == 'label':
                type = tk.Label(root, text=name)
            elif type == 'entry':
                type = tk.Entry(root)
            elif type == 'listbox':
                type = tk.Listbox(root)
            elif type == 'text':
                type = tk.Text(root)
            elif type == 'canvas':
                type = tk.Canvas(root)
            elif type == 'frame':
                type = tk.Frame(root)
            elif type == 'menu':
                type = tk.Menu(root)
            elif type == 'menubutton':
                type = tk.Menubutton(root)
            elif type == 'message':
                type = tk.Message(root)
            elif type == 'radiobutton':
                type = tk.Radiobutton(root)
            else:
                print("Error: type not recognized")
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
                
            self.location = location
            self.size = size
            self.value = value
                 
        def delete(self):
            self.value.destroy()

        def change_command(self, command: callable):
            self.command = command
            print(f"Function added to {self.name}")
        
        def call_command(self):
            # ugage:
            #   element = Element()
            #   element.change_command(lambda: print("Hello"))
            #   element.call_command()
            
            if self.command:
                self.command()
                
        def add_to_ui(self, root):
            self.type.pack()  # Adjust layout method as needed
            root.update()
            
class ElementList:
        def __init__(self, elements: list = []):
            for _, element in enumerate(elements):
                setattr(self, element.name, element.value)

class GUI:
    def __init__(self, root="", list_of_elements: list = []):
        # if not window exists, create one
        if not root:
            root = tk.Tk()
        setattr(self, 'root', root)

        # Set the title of the window
        if not self.root.title():
            self.root.title("Major App GUI")
        
        # If elements are passed, add them to the GUI
        self.elements = []
        if len(list_of_elements)>0:
            for element in list_of_elements:
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
        
        if isinstance(element, Element):
            element.add_to_ui(self.root)
        elif isinstance(element, str):
            element = Element(type=element, command=lambda: self.on_button_click(self.root))
            element.add_to_ui(self.root)
            
        else:
            print(f"Error: Unsupported element type '{element}'")
            return
        
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
        self.root.mainloop()
        print("GUI started")
        pass
    
    def quit(self):
        self.root.quit()

#%% OpenSim GUI
class App(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.title("Opensim Analysis Tool")
            
    def pack_objects(self):
        try: 
            self.label.pack(padx=10, pady=10)
            self.model_label.pack(padx=10, pady=10)
            self.model.pack(padx=10, pady=10)
            self.input_label.pack(padx=10, pady=10)
            self.input.pack(padx=10, pady=10)
            self.button_run.pack(padx=10, pady=10)
            self.button_open.pack(padx=10, pady=10)
            self.button_quit.pack(padx=10, pady=10)
        except:
            print("Error: Could not pack objects")
                
    # function to add elements to the GUI
    def add(self, type = 'osim_input', prompt = '', osim_model = False, setup_path = ''):
        
        if type == 'label':
            self.label = ctk.CTkLabel(self, text='label')
            self.label.pack(padx=10, pady=10)
        elif type == 'button':
            self.button = ctk.CTkButton(self, text='button', command=self.run_system_deault)
            self.button.pack(padx=10, pady=10)
        
        # Input for an analysis tool of opensim    
        elif type == 'osim_input':
            # prompt label
            self.label = ctk.CTkLabel(self, text=prompt)          
            
            # input field for osim model
            if osim_model:
                self.model_label = ctk.CTkLabel(self, text="Model path:")
                self.model = ctk.CTkEntry(self)
                self.model.insert(0, osim_model)
        
            # input field for setup file
            self.input_label = ctk.CTkLabel(self, text="Setup file path:")
            self.input = ctk.CTkEntry(self)   
            self.input.insert(0, setup_path)
            
            # run button
            self.button_run = ctk.CTkButton(self, text='Run', command=self.run_osim_setup)
            
            # osim setup edit button
            self.button_open = ctk.CTkButton(self, text="Edit setup", command=self.edit_setup_file)

            # pack all objects            
            self.pack_objects()
        
        # exit button
        elif type == 'exit_button':
            self.button_quit = ctk.CTkButton(self, text="Quit", command=self.quit)
            self.button_quit.pack(padx=10, pady=10)
        
        else:
            print("Error: no valid input")
        
            
            
    def run_system_deault(self):
        if not os.path.exists(self.input.get()):
            print("Error: file does not exist")
            return
        os.system(self.input.get())
    
        
    def run_osim_setup(self):       
        if not os.path.isfile(self.input.get()):
            print("Error: file does not exist")
            return
                
        if bops.is_ik_setup(self.input.get(), print_output=True):
            model = osim.Model(self.model.get())
            tool = osim.InverseKinematicsTool(self.input.get())
            tool.setModel(model)
            
            tool.run()
        else:
            print("Error: file is not a valid setup file")
            print("XML file must contain the following tags:")
            print("<InverseKinematicsTool>")
    
    # function to open the setup XML in the system default editor
    def edit_setup_file(self):
        if not os.path.exists(self.input.get()):
            print("Error: file does not exist")
            return
        os.system(self.input.get())  

    
    # function to autoscale the window to fit all elements
    def autoscale(self, centered=True):
        self.update_idletasks()
        self.geometry(f"{self.winfo_reqwidth()}x{self.winfo_reqheight()}")
        if centered:
            self.center()

    # function to center the window on the screen 
    def center(self):
        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    # function to start the GUI
    def start(self):
        self.mainloop()

# function to run the example        
def run_example():
    app = App()
    
    # example data path for walking trial 1
    trial_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "example_data", "walking", "trial1")
    
    # add IK button
    setup_file = os.path.join(trial_path, "setup_ik.xml")
    osim_model = os.path.join(os.path.dirname(trial_path), "torsion_scaled.osim")
    app.add(type = 'osim_input', prompt = 'Run Inverse Kinematics:', osim_model = osim_model, setup_path = setup_file)
    
    # add ID button
    setup_file = os.path.join(trial_path, "setup_id.xml")
    app.add(type = 'osim_input', prompt = 'Run Inverse Dynamics:', osim_model = False, setup_path = setup_file)
    
    # add exit button
    app.add(type = 'exit_button')
    
    app.autoscale()
    
    app.start()    
    
    return app

#%%
def complex_gui():
    ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

    class App(ctk.CTk):
        def __init__(self):
            super().__init__()

            # configure window
            self.title("Select subjects")
            self.geometry(f"{1100}x{580}")

            # configure grid layout (4x4)
            self.grid_columnconfigure(1, weight=1)
            self.grid_columnconfigure((2, 3), weight=0)
            self.grid_rowconfigure((0, 1, 2), weight=1)

            # create sidebar frame with widgets
            self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
            self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
            self.sidebar_frame.grid_rowconfigure(4, weight=1)
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="ctk", font=ctk.CTkFont(size=20, weight="bold"))
            self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
            self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, command=self.sidebar_button_event)
            self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)
            self.sidebar_button_2 = ctk.CTkButton(self.sidebar_frame, command=self.sidebar_button_event)
            self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)
            self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, command=self.sidebar_button_event)
            self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)
            self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
            self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
            self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                        command=self.change_appearance_mode_event)
            self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))
            self.scaling_label = ctk.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
            self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
            self.scaling_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"],
                                                                command=self.change_scaling_event)
            self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

            # create main entry and button
            self.entry = ctk.CTkEntry(self, placeholder_text="CTkEntry")
            self.entry.grid(row=3, column=1, columnspan=2, padx=(20, 0), pady=(20, 20), sticky="nsew")

            self.main_button_1 = ctk.CTkButton(master=self, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"))
            self.main_button_1.grid(row=3, column=3, padx=(20, 20), pady=(20, 20), sticky="nsew")

            # create textbox
            self.textbox = ctk.CTkTextbox(self, width=250)
            self.textbox.grid(row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

            # create tabview
            self.tabview = ctk.CTkTabview(self, width=250)
            self.tabview.grid(row=0, column=2, padx=(20, 0), pady=(20, 0), sticky="nsew")
            self.tabview.add("CTkTabview")
            self.tabview.add("Tab 2")
            self.tabview.add("Tab 3")
            self.tabview.tab("CTkTabview").grid_columnconfigure(0, weight=1)  # configure grid of individual tabs
            self.tabview.tab("Tab 2").grid_columnconfigure(0, weight=1)

            self.optionmenu_1 = ctk.CTkOptionMenu(self.tabview.tab("CTkTabview"), dynamic_resizing=False,
                                                            values=["Value 1", "Value 2", "Value Long Long Long"])
            self.optionmenu_1.grid(row=0, column=0, padx=20, pady=(20, 10))
            self.combobox_1 = ctk.CTkComboBox(self.tabview.tab("CTkTabview"),
                                                        values=["Value 1", "Value 2", "Value Long....."])
            self.combobox_1.grid(row=1, column=0, padx=20, pady=(10, 10))
            self.string_input_button = ctk.CTkButton(self.tabview.tab("CTkTabview"), text="Open CTkInputDialog",
                                                            command=self.open_input_dialog_event)
            self.string_input_button.grid(row=2, column=0, padx=20, pady=(10, 10))
            self.label_tab_2 = ctk.CTkLabel(self.tabview.tab("Tab 2"), text="CTkLabel on Tab 2")
            self.label_tab_2.grid(row=0, column=0, padx=20, pady=20)

            # create radiobutton frame
            self.radiobutton_frame = ctk.CTkFrame(self)
            self.radiobutton_frame.grid(row=0, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")
            self.radio_var = tk.IntVar(value=0)
            self.label_radio_group = ctk.CTkLabel(master=self.radiobutton_frame, text="CTkRadioButton Group:")
            self.label_radio_group.grid(row=0, column=2, columnspan=1, padx=10, pady=10, sticky="")
            self.radio_button_1 = ctk.CTkRadioButton(master=self.radiobutton_frame, variable=self.radio_var, value=0)
            self.radio_button_1.grid(row=1, column=2, pady=10, padx=20, sticky="n")
            self.radio_button_2 = ctk.CTkRadioButton(master=self.radiobutton_frame, variable=self.radio_var, value=1)
            self.radio_button_2.grid(row=2, column=2, pady=10, padx=20, sticky="n")
            self.radio_button_3 = ctk.CTkRadioButton(master=self.radiobutton_frame, variable=self.radio_var, value=2)
            self.radio_button_3.grid(row=3, column=2, pady=10, padx=20, sticky="n")

            # create slider and progressbar frame
            self.slider_progressbar_frame = ctk.CTkFrame(self, fg_color="transparent")
            self.slider_progressbar_frame.grid(row=1, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")
            self.slider_progressbar_frame.grid_columnconfigure(0, weight=1)
            self.slider_progressbar_frame.grid_rowconfigure(4, weight=1)
            self.seg_button_1 = ctk.CTkSegmentedButton(self.slider_progressbar_frame)
            self.seg_button_1.grid(row=0, column=0, padx=(20, 10), pady=(10, 10), sticky="ew")
            self.progressbar_1 = ctk.CTkProgressBar(self.slider_progressbar_frame)
            self.progressbar_1.grid(row=1, column=0, padx=(20, 10), pady=(10, 10), sticky="ew")
            self.progressbar_2 = ctk.CTkProgressBar(self.slider_progressbar_frame)
            self.progressbar_2.grid(row=2, column=0, padx=(20, 10), pady=(10, 10), sticky="ew")
            self.slider_1 = ctk.CTkSlider(self.slider_progressbar_frame, from_=0, to=1, number_of_steps=4)
            self.slider_1.grid(row=3, column=0, padx=(20, 10), pady=(10, 10), sticky="ew")
            self.slider_2 = ctk.CTkSlider(self.slider_progressbar_frame, orientation="vertical")
            self.slider_2.grid(row=0, column=1, rowspan=5, padx=(10, 10), pady=(10, 10), sticky="ns")
            self.progressbar_3 = ctk.CTkProgressBar(self.slider_progressbar_frame, orientation="vertical")
            self.progressbar_3.grid(row=0, column=2, rowspan=5, padx=(10, 20), pady=(10, 10), sticky="ns")

            # create scrollable frame
            self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="CTkScrollableFrame")
            self.scrollable_frame.grid(row=1, column=2, padx=(20, 0), pady=(20, 0), sticky="nsew")
            self.scrollable_frame.grid_columnconfigure(0, weight=1)
            self.scrollable_frame_switches = []
            for i in range(100):
                switch = ctk.CTkSwitch(master=self.scrollable_frame, text=f"CTkSwitch {i}")
                switch.grid(row=i, column=0, padx=10, pady=(0, 20))
                self.scrollable_frame_switches.append(switch)

            # create checkbox and switch frame
            self.checkbox_slider_frame = ctk.CTkFrame(self)
            self.checkbox_slider_frame.grid(row=1, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")
            self.checkbox_1 = ctk.CTkCheckBox(master=self.checkbox_slider_frame)
            self.checkbox_1.grid(row=1, column=0, pady=(20, 0), padx=20, sticky="n")
            self.checkbox_2 = ctk.CTkCheckBox(master=self.checkbox_slider_frame)
            self.checkbox_2.grid(row=2, column=0, pady=(20, 0), padx=20, sticky="n")
            self.checkbox_3 = ctk.CTkCheckBox(master=self.checkbox_slider_frame)
            self.checkbox_3.grid(row=3, column=0, pady=20, padx=20, sticky="n")

            # set default values
            self.sidebar_button_3.configure(state="disabled", text="Disabled CTkButton")
            self.checkbox_3.configure(state="disabled")
            self.checkbox_1.select()
            self.scrollable_frame_switches[0].select()
            self.scrollable_frame_switches[4].select()
            self.radio_button_3.configure(state="disabled")
            self.appearance_mode_optionemenu.set("Dark")
            self.scaling_optionemenu.set("100%")
            self.optionmenu_1.set("CTkOptionmenu")
            self.combobox_1.set("CTkComboBox")
            self.slider_1.configure(command=self.progressbar_2.set)
            self.slider_2.configure(command=self.progressbar_3.set)
            self.progressbar_1.configure(mode="indeterminnate")
            self.progressbar_1.start()
            self.textbox.insert("0.0", "CTkTextbox\n\n" + "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.\n\n" * 20)
            self.seg_button_1.configure(values=["CTkSegmentedButton", "Value 2", "Value 3"])
            self.seg_button_1.set("Value 2")

        def open_input_dialog_event(self):
            dialog = ctk.CTkInputDialog(text="Type in a number:", title="CTkInputDialog")
            print("CTkInputDialog:", dialog.get_input())

        def change_appearance_mode_event(self, new_appearance_mode: str):
            ctk.set_appearance_mode(new_appearance_mode)

        def change_scaling_event(self, new_scaling: str):
            new_scaling_float = int(new_scaling.replace("%", "")) / 100
            ctk.set_widget_scaling(new_scaling_float)

        def sidebar_button_event(self):
            print("sidebar_button click")

    app = App()
    app.mainloop()

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
        app = run_example()
    except Exception as e:
        print(f"An error occurred: {e}")
        raise e


# END