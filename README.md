# Twitter Trends Scraper

A Flask web app that scrapes Twitter's trending topics using Selenium WebDriver, stores the data in MongoDB, and displays it on a webpage. It supports refreshing the trends and graceful shutdown of the server.

## Features
- Scrapes Twitter's trending topics.
- Stores data in MongoDB.
- Displays trends on a web page with a loading spinner.
- Allows fetching new trends with a refresh button.

## Requirements
- Python 3.x
- Flask
- Selenium
- MongoDB
- ChromeDriver
- .env file for configuration

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/rohith-5/twitter_trends_selenium.git
   cd twitter_trends_selenium

2. Set up the .env file: Create a .env file in the root directory and add your Twitter credentials and MongoDB URI:

    TWITTER_USERNAME=your_username
    TWITTER_PASSWORD=your_password
    MONGO_URI=your_mongo_uri
    PROXY=your_proxy 


Running the App
Start the Flask server:

    python selenium_script.py
  Open your browser and go to http://localhost:8080 to view the trending topics.



Features in Action
    The app will display the latest Twitter trends.
    A loading spinner appears while the data is being fetched.
    Click "Fetch again" to refresh the trends.
    Graceful Shutdown
    The server can be gracefully stopped using Ctrl+C, ensuring WebDriver sessions are properly closed.

