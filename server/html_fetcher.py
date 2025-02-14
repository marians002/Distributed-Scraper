import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from DB_manager import store_data


def fetch_html(urls, settings):
    html_contents = {}
    extra_info = {}

    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()  # Check if the request was successful
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract HTML
            html_content = soup.prettify()
            html_contents[url] = html_content if settings.get('extract_html', False) else None

            # Extract CSS
            css_content = []
            if settings.get('extract_css', False):
                # Inline CSS
                for style in soup.find_all('style'):
                    if style.string:
                        css_content.append(style.string)

                # External CSS
                for link in soup.find_all('link', rel='stylesheet'):
                    css_url = link.get('href')
                    if css_url:
                        # Handle relative URLs
                        if not css_url.startswith(('http://', 'https://')):
                            css_url = urljoin(url, css_url)
                        try:
                            css_response = requests.get(css_url)
                            css_response.raise_for_status()
                            css_content.append(css_response.text)
                        except requests.exceptions.RequestException as e:
                            print(f"Error fetching CSS {css_url}: {e}")

            # Extract JavaScript
            js_content = []
            if settings.get('extract_js', False):
                # Inline JS
                for script in soup.find_all('script'):
                    if script.string:  # Check if the script tag contains JavaScript code
                        js_content.append(script.string)

                    # External JS
                    elif script.get('src'):
                        js_url = script.get('src')
                        if not js_url.startswith(('http://', 'https://')):
                            # Handle relative URLs
                            js_url = urljoin(url, js_url)
                        try:
                            js_response = requests.get(js_url)
                            js_response.raise_for_status()
                            js_content.append(js_response.text)
                        except requests.exceptions.RequestException as e:
                            print(f"Error fetching JavaScript {js_url}: {e}")

            # Store all extracted data
            extra_info[url] = {
                'css': css_content,
                'js': js_content,
            }

            # Store data in the database
            store_data(url, html_content, css_content, js_content)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            html_contents[url] = None

    return html_contents, extra_info
