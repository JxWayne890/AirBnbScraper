from flask import Flask, request, jsonify
from scraper import scrape_site

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Scraper is running."

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing 'url'"}), 400

    result = scrape_site(url)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
