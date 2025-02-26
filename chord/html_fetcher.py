import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from DB_manager import *
import logging
import json

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set the depth for in-depth scraping
DEPTH = 1


def scrape(urls, settings, depth=DEPTH):
    results = {}
    urls = [urls] if isinstance(urls, str) else urls
    logging.info(f"Starting scrape for URLs: {urls} with settings: {settings} and depth: {depth}")

    for url in urls:
        # Initialize the result dictionary for the current URL
        results[url] = {}

        # Fetch data from the database
        response = fetch_data_from_db(url)
        html_content = response.get('html_content')
        css_content = response.get('css', [])
        js_content = response.get('js', [])

        # Check if HTML is requested and available in the database
        if settings == 'html':
            if html_content:
                results[url]['html'] = html_content
                logging.info(f"HTML content for {url} found in database")
            else:
                # Fetch HTML from the web if not in the database
                logging.info(f"Fetching HTML content for {url} from the web")
                html_contents, _ = fetch_html([url], {'extract_html': True}, depth)
                results[url]['html'] = html_contents.get(url)

        # Check if CSS is requested and available in the database
        if settings == 'css':
            if css_content:
                results[url]['css'] = css_content
                logging.info(f"CSS content for {url} found in database")
            else:
                # Fetch CSS from the web if not in the database
                logging.info(f"Fetching CSS content for {url} from the web")
                _, extra_info = fetch_html([url], {'extract_css': True}, depth)
                results[url]['css'] = extra_info.get(url, {}).get('css', [])

        # Check if JavaScript is requested and available in the database
        if settings == 'js':
            if js_content:
                results[url]['js'] = js_content
                logging.info(f"JavaScript content for {url} found in database")
            else:
                # Fetch JavaScript from the web if not in the database
                logging.info(f"Fetching JavaScript content for {url} from the web")
                _, extra_info = fetch_html([url], {'extract_js': True}, depth)
                results[url]['js'] = extra_info.get(url, {}).get('js', [])

    logging.info(f"Scrape completed for URLs: {urls}")
    return json.dumps(results)


def fetch_html(urls, settings, depth=DEPTH):
    html_contents = {}
    extra_info = {}
    logging.info(f"Fetching HTML for URLs: {urls} with settings: {settings} and depth: {depth}")

    for url in urls:
        try:
            logging.info(f"Fetching content from {url}")
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
                            logging.info(f"Fetching CSS from {css_url}")
                            css_response = requests.get(css_url)
                            css_response.raise_for_status()
                            css_content.append(css_response.text)
                        except requests.exceptions.RequestException as e:
                            logging.error(f"Error fetching CSS {css_url}: {e}")

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
                            logging.info(f"Fetching JavaScript from {js_url}")
                            js_response = requests.get(js_url)
                            js_response.raise_for_status()
                            js_content.append(js_response.text)
                        except requests.exceptions.RequestException as e:
                            logging.error(f"Error fetching JavaScript {js_url}: {e}")

            # Store all extracted data
            extra_info[url] = {
                'css': css_content,
                'js': js_content,
            }

            # Send data to the database manager
            request_dict = {
                'url': url,
                'html_content': html_content,
                'css': css_content,
                'js': js_content
            }
            logging.info(f"Storing data in database for {url}")
            store_data(request_dict)

            # If depth is greater than 0, recursively fetch HTML from links found in the current page
            if depth > 0:
                links = soup.find_all('a', href=True)
                linked_urls = [urljoin(url, link['href']) for link in links]
                linked_html_contents, linked_extra_info = fetch_html(linked_urls, settings, depth - 1)
                html_contents.update(linked_html_contents)
                extra_info.update(linked_extra_info)

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching {url}: {e}")
            html_contents[url] = None

    logging.info(f"HTML fetch completed for URLs: {urls}")
    return html_contents, extra_info
