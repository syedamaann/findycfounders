# Find YC Founders



https://github.com/user-attachments/assets/a1ddf602-9604-433d-bb88-0749f20e9192

To make it easier to find and analyze Twitter handles of YC founders: I used Selenium for browsing, such as scrolling and clicking through company profiles on the YC site, and BeautifulSoup to parse the HTML and locate Twitter links. Gradio provides a simple interface where you enter a start URL and see the results. This approach automates the process, making it more accurate and saving time. The Selenium WebDriver runs in headless mode, so no browser window pops up, keeping things lightweight and fast.


### Setup

1. **Install Dependencies**:
   - Install Python if not already installed.
   - Install required libraries:
     ```bash
     pip install selenium beautifulsoup4 gradio
     ```
   - Download Chrome WebDriver and place it in the project directory.
   - Grant execution permissions to the WebDriver:
     ```bash
     chmod +x ./chromedriver
     ```

2. **Run the Script**:
   - Execute the script to launch the Gradio interface:
     ```bash
     python your_script_name.py
     ```
   - Enter the start URL in the Gradio interface to begin scraping.

### Troubleshooting

- **WebDriver Errors**: Ensure that the ChromeDriver version matches your installed Chrome browser version and that the driver has execution permissions.
- **Timeout Issues**: If the script times out, consider increasing the `WebDriverWait` time or checking your internet connection for stability.

In the future, if the script fails to find some Twitter handles, check for changes in the website’s structure and update the CSS selectors in the script accordingly.
