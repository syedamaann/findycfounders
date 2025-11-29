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
from curl_cffi import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def scrape_company_fast(company_link):
    """Worker function to scrape a single company concurrently."""
    # handle case where link is relative or absolute
    if company_link.startswith("http"):
        url = company_link
    else:
        url = f"https://www.ycombinator.com{company_link}"

    try:
        # impersonate="chrome" tricks Cloudflare into thinking we are a real browser
        response = requests.get(url, impersonate="chrome", timeout=10)
        
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Fast CSS selector for social links
        social_links = soup.select('a[href*="x.com"], a[href*="twitter.com"]')
        
        found_handles = []
        for link in social_links:
            href = link.get('href', '')
            if "intent/tweet" not in href and "share" not in href:
                found_handles.append(href)
                
        return list(set(found_handles)) # Remove duplicates
        
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        return None

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

        # Close Selenium driver early as we don't need it for individual pages anymore
        driver.quit()

        twitter_handles = []
        companies_with_no_twitter = 0

        # --- BLOCK 3: EXTRACT TWITTER HANDLES (FAST PARALLEL) ---
        print(f"Found {len(company_links)} companies. Starting fast scrape with curl_cffi...")
        
        # We scrape 10 companies at the same time
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            future_to_url = {executor.submit(scrape_company_fast, link): link for link in company_links}
            
            for i, future in enumerate(as_completed(future_to_url)):
                handles = future.result()
                
                if handles:
                    twitter_handles.extend(handles)
                else:
                    companies_with_no_twitter += 1
                
                # Optional: Print progress
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1}/{len(company_links)}")

        # Remove duplicates from the final list while preserving order (optional)
        twitter_handles = list(set(twitter_handles))

        return twitter_handles, len(company_links), len(twitter_handles), companies_with_no_twitter, None

    except Exception as e:
        return [], 0, 0, 0, f"Unexpected error: {str(e)}"
    
    finally:
        # Ensure driver is closed if it wasn't closed earlier
        try:
            driver.quit()
        except:
            pass

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
