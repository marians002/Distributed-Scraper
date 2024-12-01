import json
from scraper import fetch_html
from DB_manager import fetch_data_from_db, init_db, show_data, delete_data

# Initialize the database
init_db()

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

def main():
    urls = [
        'https://www.example.com',
        'https://www.python.org'
    ]
    settings = {
        'extract_images': True,
        'extract_links': True
    }
    results = scrape(urls, settings)
    
    # Print the information for a single URL
    url_to_print = urls[0]
    print(f"Information for {url_to_print}:")
    show_data(url_to_print)

if __name__ == '__main__':
    main()