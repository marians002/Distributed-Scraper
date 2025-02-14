
from flask import Flask, render_template, request
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5002

@app.route('/')
def home():
    return render_template('frontend.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    urls = [request.form['url']]
    scrape_option = request.form['scrapeOption']

    settings = {
        'extract_html': scrape_option == 'html',
        'extract_css': scrape_option == 'css',
        'extract_js': scrape_option == 'js'
    }

    response = send_request_to_server(urls, settings)
    return response

def send_request_to_server(url, settings):
    response = requests.post(f'http://{SERVER_IP}:{SERVER_PORT}/scrape', json={'url': url, 'settings': settings})
    print("Normal: ", response)
    print(".TEXT: ", response.text)
    return format_response(response.text)

import json

def format_response(response_text):
    try:
        # Parse the JSON response
        response_data = json.loads(response_text)
        
        # Extract the URL and content
        url = list(response_data.keys())[0]
        content = response_data[url].get("html", "") or response_data[url].get("css", "") or response_data[url].get("js", "")
        content_type = "HTML" if "html" in response_data[url] else ("CSS" if "css" in response_data[url] else "JavaScript")
        
        # Format the output in a user-friendly way
        formatted_output = f"""
        Scraped URL: {url}
        Content Type: {content_type}
        Content:
        -------------------------
        {content}
        -------------------------
        """
        
        return formatted_output
    
    except json.JSONDecodeError:
        return "Invalid JSON response."
    except KeyError:
        return "The response format is not as expected."



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)