from flask import Flask, request, jsonify
from html_fetcher import send_request_to_db_manager, fetch_html

app = Flask(__name__)


@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    data = request.json
    urls = data.get('url', [])
    settings = data.get('settings', {})
    results = scrape(urls, settings)
    return jsonify(results)


def scrape(urls, settings):
    results = {}
    for url in urls:
        # Initialize the result dictionary for the current URL
        results[url] = {}

        # Fetch data from the database
        request_dict = {'action': 'fetch', 'url': url}
        response = send_request_to_db_manager(request_dict)
        html_content = response.get('html_content')
        css_content = response.get('css', [])
        js_content = response.get('js', [])

        # Check if HTML is requested and available in the database
        if settings.get('extract_html', False):
            if html_content:
                results[url]['html'] = html_content
            else:
                # Fetch HTML from the web if not in the database
                html_contents, _ = fetch_html([url], {'extract_html': True})
                results[url]['html'] = html_contents.get(url)

        # Check if CSS is requested and available in the database
        if settings.get('extract_css', False):
            if css_content:
                results[url]['css'] = css_content
            else:
                # Fetch CSS from the web if not in the database
                _, extra_info = fetch_html([url], {'extract_css': True})
                results[url]['css'] = extra_info.get(url, {}).get('css', [])

        # Check if JavaScript is requested and available in the database
        if settings.get('extract_js', False):
            if js_content:
                results[url]['js'] = js_content
            else:
                # Fetch JavaScript from the web if not in the database
                _, extra_info = fetch_html([url], {'extract_js': True})
                results[url]['js'] = extra_info.get(url, {}).get('js', [])

    return results


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
