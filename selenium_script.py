from flask import Flask, jsonify, render_template_string
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
import uuid
import time
import json
import requests
import threading
import signal
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Flask App Initialization
app = Flask(__name__)

# Global to manage server and WebDriver instance
driver = None
server_thread = None
fetching_trends = False
fetched_data = None

# Environment Variables
PROXY = os.getenv("PROXY")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "stirTech")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "twitterTrends")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")

# Initialize WebDriver
def initialize_driver():
    global driver
    if driver is None:
        chrome_options = Options()
        #if PROXY:
        #    chrome_options.add_argument(f"--proxy-server={PROXY}")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        service = Service("C:\\webdriver\\chromedriver-win64\\chromedriver.exe")
        driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# Fetch Twitter Trends
def fetch_trending_topics():
    global fetching_trends, fetched_data
    try:
        print("Navigating to Twitter login page...")
        driver = initialize_driver()
        driver.get("https://twitter.com/login")

        # Login to Twitter
        print("Waiting for username input field...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/div[4]/label/div/div[2]/div/input'))
        ).send_keys(TWITTER_USERNAME + Keys.RETURN)

        print("Waiting for password input field...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div/div[3]/div/label/div/div[2]/div[1]/input'))
        ).send_keys(TWITTER_PASSWORD + Keys.RETURN)

        # Wait for the trends section
        print("Waiting for trends section...")
        trends_section = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[2]/div/div[2]/div/div/div/div[4]/section/div'))
        )
        trends = trends_section.find_elements(By.XPATH, ".//span")
        trending_topics = [
            trend.text for trend in trends
            if trend.text.strip() and
               "posts" not in trend.text.lower() and
               trend.text not in ["What’s happening"] and
               "· Trending" not in trend.text and
               not trend.text.startswith("Trending in")
        ]
        trending_topics = list(dict.fromkeys(trending_topics))[:5]

        unique_id = str(uuid.uuid4())
        ip_address = requests.get("https://api.ipify.org").text
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        fetched_data = {
            "_id": unique_id,
            "trending_topics": trending_topics,
            "timestamp": timestamp,
            "ip_address": ip_address,
        }

        save_to_mongodb(fetched_data)
        print("Trending topics fetched successfully.")
        if trending_topics:
            for topic in trending_topics:
                print(topic)

    except Exception as e:
        print(f"Error fetching trends: {e}")
        fetched_data = {"error": str(e)}
    finally:
        fetching_trends = False

# Save Trends to MongoDB
def save_to_mongodb(data):
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        collection.insert_one(data)
        print("Trends saved to MongoDB")
    except Exception as e:
        print(f"Error saving to MongoDB: {e}")

# Flask Route to Display Trends
@app.route("/")
def display_trends():
    global fetching_trends, fetched_data
    if fetching_trends:
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Fetching Trends...</title>
            </head>
            <body style="display:flex;flex-direction:column;justify-content:center;align-items:center;">
                <h1>Fetching trending topics...</h1>
                <div style="
                    margin: 50px 20px;
                    width: 30px;
                    height: 30px;
                    border: 5px solid #f3f3f3;
                    border-top: 5px solid #3498db;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                "></div>
                <p>Please wait while we retrieve the latest trends.</p>
                <script>
                    const style = document.createElement('style');
                    style.innerHTML = `
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                    `;
                    document.head.appendChild(style);
                    setTimeout(() => { location.reload(); }, 5000);
                </script>
            </body>
            </html>
        """)
    elif fetched_data:
        if "error" in fetched_data:
            return f"<h1>Error: {fetched_data['error']}</h1>"
        
        # Update here to check if the 5th trend is "Show more"
        trends_html = ''.join([f'<li>{topic}</li>' for topic in fetched_data['trending_topics'][:4]])

        # Check if there is a fifth trend (which should be "Show more")
        if len(fetched_data['trending_topics']) == 5:
            trends_html += f'<li><a href="/fetch_again">Show more</a></li>'

        return render_template_string(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Trending Topics</title>
            </head>
            <body style="display:flex;flex-direction:column;justify-content:center;align-items:center;">
                <h1>Trending Topics</h1>
                <ul>
                    {trends_html}
                </ul>
                <h4>IP Address: {fetched_data['ip_address']}</h4>
                <h2>JSON extract</h2>
                <pre>{json.dumps(fetched_data, indent=4, ensure_ascii=False)}</pre>
                <h4>Fetched at: {fetched_data['timestamp']}</h4>
                <button><a href="/fetch_again">Fetch again</a></button>
            </body>
            </html>
        """)
    else:
        fetching_trends = True
        threading.Thread(target=fetch_trending_topics).start()
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Fetching Trends...</title>
            </head>
            <body style="display:flex;flex-direction:column;justify-content:center;align-items:center;">
                <h1>Fetching trending topics...</h1>
                <div style="
                    margin: 50px auto;
                    width: 50px;
                    height: 50px;
                    border: 5px solid #f3f3f3;
                    border-top: 5px solid #3498db;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                "></div>
                <p>Please wait while we retrieve the latest trends.</p>
                <script>
                    const style = document.createElement('style');
                    style.innerHTML = `
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                    `;
                    document.head.appendChild(style);
                    setTimeout(() => { location.reload(); }, 5000);
                </script>
            </body>
            </html>
        """)

# Flask Route to Reset and Fetch Again
@app.route("/fetch_again")
def fetch_again():
    global fetching_trends, fetched_data, driver

    # Reset states
    fetching_trends = True
    fetched_data = None

    # Ensure the WebDriver session is properly closed
    if driver:
        try:
            driver.quit()
        except Exception as e:
            print(f"Error closing WebDriver: {e}")
        driver = None

    # Start a new thread to fetch trends
    threading.Thread(target=fetch_trending_topics).start()

    # Return loading spinner while fetching
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fetching Trends...</title>
        </head>
        <body style="display:flex;flex-direction:column;justify-content:center;align-items:center;">
            <h1>Fetching trending topics...</h1>
            <div style="
                margin: 50px auto;
                width: 50px;
                height: 50px;
                border: 5px solid #f3f3f3;
                border-top: 5px solid #3498db;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            "></div>
            <p>Please wait while we retrieve the latest trends.</p>
            <script>
                const style = document.createElement('style');
                style.innerHTML = `
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                `;
                document.head.appendChild(style);
                setTimeout(() => { location.href = '/'; }, 5000);
            </script>
        </body>
        </html>
    """)

# Graceful Shutdown
def shutdown_handler(signal, frame):
    global driver
    print("\nShutting down...")
    if driver:
        driver.quit()
        print("WebDriver closed.")
    print("END!")
    exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown_handler)
    print("Starting Flask server...")
    app.run(debug=True, port=8080)
