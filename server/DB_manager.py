import sqlite3
import os

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


# Show data for a URL
def show_data(url):
    html_content, links, images = fetch_data_from_db(url)
    if html_content:
        print(f"HTML content for {url}:\n{html_content[0]}")
    else:
        print(f"No HTML content found for {url}")
    if links:
        print(f"Links for {url}:")
        for link in links:
            print(link)
    else:
        print(f"No links found for {url}")
    if images:
        print(f"Images for {url}:")
        for image in images:
            print(image)
    else:
        print(f"No images found for {url}")


# Delete data for a URL
def delete_data(url):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM html_content WHERE url = ?', (url,))
    cursor.execute('DELETE FROM links WHERE url = ?', (url,))
    cursor.execute('DELETE FROM images WHERE url = ?', (url,))
    conn.commit()
    conn.close()
