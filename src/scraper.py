import os
import requests
from bs4 import BeautifulSoup

def fetch_html(urls):
    html_contents = {}
    
    # Create 'htmls' directory if it doesn't exist
    if not os.path.exists('htmls'):
        os.makedirs('htmls')
    
    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()  # Check if the request was successful
            soup = BeautifulSoup(response.text, 'html.parser')
            html_content = soup.prettify()
            html_contents[url] = html_content
            
            # Save HTML content to file
            filename = os.path.join('htmls', url.replace('https://', '').replace('http://', '').replace('/', '_') + '.html')
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(html_content)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            html_contents[url] = None
    
    return html_contents

# Example usage
urls = [
    'https://www.example.com',
    'https://www.python.org'
]

html_texts = fetch_html(urls)
for url, html in html_texts.items():
    print(f"HTML content for {url} saved.\n")