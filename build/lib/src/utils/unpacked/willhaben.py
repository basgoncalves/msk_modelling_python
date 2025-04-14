import requests
import os
from bs4 import BeautifulSoup
import pandas as pd

def data_from_willhaben(url):
    try:
        data = requests.get(url)            # request data
        print(data.reason)
    except requests.ConnectionError as e:
        print("ERROR: Failed to establish connection")
        return
    except:
        print("Paste URL for the Willhaben ad (https://www.willhaben.at): ")
        url = input()
        try:
            data = requests.get(url)
        except requests.ConnectionError as e:
            print(e)
            return
        

    # current_script_path = os.getcwd()               # .ipynb
    current_script_path = os.path.dirname(__file__) # .py

    filename = os.path.join(current_script_path, '.\\ncbi.html')
    with open(filename, 'w+', encoding="utf-8") as f:
        f.write(data.text)

    dfs = [] # create data frame

    with open(filename, 'r', encoding="utf-8") as f:
        page = f.read()

    soup = BeautifulSoup(page, 'html.parser')
    address = soup.find('div', attrs={
                    'data-testid': 'object-location-address'}, class_='Box-sc-wfmb7k-0').text.strip()
    price = soup.find('span', attrs={
                  'data-testid': 'contact-box-price-box-price-value-0'}, class_='Text-sc-10o2fdq-0 iYbzSg').text.strip()
    costs_tree = soup.findAll('span', class_='Text-sc-10o2fdq-0 jfmShM')

    costs = []
    for i in range(0,len(costs_tree)):
        costs.append(costs_tree[i].find('span', class_='Text-sc-10o2fdq-0 gxQSIC').text.strip())
        if i != len(costs_tree)-1:
            costs.append(' + ')
    costs = ' '.join(costs).replace('.',',')

    print('')
    print('')
    print('Data from URL:')
    print('address: ' + address)
    print('price: ' + price)
    print('costs: ' + costs)

    data = {'address': [address],'price': [price], 'costs': [costs], 
        'url': [url]}

    df = pd.DataFrame(data)
    df[0:].to_clipboard(excel=True, sep=None, index=False, header=None)

# test example
# data_from_willhaben('https://www.willhaben/d/mietwohnungen/wien/wien-1050-margareten/traumhaft-sanierte-altbauwohnung-am-bacherplatz-622809329/')
data_from_willhaben('')


