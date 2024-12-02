from flask import Flask, render_template, request, jsonify
import socket
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# SERVER_IP = "10.0.11.2"
# SERVER_PORT = "5001"
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5002


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

    response = send_request_to_server(url, settings)
    return jsonify(response)


def send_request_to_server(url, settings):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, SERVER_PORT))
        request_data = {'url': url, 'settings': settings}
        s.sendall(str(request_data).encode())
        print("Waiting for response from server...")
        data = s.recv(4096)
        print("Received response from server")
        return eval(data.decode())


if __name__ == '__main__':
    app.run(debug=True)
