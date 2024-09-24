import requests
import os
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

cwd = os.getcwd()  # change for '__file__' if using .py 
url_general = "chrome://bookmarks/" # import data (skip if it has been done)

data = requests.get(url_general)

filename = os.path.join(cwd, '.\\chrome.html')
with open(filename, 'w+', encoding="utf-8") as f:
    f.write(data.text)
