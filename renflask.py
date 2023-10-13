from flask import Flask, render_template
import pandas as pd
from datetime import datetime, date

app = Flask(__name__)

created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
today = date.today().strftime("%Y%m%d")

#source='listofshipment20231013.html'

@app.route('/')
def display_data():
    source='listofshipment'+today+ '.html'
    outf = source.replace('.html', '.csv')
    data = pd.read_csv(outf)
    # Pass your DataFrame to the template
    return render_template('shipment_temp.html', data=data.to_html(classes='dark-background'), created_time=created_time, source=source)

if __name__ == '__main__':
    app.run()