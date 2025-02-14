from flask import Flask, render_template, request
import socket
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# SERVER_IP = "10.0.11.2"
SERVER_PORT = 5002
SERVER_IP = "127.0.0.1"


@app.route('/')
def home():
    return render_template('frontend.html')


@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    scrape_option = request.form['scrapeOption']

    settings = {
        'extract_html': scrape_option == 'html',
        'extract_css': scrape_option == 'css',
        'extract_js': scrape_option == 'js'
    }

    response = send_request_to_server(url, settings)
    return response

def send_request_to_server(url, settings):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, SERVER_PORT))
        print("Successfully connected")
        request_data = str({'url': url, 'settings': settings})
        s.sendall(request_data.encode())
        print("Waiting for response from server...")

        # Receive the response in parts and concatenate them
        data = b""
        while True:
            part = s.recv(4096)
            if not part:
                break
            data += part

        print("Received response from server")

        decoded = data.decode()
        response = eval(decoded)
        return format_response(response)


def format_response(response):
    """
    Formats the response to make it more visually appealing and removes brackets/quotes.
    """
    formatted_response = []
    for url, content in response.items():
        formatted_response.append(f"URL: {url}")
        if 'css' in content and isinstance(content['css'], list):
            css_content = content['css'][0] if len(content['css']) == 1 else "\n".join(content['css'])
            formatted_response.append(f"CSS:\n{css_content}")
        if 'js' in content and isinstance(content['js'], list):
            js_content = content['js'][0] if len(content['js']) == 1 else "\n".join(content['js'])
            formatted_response.append(f"JavaScript:\n{js_content}")
        if 'html' in content:
            formatted_response.append(f"HTML:\n{content['html']}")
        formatted_response.append("")

    return "\n".join(formatted_response)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
