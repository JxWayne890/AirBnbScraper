from flask import Flask, request, jsonify
from scraper import scrape_website

app = Flask(__name__)

@app.route("/")
def home():
    return "Scraper is running."

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400
    result = scrape_website(url)
    return jsonify(result)
