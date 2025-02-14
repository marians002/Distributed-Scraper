import sqlite3
import os
import socket
import threading
import json

# Define the database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'scraper.db')


# Initialize the database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS html_content (
            url TEXT PRIMARY KEY,
            content TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            link TEXT,
            FOREIGN KEY(url) REFERENCES html_content(url)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            image_path TEXT,
            FOREIGN KEY(url) REFERENCES html_content(url)
        )
    ''')
    conn.commit()
    conn.close()


# Store data in the database
def store_data(url, html_content, links, images):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO html_content (url, content) VALUES (?, ?)', (url, html_content))
    for link in links:
        cursor.execute('INSERT INTO links (url, link) VALUES (?, ?)', (url, link))
    for image in images:
        cursor.execute('INSERT INTO images (url, image_path) VALUES (?, ?)', (url, image))
    conn.commit()
    conn.close()


# Fetch data from the database
def fetch_data_from_db(url):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT content FROM html_content WHERE url = ?', (url,))
    html_content = cursor.fetchone()
    cursor.execute('SELECT link FROM links WHERE url = ?', (url,))
    links = [row[0] for row in cursor.fetchall()]
    cursor.execute('SELECT image_path FROM images WHERE url = ?', (url,))
    images = [row[0] for row in cursor.fetchall()]
    conn.close()
    return html_content, links, images

# Delete data for a URL
def delete_data(url):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM html_content WHERE url = ?', (url,))
    cursor.execute('DELETE FROM links WHERE url = ?', (url,))
    cursor.execute('DELETE FROM images WHERE url = ?', (url,))
    conn.commit()
    conn.close()

def receive_all_data(server_socket, buffer_size=2048):
    """
    Receive all data from the server socket.
    """
    data = b""
    while True:
        chunk = server_socket.recv(buffer_size)
        data += chunk  # Append the received chunk to the data
        if len(chunk) < buffer_size:  # If the chunk is smaller than the buffer size, we've received all data
            print("TAMAÑO DEL CHUNK: ", len(chunk))
            break
    return data


def handle_server_connection(server_socket):       

    print("Receiving data from server")
    request_data = receive_all_data(server_socket)

    print("REQUEST DATA: ", request_data[0:10], request_data[-10:-1])

    print("Received server data")
    request_dict = eval(request_data.decode())
        
    action = request_dict['action']
    url = request_dict['url']
    
    if action == 'store':
        html_content = request_dict.get('html_content')
        links = request_dict.get('links', [])
        images = request_dict.get('images', [])
        store_data(url, html_content, links, images)
        response = {'status': 'OK'}
    elif action == 'fetch':
        html_content, links, images = fetch_data_from_db(url)
        response = {
            'html_content': html_content[0] if html_content else None,
            'links': links,
            'images': images
        }
    elif action == 'delete':
        delete_data(url)
        response = {'status': 'OK'}
    else:
        response = {'status': 'Unknown action'}
    
    server_socket.sendall(str(response).encode())
    print("Response sent")
    server_socket.close()

def start_DB():
    DB_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    DB_socket.bind(("0.0.0.0", 5008))
    DB_socket.listen(5)
    print("DB says: Listening on 0.0.0.0:5008")

    while True:
        server_socket, _ = DB_socket.accept()
        client_handler = threading.Thread(target=handle_server_connection, args=(server_socket,))
        client_handler.start()

if __name__ == '__main__':
    init_db()
    start_DB()