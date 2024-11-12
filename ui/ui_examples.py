import os
import tkinter as tk
import customtkinter as ctk
import screeninfo as si
import unittest


def get_ui_settings(settings_type = 'Default'):
    
    if settings_type == 'Default':
        settings = {
            "bg_color": "white",
            "fg_color": "black",
            "font": ("Arial", 12),
        }
    elif settings_type == 'Dark':
        settings = {
            "bg_color": "black",
            "fg_color": "white",
            "font": ("Arial", 12)
        }
    
    return settings

def show_warning(message, settings_type = 'Default'):
    
    root = ctk.CTk()
    root.title("Warning")
        
    screen = si.get_monitors()[0]
    width = 300
    height = 150
    x = (screen.width - width) // 2
    y = (screen.height - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    label = ctk.CTkLabel(root, text=message, wraplength=280)
    label.pack(pady=20)
    
    button = ctk.CTkButton(root, text="OK", command=root.destroy)
    button.pack(pady=10)
    
    root.mainloop()



class test_default_ui_examples(unittest.TestCase):
    
    ##### TESTS WORKING ######
    def test_show_warning(self):
        show_warning("This is a warning message")
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
   

# END