import argparse
import os
from datetime import date
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import Playwright, sync_playwright
import getpass

import renflask

# To not make mr. flake mad. Here is the general descr
# This file is the mail file to
# 1. login to tensojapan.com via playwright and get list of packages
# 2. convert list to data frame with beautifyl soup and pandas
# 3. match against amazon orders downloaded.
# 4. call renflask to render table in flask.

# 1. login using playwright generated by playwright
# py -m playwright codegen --target python -o tenso.py \
# https://www.tensojapan.com/ja/login?ReturnUrl=%2Fen%2Fpackage%2Flist


def run(playwright: Playwright) -> None:
    tenso_login = input("Enter your login for Tensoj ")
    tenso_passw = getpass.getpass("Enter your passw for Tensoj ")
    today = date.today().strftime("%Y%m%d")
    output_filename = 'listofshipment'+today+'.html'

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("""https://www.tensojapan.com/en/login?ReturnUrl=%2Fja%2Fpackage%2Flist""")  # noqa
    page.get_by_label("Registered Email Address").click()
    page.get_by_label("Registered Email Address").fill(tenso_login)
    page.get_by_label("Registered Email Address").press("Tab")
    page.get_by_label("Password").fill(tenso_passw)
    page.get_by_label("Password").press("Enter")
    page.goto("https://www.tensojapan.com/ja/package/list")

    with open(output_filename, 'w', encoding='utf-8') as file:
        file.write(page.content())

    page.close()

    # ---------------------
    context.close()
    browser.close()


def io_names():
    today = date.today().strftime("%Y%m%d")
    parser = argparse.ArgumentParser(description='TensojapanParse')
    tenso_filename = 'listofshipment'+today+'.html'

    parser.add_argument('Inputfile', nargs='?', default=tenso_filename)
    parser.add_argument('Outputfile',  nargs='?')
    parser.add_argument('-i', '--input')
    parser.add_argument('-o', '--output')
    parser.add_argument('-d', dest='usedate', action='store_true',
                        help="Use date as the output file name $date.csv")
    parser.add_argument('-en', dest='EN', action='store_true',
                        help="Use EN formatting instead \
                            of JA when you load EN pages")
    args = parser.parse_args()

    if args.input is not None:
        ifile = args.input
    elif args.Inputfile is not None:
        ifile = args.Inputfile
    else:
        print('no input given, default to file obtained from tensoJ today')
        ifile = tenso_filename

    if args.output is not None:
        ofile = args.output
    elif args.Outputfile is not None:
        ofile = args.Outputfile
    else:
        ofile = ifile[:-5] + ".csv"

    if args.usedate:
        ofile = today + ".csv"

    return ifile, ofile, args.EN


def tensosoup(ifile, offset, en_format):
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))

    with open(os.path.join(__location__, ifile), "r", encoding="UTF-8") as fp:
        soup = BeautifulSoup(fp, 'html.parser')

        items = soup.find("div", {"class": "content"})

        nos = [no.get_text().strip() for no in items.find_all("dd")]
        dates = [sd['datetime'] for sd in items.find_all('time')]
        types = [ty.get_text() for ty in items.find_all('li')]

        descs = items.find_all("div", {"class": "item-date text-right"})
        des = [des.get_text() for des in descs]

        offset = [12, 5, 4, -2, 10] if not en_format else [33, 18, 8, -2, 12]

        source_nos = [soono.split('\n')[1][offset[0]:] for soono in des]
        origins = [soops.split('\n')[2][offset[1]:] for soops in des]
        weights = [woops.split('\n')[3][offset[2]:offset[3]] for woops in des]
        tensos = [toops.split('\n')[4][offset[4]:] for toops in des]

        shipmentsdf = pd.DataFrame({
            "no": nos,
            "received_date": dates,
            "type": types,
            "Source_No": source_nos,
            "origin": origins,
            "weight": weights,
            "TenSo fee": tensos
            })

    return shipmentsdf


def amznmatch(shipmentsdf, retail_order_file):
    retail_order_df = pd.read_csv(retail_order_file)
    shipmentsdf['Product Name'] = None
    shipmentsdf['Total Owed'] = None

    for index, row in shipmentsdf.iterrows():
        for retail_index, retail_row in retail_order_df.iterrows():
            if row['Source_No'] in retail_row['Carrier Name & Tracking Number']: # noqas
                shipmentsdf.at[index, 'Source_No'] = retail_row['Carrier Name & Tracking Number'] # noqa
                shipmentsdf.at[index, 'Product Name'] = retail_row['Product Name'] # noqa
                shipmentsdf.at[index, 'Total Owed'] = retail_row['Total Owed']

    return shipmentsdf

def mandarakematch(shipmentsdf, mandarakefile):

    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))

    with open(os.path.join(__location__, mandarakefile), "r", encoding="UTF-8") as fp:
        # Parse the HTML using BeautifulSoup
        soup = BeautifulSoup(fp, 'html.parser')

        # Find the carrier name
        carrier_name = soup.find('span', id='shipMethodName').get_text()

        # Find the tracking number
        tracking_number = soup.find('span', id='shipNo').get_text()

        # Find the total owed value
        total_owed = soup.find('span', id='total').get_text()

        # Find all the <span> elements with id "itemName"
        item_name_elements = soup.find_all('span', id='itemName')

        # Extract the text from each element and store it in a list
        productname_list = [item.get_text() for item in item_name_elements]

        # Concatenate the list into a single string
        productname = '|, '.join(productname_list)

    print("Carrier Name:", carrier_name)
    print("Tracking Number:", tracking_number)

    combined = f"{carrier_name}({tracking_number})"

    print("Total Owed:", total_owed)

    for index, row in shipmentsdf.iterrows():
        if row['Source_No'] in tracking_number:
            shipmentsdf.at[index, 'Source_No'] = combined
            shipmentsdf.at[index, 'Product Name'] = productname
            shipmentsdf.at[index, 'Total Owed'] =total_owed

    return shipmentsdf

def manddarakefilelist(shipmentsdf):
    # Get the current directory
    current_directory = os.getcwd()

    # Initialize an empty list to store the matching files
    matching_files = []

    # Loop through all files in the current directory
    for filename in os.listdir(current_directory):
        # Check if the filename starts with "まんだらけ _ ご注文情報" and ends with ".html"
        if filename.startswith("まんだらけ _ ご注文情報") and filename.endswith(".html"):
            # Add the matching filename to the list
            matching_files.append(filename)

    # Now you have a list of matching filenames to run through in a for loop
    for file in matching_files:
        print("Processing file:", file)
        shipmentsdf = mandarakematch (shipmentsdf, file)

    return shipmentsdf


def movicmatch(shipmentsdf, movicfile):

    __location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

    with open(os.path.join(__location__, movicfile), "r", encoding="shift-jis") as fp:
        # Parse the HTML using BeautifulSoup
        soup = BeautifulSoup(fp, 'html.parser')

        # Find the div element with class "history_ship_"
        history_ship_div = soup.find('div', class_='history_ship_')

        # Find the list item (li) element within the div
        list_item = history_ship_div.find('li')

        # Extract the text from the list item
        tracking_number_text = list_item.get_text()

        # Extract the tracking number from the text
        tracking_number = tracking_number_text.split('No')[-1].strip()

        # Find the table element with class "formdetail_ estimate_ sales_"
        table = soup.find('table', class_='formdetail_ estimate_ sales_')

        # Find the `td` element within the table
        td = table.find('td')

        # Extract the text from the `td` element
        total_owed_text = td.get_text()

        # Clean the text by removing non-numeric characters
        total_owed = ''.join(filter(str.isdigit, total_owed_text))

                # Find all the <td> elements with class "name_"
        name_elements = soup.find_all('td', class_='name_')

        # Extract and concatenate the names into a list of strings
        productname = [name.get_text() for name in name_elements]

        carrierN_trackingnumber = f"movic({tracking_number})"
    
    for index, row in shipmentsdf.iterrows():
        if row['Source_No'] in tracking_number:
            shipmentsdf.at[index, 'Source_No'] = carrierN_trackingnumber
            shipmentsdf.at[index, 'Product Name'] = productname
            shipmentsdf.at[index, 'Total Owed'] =total_owed

    return shipmentsdf


def movicfilelist(shipmentsdf):
    # Get the current directory
    current_directory = os.getcwd()

    # Initialize an empty list to store the matching files
    matching_files = []

    # Loop through all files in the current directory
    for filename in os.listdir(current_directory):
        # Check if the filename starts with "まんだらけ _ ご注文情報" and ends with ".html"
        if filename.startswith("購入履歴詳細｜ムービック（movic）") and filename.endswith(".html"):
            # Add the matching filename to the list
            matching_files.append(filename)

    for file in matching_files:
        print("Processing file:", file)
        shipmentsdf = movicmatch(shipmentsdf, file)

    return shipmentsdf


def main():
    with sync_playwright() as playwright:
        run(playwright)

    ifile, ofile, en_format = io_names()
    offset = [12, 5, 4, -2, 10] if not en_format else [33, 18, 8, -2, 12]
    shipmentsdf = tensosoup(ifile, offset, en_format)

    shipmentsdf = amznmatch(shipmentsdf, "Retail.OrderHistory.amzn.csv")

    #cycling through mandarake files, need to add ways to get those files
    shipmentsdf = manddarakefilelist(shipmentsdf)

    shipmentsdf = movicfilelist(shipmentsdf)

    shipmentsdf = shipmentsdf.rename(columns={'Source_No':'Carrier Name & Tracking Number'}) # noqa

    if ofile[-4:] != ".csv":
        ofile = ofile + ".csv"
    shipmentsdf.to_csv(ofile, encoding='utf-8-sig')

    # renflask.display_data(shipmentsdf)
    # renflask.app(ifile)


if __name__ == '__main__':
    main()
    renflask.app.run()
