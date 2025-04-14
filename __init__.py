try:
    from .osimRun import greet


except:
    from osimRun import greet
    
    
if __name__ == "__main__":
    greet()