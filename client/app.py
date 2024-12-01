from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('frontend.html')


@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    scrape_option = request.form['scrapeOption']

    # Perform the scraping based on the selected option
    if scrape_option == 'html':
        response = requests.get(url)
        data = response.text
    elif scrape_option == 'links':
        response = requests.get(url)
        data = extract_links(response.text)
    elif scrape_option == 'archives':
        data = "Archives scraping not implemented yet"
    else:
        data = "Invalid option"

    return jsonify({'data': data})


def extract_links(html):
    # Implement link extraction logic
    return "Links extraction not implemented yet"

if __name__ == '__main__':
    app.run(debug=True)
