from flask import Flask, request, jsonify
from scraper import fetch_html
from DB_manager import fetch_data_from_db, init_db, show_data, delete_data

app = Flask(__name__)

# Initialize the database
init_db()


@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    data = request.json
    urls = data.get('urls', [])
    settings = data.get('settings', {})
    results = scrape(urls, settings)
    # print(results)
    return results


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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
