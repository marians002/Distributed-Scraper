import sqlite3
import os

# Define the database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'scraper.db')

def inspect_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch and print HTML content
    cursor.execute('SELECT * FROM html_content')
    html_content = cursor.fetchall()
    print("HTML Content:")
    for row in html_content:
        if 'juventudrebelde' in row[1]:  # Assuming the content is in the second column
            print(row)

    # Fetch and print links
    cursor.execute('SELECT * FROM links')
    links = cursor.fetchall()
    # print("\nLinks:")
    # for row in links:
    #     print(row)

    # Fetch and print images
    cursor.execute('SELECT * FROM images')
    images = cursor.fetchall()
    # print("\nImages:")
    # for row in images:
    #     print(row)

    conn.close()

if __name__ == '__main__':
    inspect_db()