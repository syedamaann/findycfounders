from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import gradio as gr

def scroll_to_load_all_companies(driver):
    """Scroll down the page to load all companies."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for the page to load
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def scrape_twitter_urls(start_url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Added User Agent to avoid being blocked as a bot
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(start_url)
        time.sleep(3)
        
        # --- BLOCK 1: GET COMPANY LINKS ---
        company_links = []
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Fallback method (Most reliable for YC's current layout)
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            # Check if it looks like a company profile link
            if '/companies/' in href and href not in company_links:
                company_links.append(href)
        
        if not company_links:
            return [], 0, 0, 0, "Error: Could not find company links. Page structure may have changed."
        
        # --- BLOCK 2: SCROLLING ---
        if company_links:
            scroll_to_load_all_companies(driver)
            # Re-parse after scrolling to get all companies
            soup = BeautifulSoup(driver.page_source, "html.parser")
            all_links = soup.find_all('a', href=True)
            company_links = []
            for link in all_links:
                href = link['href']
                if '/companies/' in href and href not in company_links:
                    company_links.append(href)

        twitter_handles = []
        companies_with_no_twitter = 0

        # --- BLOCK 3: EXTRACT TWITTER HANDLES ---
        print(f"Found {len(company_links)} companies. Starting scrape...")

        for company_link in company_links:
            # handle case where link is relative or absolute
            if company_link.startswith("http"):
                 company_url = company_link
            else:
                 company_url = f"https://www.ycombinator.com{company_link}"

            driver.get(company_url)
            
            try:
                # FIX: Don't wait for a specific class that might change. Wait for the body.
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                company_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # FIX: Use CSS Selectors to find ANY link containing x.com or twitter.com
                social_links = company_soup.select('a[href*="x.com"], a[href*="twitter.com"]')
                
                found_on_page = False
                for link in social_links:
                    url = link['href']
                    # Avoid sharing intents (e.g., "share this page on twitter")
                    if "intent/tweet" not in url and "share" not in url:
                        if url not in twitter_handles:
                            twitter_handles.append(url)
                            found_on_page = True
                
                if not found_on_page:
                    companies_with_no_twitter += 1
            
            except Exception as e:
                print(f"Error scraping {company_url}: {e}")
                companies_with_no_twitter += 1
                continue
            
            # Be nice to the server
            time.sleep(1)

        return twitter_handles, len(company_links), len(twitter_handles), companies_with_no_twitter, None

    finally:
        driver.quit()

def run_gradio(start_url):
    result = scrape_twitter_urls(start_url)
    twitter_handles, total_companies, total_twitter, no_twitter, error_msg = result
    
    # Handle error case
    if error_msg:
        return f"<div style='border:1px solid #ff6b6b; padding:10px; color: #d63031;'><b>Error:</b> {error_msg}</div>"
    
    clickable_links = "<br>".join([f'<a href="{url}" target="_blank">{url}</a>' for url in twitter_handles])
    
    stats = f"""
    <br><b>Stats:</b><br>
    total companies found: {total_companies}<br>
    founders' twitter handles found: {total_twitter}<br>
    founders not on twitter: {no_twitter}
    """
    
    return f"<div style='border:1px solid #ddd; padding:10px;'>{clickable_links}</div>{stats}"

gr.Interface(
    fn=run_gradio,
    inputs=gr.Textbox(label="Start URL"),
    outputs=gr.HTML(label="Results"),
    title="Find Twitter handles of YC founders",
).launch(share=True)
