import os
import tkinter as tk
import customtkinter as ctk
import screeninfo as si
from tkinter import messagebox
from msk_modelling_python import *
import msk_modelling_python as msk
from msk_modelling_python import bops
from msk_modelling_python.ui import ui_examples 
from msk_modelling_python.ui.ui_examples import get_ui_settings, show_warning, select_folder, create_folder, select_file

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

# OpenSim GUI
class App(ctk.CTk):
    '''
    Class to create a GUI for the Opensim analysis tool. The GUI includes input fields for the Opensim model and the setup files for the analysis tools.
    
    Example:
        app = App()
        app.add(type = 'osim_input', osim_model=trial_paths.model_torsion, setup_ik_path=trial_paths.setup_ik,
                setup_id_path=trial_paths.setup_id, setup_so_path=trial_paths.setup_so, setup_jra_path=trial_paths.setup_jra)
        app.add(type = 'exit_button')   
        app.autoscale()
        app.start()
    '''
        
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.title("Opensim Analysis Tool")
        
        # pading for the elements (5 pixels by default)
        self.padx = kwargs.get('padx', 5)
        self.pady = kwargs.get('pady', 5)
    
    # function to pack elements with error handling
    def try_pack(self, element):
        try:
            element.pack()
        except:
            print("Error: Could not pack element")
        
    # function to create input field and buttons for file selection and running the analysis tool     
    def create_osim_analysis_buttons(self, label_text, input_text, run_command, edit_command, padx='', pady=''):
        
        padx = padx if padx else self.padx
        pady = pady if pady else self.pady
        
        # create text label
        label = ctk.CTkLabel(self, text=label_text)
        label.pack(padx=padx, pady=pady)

        input = ctk.CTkEntry(self)
        input.insert(0, input_text)
        input.pack(padx=padx, pady=pady)

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(padx=padx, pady=pady)
        
        # button to select new file path
        open_button = ctk.CTkButton(self, text="Open", command=lambda: bops.select_file(input_text))
        open_button.pack(in_=button_frame, side="left", padx=padx, pady=pady)

        # button to run the analysis tool
        if edit_command:
            edit_button = ctk.CTkButton(self, text="Edit setup", command=edit_command)
            edit_button.pack(in_=button_frame, side="left", padx=padx, pady=pady)
        else:
            edit_button = None

        # button to run the analysis tool
        if run_command:
            run_button = ctk.CTkButton(self, text='Run', command=run_command)
            run_button.pack(in_=button_frame, side="left", padx=padx, pady=pady)
        else:
            run_button = None 
        
        return input, run_button, edit_button, open_button, label, button_frame
    
    # function to create buttons at the same y position
    def create_buttons_in_line(self, button_list, command_list, padx='', pady=''):
        
        padx = padx if padx else self.padx
        pady = pady if pady else self.pady
        
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(padx=padx, pady=pady)
        
        for i, button_text in enumerate(button_list):
            button = ctk.CTkButton(button_frame, text=button_text, command=command_list[i])
            button.pack(side="left", padx=padx, pady=pady)
    
    #%% Element handling functions
    
    # function to add elements to the GUI based on the type. osim_input is the default type and includes all input fields for the opensim analysis tools
    def add(self, type = 'osim_input', osim_model = False, setup_ik_path = '', 
            setup_id_path = '', setup_so_path = '', setup_jra_path = '', **kwargs):
        '''
        Add elements to the GUI. The default type is 'osim_input' which includes input fields for the Opensim analysis tools.
        
        usage (default):
            app = App()
            app.add('label', text='label')
            app.add('button', command=lambda: print("Button clicked"))
            app.add('entry', text='entry')
            app.add('exit_button')
            
        
        
        usage (OpenSim example advanced):
            trial_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "example_data", "walking", "trial1")
            
            app.add(type = 'osim_input', osim_model=trial_paths.model_torsion, setup_ik_path=trial_paths.setup_ik,
                    setup_id_path=trial_paths.setup_id, setup_so_path=trial_paths.setup_so, setup_jra_path=trial_paths.setup_jra)
        '''
        
        valid_types = ['label', 'button', 'entry', 'osim_input', 'exit_button']
        if type not in valid_types:
            print(f"Error: type '{type}' not recognized")
            return
        
        
        if type == 'label':
            if 'text' in kwargs:
                self.label = ctk.CTkLabel(self, text=kwargs['text'])
            else:
                self.label = ctk.CTkLabel(self, text='label')
            
            self.label.pack(padx=self.padx, pady=self.pady)
            
            return self.label
        
        # create button with or without a command
        elif type == 'button':
            if 'command' in kwargs:
                self.button = ctk.CTkButton(self, text='button', command=kwargs['command'])
            else:
                self.button = ctk.CTkButton(self, text='button', command=self.run_system_deault)
            
            self.button.pack(padx=self.padx, pady=self.pady)
            return self.button
        
        # create entry field with or without a default text
        elif type == 'entry':
            
            if 'text' in kwargs:
                self.input = ctk.CTkEntry(self)
                self.input.insert(0, kwargs['text'])
            else:
                self.input = ctk.CTkEntry(self)
            
            self.input.pack(padx=self.padx, pady=self.pady)

            return self.input
        
        # Input for an analysis tool of opensim    
        elif type == 'osim_input':
            
            # set the input field and paths
            self.model = osim_model
            self.setup_ik = setup_ik_path
            self.setup_id = setup_id_path
            self.setup_so = setup_so_path
            self.setup_jra = setup_jra_path
            
            # function to update the input field
            def update_field(field):
                new_text = bops.select_file()
                if isinstance(field, ctk.CTkEntry):
                    field.delete(0, tk.END)
                    field.insert(0, new_text)
                else:
                    print("Error: field is not a CTkEntry widget")
            
            label_osim_model = self.add(type='label', text='OpenSim Model:')
            self.entry_osim_model = self.add(type='entry', text=self.model)
            
            # input field for osim model
            button_list = ['Select new', 'Change Fmax', 'Run']
            command_list = [lambda: update_field(self.entry_osim_model), 
                            lambda: self.increase_max_isometric_force(self.model),
                            lambda: print(self.model)]
            self.create_buttons_in_line(button_list, command_list)
            
            # input field for setup file
            self.input_label = ctk.CTkLabel(self, text="Setup file paths:")
                        
            # IK
            self.create_osim_analysis_buttons("IK Setup:", setup_ik_path, 
                                          lambda: self.run_osim_setup(setup_ik_path), lambda: self.edit_setup_file(setup_ik_path))

            # ID
            self.create_osim_analysis_buttons("ID Setup:", setup_id_path, 
                                          lambda: self.run_osim_setup(setup_id_path), lambda: self.edit_setup_file(setup_id_path))
            
            # SO
            self.create_osim_analysis_buttons("SO Setup:", setup_so_path, 
                                          lambda: self.run_osim_setup(setup_so_path), lambda: self.edit_setup_file(setup_so_path))
            
            # JRA
            self.create_osim_analysis_buttons("JRA Setup:", setup_jra_path, 
                                          lambda: self.run_osim_setup(setup_jra_path), lambda: self.edit_setup_file(setup_jra_path))
                
        
        # exit button
        elif type == 'exit_button':
            self.button_quit = ctk.CTkButton(self, text="Quit", command=self.destroy)
            self.button_quit.pack(padx=self.padx, pady=self.pady)

        
        # if no valid type is given, print an error
        else:
            print("Error: no valid input")
    
    
    def close(self):
        self.quit()
        self.destroy()
    
    # function to autoscale the window to fit all elements
    def autoscale(self, centered=True):
        '''
        Autoscale the window to fit all elements. 
        usage:
            app.autoscale()
        
        arguments:
            centered: boolean to center the window on the screen
        '''
        self.update_idletasks()
        self.geometry(f"{self.winfo_reqwidth()}x{self.winfo_reqheight()}")
        if centered:
            self.center()

    # function to center the window on the screen 
    def center(self):
        '''
        Center the window on the screen.
        '''
        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    # function to split the window into two frames and get two elements as output
    def split(self, element1, element2, orientation='vertical'):
        '''
        Split the window into two frames and return the two elements.
        
        usage:
            element1, element2 = app.split(element1, element2, orientation='vertical')
        
        arguments:
            element1: first element to split
            element2: second element to split
            orientation: orientation of the split ('vertical' or 'horizontal')
        '''
        
        if orientation == 'vertical':
            frame1 = ctk.CTkFrame(self)
            frame1.pack(fill='both', expand=True)
            element1.pack(in_=frame1, fill='both', expand=True)
            
            frame2 = ctk.CTkFrame(self)
            frame2.pack(fill='both', expand=True)
            element2.pack(in_=frame2, fill='both', expand=True)
            
        elif orientation == 'horizontal':
            frame1 = ctk.CTkFrame(self)
            frame1.pack(side='left', fill='both', expand=True)
            element1.pack(in_=frame1, fill='both', expand=True)
            
            frame2 = ctk.CTkFrame(self)
            frame2.pack(side='right', fill='both', expand=True)
            element2.pack(in_=frame2, fill='both', expand=True)
        
        return frame1, frame2
    
    
    
    #%% OpenSim functions
    def increase_max_isometric_force(self, model_path):
        
        # pop up gui to enter new value
        new_value = None
        has_confirm = False
        while not type(new_value) == int:
            new_value = ctk.CTkInputDialog(title="Update Fmax", text="Enter the scale factor to use:")
            
            # tick box to confirm the action of plotting the data
            if not has_confirm:
                self.confirm_var = tk.IntVar()
                confirm = ctk.CTkCheckBox(self, text="Confirm", variable=self.confirm_var)
                confirm.pack(padx=self.padx, pady=self.pady)
                has_confirm = True
            
            new_value = new_value.get_input()
            if new_value == 'Cancel' or new_value is None:
                return
            
            # check if the input is a number
            try:
                new_value = int(new_value.get_input())
            except:
                new_value = None
        
        # update the model
        new_osim_model = bops.osimSetup.increase_max_isometric_force(model_path, new_value, self.confirm_var.get())
        
        # update the model in the GUI
        self.entry_osim_model = new_osim_model
        
        return new_osim_model
         
    # function to run the file with the system default application     
    def run_system_deault(self):
        if not os.path.exists(self.input.get()):
            print("Error: file does not exist")
            return
        os.system(self.input.get())
    
    # function to run the opensim analysis tool based on the setup file
    def run_osim_setup(self,setup_file):
        if not os.path.isfile(setup_file):
            print("Error: file does not exist")
            return
        
        
        # Check if the file is a valid setup file
        if bops.is_setup_file(setup_file,'InverseKinematicsTool' , print_output=False):
            model = osim.Model(self.model)
            tool = osim.InverseKinematicsTool(setup_file)
            tool.setModel(model)
            
            tool.run()
            
        elif bops.is_setup_file(setup_file,'InverseDynamicsTool' , print_output=False):
            model = osim.Model(self.model)
            tool = osim.InverseDynamicsTool(setup_file)
            tool.setModel(model)
            
            tool.run()
        
        elif bops.is_setup_file(setup_file,'StaticOptimization' , print_output=False) and not bops.is_setup_file(setup_file,'JointReaction' , print_output=False):
            model = osim.Model(self.model)
            tool = osim.AnalyzeTool(setup_file)
            tool.setModel(model)
            
            tool.run()
        
        elif bops.is_setup_file(setup_file,'JointReaction' , print_output=False):
            trial_path = os.path.dirname(setup_file)
            bops.runJRA(self.model, trial_path,setup_file)
            
        else:
            print("Error: file is not a valid setup file")
            print("XML file must contain the following tags:")
            print("<InverseKinematicsTool>")
    
    # function to open the setup XML in the system default editor
    def edit_setup_file(self, setup_file):
        if not os.path.exists(setup_file):
            print("Error: file does not exist")
            return
        os.system(setup_file)  
 
       
    # %% function to start the GUI
    def start(self):
        self.mainloop()

 
    

#%%
def complex_gui():
    # Create a complex GUI with multiple elements   
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

# Run when the module is called
if __name__ == "__main__":
    
    # test code 
    try:
        app = msk.bops.run_example()
        msk.bops.Platypus().happy()
        
    except Exception as e:
        print(f"An error occurred: {e}")
        raise e


# END