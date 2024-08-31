from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
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
    
    service = ChromeService(executable_path='./chromedriver')  # Replace with your WebDriver path
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.get(start_url)
    
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "._company_86jzd_338")))
    except TimeoutException:
        driver.quit()
        return [], "Error: Timed out waiting for page to load", 0, 0
    
    # Scroll to load all companies
    scroll_to_load_all_companies(driver)

    # Parse the main page to get company links
    soup = BeautifulSoup(driver.page_source, "html.parser")
    company_links = [a['href'] for a in soup.select("._company_86jzd_338")]

    twitter_handles = []
    companies_with_no_twitter = 0

    # Iterate through each company link
    for company_link in company_links:
        company_url = f"https://www.ycombinator.com{company_link}"
        driver.get(company_url)
        
        try:
            # Wait for the company page to load and check for the presence of the Twitter icon
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".bg-image-twitter")))
            
            # Parse the company page
            company_soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Find the Twitter URL
            twitter_element = company_soup.find("a", class_="inline-block h-5 w-5 bg-contain bg-image-twitter")
            
            if twitter_element and 'href' in twitter_element.attrs:
                twitter_url = twitter_element['href']
                twitter_handles.append(twitter_url)
            else:
                companies_with_no_twitter += 1
        
        except TimeoutException:
            companies_with_no_twitter += 1
            continue  # Move on to the next company URL
        
        # Optional: Sleep to avoid too rapid requests
        time.sleep(1)

    driver.quit()
    
    return twitter_handles, len(company_links), len(twitter_handles), companies_with_no_twitter

def run_gradio(start_url):
    twitter_handles, total_companies, total_twitter, no_twitter = scrape_twitter_urls(start_url)
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
