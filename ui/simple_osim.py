import tkinter as tk
from tkinter import ttk
import os
import customtkinter
from msk_modelling_python import osim


class App(customtkinter.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__()

        self.title("Simple osim")
               
        
        self.label = customtkinter.CTkLabel(self, text="Enter the path of the osim model:")
        self.label.pack(padx=20, pady=20)
                
        
        self.button = customtkinter.CTkButton(self, text="my button", command=self.run_system_deault)
        self.button.pack(padx=20, pady=20)
        
        self.autoscale()
        
    
            
    def add(self, *args, **kwargs):
        
        if "label" in kwargs:
            self.label = customtkinter.CTkLabel(self, text=kwargs["label"])
            self.label.pack(padx=20, pady=20)
        elif "button" in kwargs:
            self.button = customtkinter.CTkButton(self, text=kwargs["button"], command=self.run_system_deault)
            self.button.pack(padx=20, pady=20)
            
        elif "osim_input" in kwargs:
            self.label = customtkinter.CTkLabel(self, text=kwargs["osim_input"][0])
            self.label.pack(padx=20, pady=20)
            
            self.input = customtkinter.CTkEntry(self)   
            self.input.insert(0, ik_path)
            self.input.pack(padx=20, pady=20)
            
            self.button_run = customtkinter.CTkButton(self, text=kwargs["osim_input"][2], command=self.run_system_deault)
            self.button_run.pack(padx=20, pady=20)
            
            self.input_setup_xml = os.path.dirname(self.input.get())
            self.button_open = customtkinter.CTkButton(self, text="Edit setup", command=self.edit_setup_file)
            self.button_open.pack(padx=20, pady=20)
        
        else:
            print("Error: no valid input")
        
        # self.autoscale()
            
            
    def run_system_deault(self):
        if not os.path.exists(self.input.get()):
            print("Error: file does not exist")
            return
        os.system(self.input.get())
        
    def run_osim_setup(self):
        if not os.path.exists(self.input_setup_xml):
            print("Error: file does not exist")
            return
        osim.run(self.input_setup_xml)
        
    def edit_setup_file(self):
        if not os.path.exists(self.input_setup_xml):
            print("Error: file does not exist")
            return
        os.system(self.input_setup_xml)  

        
    def autoscale(self, centered=True):
        self.update_idletasks()
        self.geometry(f"{self.winfo_reqwidth()}x{self.winfo_reqheight()}")
        if centered:
            self.center()

    def center(self):
        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def start(self):
        self.mainloop()
        
  


app = App()
# ik path as relative path to example_data
prompt = "Enter the path of the ik setup file"
ik_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "example_data", "walking", "trial1", "ik.mot")
app.add(osim_input = ["Penis:", ik_path, "Run"])
app.autoscale()
app.start()