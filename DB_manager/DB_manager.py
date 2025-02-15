from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

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
        CREATE TABLE IF NOT EXISTS css_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            css TEXT,
            FOREIGN KEY(url) REFERENCES html_content(url)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS js_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            js TEXT,
            FOREIGN KEY(url) REFERENCES html_content(url)
        )
    ''')
    conn.commit()
    conn.close()


@app.route('/store', methods=['POST'])
def store_data():
    data = request.json
    url = data['url']
    html_content = data['html_content']
    css_content = data.get('css', [])
    js_content = data.get('js', [])

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO html_content (url, content) VALUES (?, ?)', (url, html_content))
    for css in css_content:
        cursor.execute('INSERT INTO css_content (url, css) VALUES (?, ?)', (url, css))
    for js in js_content:
        cursor.execute('INSERT INTO js_content (url, js) VALUES (?, ?)', (url, js))
    conn.commit()
    conn.close()
    return jsonify({'status': 'OK'})


@app.route('/fetch', methods=['POST'])
def fetch_data_from_db():
    data = request.json
    url = data['url']

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT content FROM html_content WHERE url = ?', (url,))
    html_content = cursor.fetchone()
    cursor.execute('SELECT css FROM css_content WHERE url = ?', (url,))
    css_content = [row[0] for row in cursor.fetchall()]
    cursor.execute('SELECT js FROM js_content WHERE url = ?', (url,))
    js_content = [row[0] for row in cursor.fetchall()]
    conn.close()

    return jsonify({
        'html_content': html_content[0] if html_content else None,
        'css': css_content,
        'js': js_content
    })


@app.route('/delete', methods=['POST'])
def delete_data():
    data = request.json
    url = data['url']

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM html_content WHERE url = ?', (url,))
    cursor.execute('DELETE FROM css_content WHERE url = ?', (url,))
    cursor.execute('DELETE FROM js_content WHERE url = ?', (url,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'OK'})


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5008)
