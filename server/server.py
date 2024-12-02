from flask import Flask, request, jsonify
from html_fetcher import fetch_html
from DB_manager import fetch_data_from_db, init_db
import socket
import threading

app = Flask(__name__)

# Initialize the database
init_db()


@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    data = request.json
    urls = data.get('urls', [])
    settings = data.get('settings', {})
    results = scrape(urls, settings)
    return jsonify(results)


def scrape(urls, settings):
    results = {}
    for url in urls:
        html_content, links, images = fetch_data_from_db(url)
        if html_content:
            results[url] = {
                'html': html_content[0],
                'links': links if settings.get('extract_links', False) else [],
                'images': images if settings.get('extract_images', False) else []
            }
        else:
            html_contents, extra_info = fetch_html([url], settings)
            results[url] = {
                'html': html_contents.get(url),
                'links': extra_info.get(url, {}).get('links', []),
                'images': extra_info.get(url, {}).get('images', [])
            }
    return results


def handle_client_connection(client_socket):
    request_data = client_socket.recv(4096)
    print("Received request data")
    request_dict = eval(request_data.decode())
    url = request_dict['url']
    settings = request_dict['settings']
    results = scrape([url], settings)
    print("Sending results")
    client_socket.sendall(str(results).encode())
    print("Results sent")
    client_socket.close()


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("0.0.0.0", 5002))
    server_socket.listen(5)
    print("Server says: Listening on 0.0.0.0:5002")

    while True:
        client_socket, _ = server_socket.accept()
        client_handler = threading.Thread(target=handle_client_connection, args=(client_socket,))
        client_handler.start()


if __name__ == '__main__':
    threading.Thread(target=start_server).start()
    app.run(host='0.0.0.0', port=5001)
