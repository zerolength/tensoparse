import sys
import argparse


parser = argparse.ArgumentParser(description='TensojapanParse')

parser.add_argument('Inputfile', nargs=1)
parser.add_argument('Outputfile',  nargs='?')
parser.add_argument('-i', '--input')
parser.add_argument('-o', '--output')
parser.add_argument('-d', dest='usedate',action='store_true',help="Use date as output file name $date.csv")
#parser.add_argument('-ja',dest='JA',action='store_true')
parser.add_argument('-en',dest='EN',action='store_true',help="Use EN formatting instead of JA when you load EN pages")
args = parser.parse_args()

if args.input is not None:
    ifile = args.input[0]
elif args.Inputfile is not None:
        ifile = args.Inputfile[0] 
else:
        print('no input given')

from datetime import date

today = date.today().strftime("%Y%m%d")


if args.output is not None:
    ofile = args.output
elif args.Outputfile is not None:
    
    ofile = args.Outputfile

else: ofile = ifile[:-5]+".csv"

if args.usedate is True:
    ofile = today+".csv"


offset = [12, 5, 4, -2, 10]

if args.EN is True:
    #use EN format and offset
    offset = [33, 18, 8, -2, 12]

#testS = "a very long test string"
#testSe= testS[offset[3]:]
print(args)


print("Date:", today)

import os
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

from bs4 import BeautifulSoup

with open(os.path.join(__location__, ifile),"r",encoding="UTF-8") as fp:
    soup = BeautifulSoup(fp, 'html.parser')


# find the items section-----------------------------------
items = soup.find("div",{"class": "content"})

# find the item no.----------------------------------------
nos = [no.get_text().strip() for no in items.find_all("dd")]
firstnos = nos[0]
#print(firstnos)


# find item date
dates = [sd['datetime'] for sd in items.find_all('time')]
types = [ty.get_text() for ty in items.find_all('li')]
firstdate = dates[0]
#print(firstdate)

firstype = types[0]
#print(firstype)

#find description
descs = items.find_all("div",{"class": "item-date text-right"})
des = [des.get_text() for des in descs]
firstdesc = des[0]
#print(firstdesc)

#extract soURCE tracking nos (first line of des, truncate first 12)
sonos = [soono.split('\n')[1][offset[0]:] for soono in des]
#print(sonos[0])

#extract sITE oF pURCHASEs (2nd line of des, truncate first 18)
sops = [soops.split('\n')[2][offset[1]:] for soops in des]
#print(sops[0])

#extract wEIgHTs (3nd line of des, truncate first 4 and last 2)
wgs = [woops.split('\n')[3][offset[2]:offset[3]] for woops in des]
#print(wgs[0])

#extract single fee (4th line of des, truncate first 10) tENSOjapan sHIPPING cHARGEs
tscs = [toops.split('\n')[4][offset[4]:] for toops in des]
#print(tscs[0])

#manipulation



import pandas as pd

itemf = pd.DataFrame({

    "no": nos,
    "type": types,
    "Source_No": sonos,
    "origin": sops,
    "weight": wgs,
    "TenSo fee": tscs
})

if ofile[-4:] != ".csv":
    ofile = ofile +".csv"
    print(ofile)
itemf.to_csv(ofile)
 
    
#exec(open('tensoparse.py').read())