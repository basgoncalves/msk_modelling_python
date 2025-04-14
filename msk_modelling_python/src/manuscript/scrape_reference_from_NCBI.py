# Description: Web scraping scientific papers' details and add them to "LiteratureReview.xlsx"
# ----------------------------------------------------------------------------
# Usage: Run the code and paste the Pubmed URL or DOI for the paper
#        Pubmed: https://pubmed.ncbi.nlm.nih.gov/
#        DOI: https://www.doi.org/
# ----------------------------------------------------------------------------
# Author: Bas Goncalves
# GitHub: https://github.com/basgoncalves
# Created: June 20, 2022 
# Last Update: August 23, 2023
# ----------------------------------------------------------------------------


import requests
import os
import sys
import os
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from tkinter.filedialog import askopenfilename
import re
import webbrowser

def save_to_xlsx(): # not finished yet
    
    # Step 1: Load the .xlsx file
    file_path = askopenfilename(filetypes=[("Excel Files", "*.xlsx")])

    # Check if a file was selected
    if not file_path:
        messagebox.showinfo("Info", "No file selected. Exiting...")
        exit()

    # Step 2: Find all the tabs and ask the user to select one
    xl = pd.ExcelFile(file_path)
    tabs = xl.sheet_names()
    selected_tab = messagebox.askquestion("Select Tab", "Select a tab to add a row:", choices=tabs)

    # Check if a tab was selected
    if selected_tab == 'no':
        messagebox.showinfo("Info", "No tab selected. Exiting...")
        exit()

    # Step 3: Add a row to the selected tab
    df = pd.read_excel(file_path, sheet_name=selected_tab)
    new_row = pd.DataFrame({'Column1': 'Value1', 'Column2': 'Value2'}, index=[0])
    df = pd.concat([df, new_row])

    # Step 4: Save the .xlsx file
    xl_writer = pd.ExcelWriter(file_path, engine='xlsxwriter')
    df.to_excel(xl_writer, sheet_name=selected_tab, index=False)
    xl_writer.save()

    # Step 5: Open the file in the system viewer
    os.startfile(file_path)

def get_pubmed_url(doi):
    base_url = 'https://pubmed.ncbi.nlm.nih.gov/?term='
    doi_url = base_url + doi.replace('/', '%2F')
    
    response = requests.get(doi_url)
    if response.status_code == 200:
        return response.url
    else:
        return None

def identify_string_type(string):
    # Regular expression patterns for URL and DOI
    url_pattern = r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)'
    doi_pattern = r'\b(10\.[0-9]{4,}(?:\.[1-9][0-9]*)*/(?:(?!["&\'<>])\S)+)\b'

    # Check if the string matches the URL pattern
    if re.match(url_pattern, string):
        return 'URL'

    # Check if the string matches the DOI pattern
    if re.match(doi_pattern, string):
        return 'DOI'

    # If the string matches neither pattern, return None
    return None

def send_to_citation_manager(url=0):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from bs4 import BeautifulSoup
    # Set up the Selenium webdriver
    driver = webdriver.Chrome()

    url = 'https://pubmed.ncbi.nlm.nih.gov/33967684/'

    driver.get(url)

    # Wait for the "Citation manager" button to be visible
    wait = WebDriverWait(driver, 1)
    citation_manager_button = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "citation-manager-panel-trigger")))

    # Click the "Citation manager" button
    citation_manager_button.click()

    # Wait for the "Create file" button to be visible
    create_file_button = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "action-panel-submit")))

    # Click the "Create file" button
    create_file_button.click()

    # Wait for the file to be generated and retrieve the download link
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "download-link")))
    download_link = driver.find_element(By.CLASS_NAME, "download-link").get_attribute("href")

    # Print the download link
    print(download_link)

    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs", {
        "download.default_directory": get_download_dir()
    })

    driver = webdriver.Chrome(options=options)

def get_download_dir():
    home_dir = os.path.expanduser("~")

    # Construct the download folder path based on the operating system
    if os.name == 'nt':  # Windows
        download_folder = os.path.join(home_dir, 'Downloads')
    elif os.name == 'posix':  # macOS or Linux
        download_folder = os.path.join(home_dir, 'Downloads')
    else:
        download_folder = None  # Unsupported operating system
    
    return download_folder

def get_information_from_url(url=''):
              
    # find location of current file
    current_script_path = os.path.dirname(__file__)# 'os.path.dirname(__file__)' if.py  'os.getcwd() ' if  .ipynb)
    print(current_script_path)

    if not url:
        print("Paste the pubmed URL for the paper: ")
        url = input()

    if identify_string_type(url) == 'DOI':
        print('PubMed URL identified...')
        url = get_pubmed_url(url)
        print('new url: ', url)

    # if url starts with " -o "
    if url.startswith('-o '):
        open_url = True
        url = url.replace('-o ', '')
        print('url: ', url)
    else:
        open_url = False


    # request data if URL doesn't exist use a generic Pubmed link
    try:
        print("requsting data from " + url)
        data = requests.get(url)            
    except:
        
        print(url + ' does not exist')
        url = r'https://pubmed.ncbi.nlm.nih.gov/36457193/'
        print("requsting data from " + url)
        data = requests.get(url)            

    ncbi_html = os.path.join(current_script_path, '.\\ncbi.html')
    with open(ncbi_html, 'w+', encoding="utf-8") as f:
        f.write(data.text)

    # create data frame
    dfs = []
    with open(ncbi_html, 'r', encoding="utf-8") as f:
        page = f.read()

    os.remove(ncbi_html)

    soup = BeautifulSoup(page, 'html.parser')
    authors = soup.findAll('a', class_='full-name')
    names = []
    for i in range(0,len(authors)):
        names.append(authors[i]['data-ga-label'])

    # author last name
    try:
        last_name = (names[0].rsplit(" ", 1)[1] + ' et al.')
    except:
        last_name = 'None'
    
    # Title
    try:
        title = soup.find('h1', class_='heading-title').text.strip()
    except:
        title = 'None'
    
    # Journal
    try:
        journal = soup.find('div', class_='journal-actions dropdown-block').button['title']
    except:
        journal = 'None'
    
    # Year
    try:
        year = soup.find('span', class_='cit').text[0:4]
    except:
        year = 'None'     
    
    # DOI
    try:
        doi = soup.find('span', class_='citation-doi').text.strip()
    except:
        doi = 'none'

    data = {'author': [last_name],'year': [year], 'journal': [journal], 
            'url': [url]}

    df = pd.DataFrame(data)
    df[0:].to_clipboard(excel=True, sep=None, index=False, header=None)

    if open_url:
        webbrowser.open(url)

    print('')
    print('')
    print(url)
    print({'author':[last_name],'title': [title], 'doi': [doi]})
    print(last_name + '-' + year + '-' + journal)

    print('')
    names_in_string = ', '.join(names)
    print('{0}, {1}, {2}, {3}, {4}'.format(names_in_string, year, title ,journal, doi))

    # to use for a diffrent format of excel
    dif_format = False
    if dif_format:
        data = {'author': [last_name],'title': [title], 'year': [year], 'journal': [journal], 'doi': [doi[5:]],
                'url': [url]}

        df2 = pd.DataFrame(data)
        df2[0:].to_clipboard(excel=True, sep=None, index=False, header=None)

    return df[0:]
       
  
if __name__ == '__main__':
    get_information_from_url()
    current_script_path = os.path.dirname(__file__)
  
    # open excel file
    # os.startfile(os.path.join(current_script_path, r'literature_review.xlsx'))
# end