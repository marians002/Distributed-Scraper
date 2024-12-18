import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from DB_manager import store_data


def fetch_html(urls, settings):
    html_contents = {}
    extra_info = {}

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

            # Always extract images and links
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg']
            images = [urljoin(url, img['src']) for img in soup.find_all('img') if
                      'src' in img.attrs and any(img['src'].endswith(ext) for ext in image_extensions)]
            links = [a['href'] for a in soup.find_all('a') if
                     'href' in a.attrs and (a['href'].startswith('http://') or a['href'].startswith('https://'))]

            # Download images and save them in a directory corresponding to each URL
            image_dir = os.path.join('htmls',
                                     url.replace('https://', '').replace('http://', '').replace('/', '_') + '_images')
            if not os.path.exists(image_dir):
                os.makedirs(image_dir)

            downloaded_images = []
            for img_url in images:
                try:
                    img_response = requests.get(img_url)
                    img_response.raise_for_status()
                    img_name = os.path.join(image_dir, os.path.basename(img_url))

                    downloaded_images.append(img_name)
                except requests.exceptions.RequestException as e:
                    print(f"Error downloading image {img_url}: {e}")

            extra_info[url] = {'images': downloaded_images, 'links': links}

            # Store data in the database
            store_data(url, html_content, links, downloaded_images)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            html_contents[url] = None

    # Filter the results based on settings
    filtered_extra_info = {}
    for url, info in extra_info.items():
        filtered_info = {}
        if settings.get('extract_images', False):
            filtered_info['images'] = info['images']
        if settings.get('extract_links', False):
            filtered_info['links'] = info['links']
        filtered_extra_info[url] = filtered_info

    return html_contents, filtered_extra_info
