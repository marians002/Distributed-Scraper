from flask import Flask, render_template, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route('/')
def home():
    return render_template('frontend.html')


@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    scrape_option = request.form['scrapeOption']

    settings = {
        'extract_images': scrape_option == 'images',
        'extract_links': scrape_option == 'links'
    }

    response = requests.post('http://127.0.0.1:5001/scrape', json={'urls': [url], 'settings': settings})
    data = response.json()
    print(data['https://github.com/Alej0prepper/ditributed-systems-project-fall-2024/tree/main/src/network'])

    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)
