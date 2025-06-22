from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/')
def home():
    return "Scraper is running."

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'Missing URL'}), 400

    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')
    title = soup.title.string if soup.title else 'No title found'

    return jsonify({'title': title})
