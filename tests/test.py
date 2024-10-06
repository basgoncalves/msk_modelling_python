import msk_modelling_python as msk
import pandas as pd 

def print_test():
    print('Hello World')    

class object:
    def __init__(self, name, value, units):
        self.name = name
        self.value = value
        self.units = units

class Element:
    def __init__(self):
        self.element_type = []
        self.location = []
        self.size = []

class My:
    def __init__(self, elements):
        for index, element in enumerate(elements):
            setattr(self, element.name, element.value)

    def __add__(self, element: Element):
        setattr(self, element.name, element.value)
    
    def __attr__(self):
        return self.__dict__.keys()
    
    def print(self):
        print_test()


a = object('a', 1, 'm')
b = object('b', 2, 'm')
# for index,element in enumerate([a,b]):
#     print(element.name)
my = My([a,b])
print(my)
print(my.a)
print(my.__dict__)

my.__add__(object('c', 3, 'm'))

if type(a)==object:
    print(a)
    print('a: is an object')
else:
    print('a: is not an object')
    
if type(my)==My:
    print('my: is a My object')
else:
    print('my: is not a My object')

if hasattr(my, 'c'):
    print('my contains c')
else:
    print('my does not contain c')
    

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