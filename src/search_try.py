import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus, unquote
from readabilipy import simple_json_from_html_string
import trafilatura
import nltk
import os
import pickle
import uuid

# Ollama 配置
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss")


def clean_source_gpt35(source : str) -> str:
    for idx in range(8):
        try:
            prompt = f"Clean and refine the extracted text from a website. Remove any unwanted content such as headers, sidebars, and navigation menus. Retain only the main content of the page and ensure that the text is well-formatted and free of HTML tags, special characters, and any other irrelevant information. Refined text should contain the main intended readable text. Apply markdown formatting when outputting the answer.\n\nHere is the website:\n```html_text\n{source.strip()}```"
            
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "temperature": 0.0,
                    "stream": False,
                    "options": {
                        "num_predict": 1800,
                        "top_p": 1.0
                    }
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            break
        except Exception as e:
            print(f'Error while cleaning text with Ollama {e}')
            source = source[:-int(800*(1 + idx/2))]
            import time
            time.sleep(3 + idx**2)
    
    # Store the usage in the folder response_usages, with a random file name
    try:
        os.makedirs("response_usages", exist_ok=True)
        usage_info = {"model": OLLAMA_MODEL, "task": "clean_source"}
        pickle.dump(usage_info, open(f"response_usages/{uuid.uuid4()}.pkl", "wb"))
    except:
        pass

    tex = result['response'].strip()
    new_lines = [""]
    for line in tex.split('\n\n'):
        new_lines[-1] +=line+'\n'
        if len(nltk.sent_tokenize(line))!=1:
            new_lines.append("")
    new_lines = [x.strip() for x in new_lines]
    return "\n\n".join(new_lines)

def clean_source_text(text: str) -> str:
    return (
        text.strip()
        .replace("\n\n\n", "\n\n")
        .replace("\n\n", " ")
        .replace("  ", " ")
        .replace("\t", "")
        .replace("\n", "")
    )

import time
import sys
from pdb import set_trace as bp

try:
    from ddgs import DDGS
except Exception:
    DDGS = None


def summarize_text_identity(source, query) -> str:
    return source[:8000]


def fetch_search_html(url: str, headers: dict, retries: int = 3):
    last_err = None
    for i in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=12)
            text = r.text or ""
            # DuckDuckGo often returns 202/403 with html body; still parse it.
            if len(text) > 200:
                return text
            r.raise_for_status()
        except Exception as e:
            last_err = e
            time.sleep(1.2 * (i + 1))
    if last_err:
        raise last_err
    raise RuntimeError(f"Failed to fetch search page: {url}")


def collect_links_from_duckduckgo(soup: BeautifulSoup, links: list):
    # html.duckduckgo.com format
    for a in soup.find_all('a', class_='result__a'):
        href = a.get('href')
        if not href:
            continue
        if 'uddg=' in href:
            actual = unquote(href.split('uddg=')[1].split('&')[0])
            if actual.startswith('http') and actual not in links:
                links.append(actual)
        elif href.startswith('http') and href not in links:
            links.append(href)

    # lite.duckduckgo.com format
    for a in soup.find_all('a'):
        href = a.get('href')
        if not href:
            continue
        if href.startswith('//'):
            href = 'https:' + href
        if 'duckduckgo.com/l/?' in href and 'uddg=' in href:
            actual = unquote(href.split('uddg=')[1].split('&')[0])
            if actual.startswith('http') and actual not in links:
                links.append(actual)
        elif href.startswith('http') and 'duckduckgo.com' not in href and href not in links:
            links.append(href)


def collect_links_from_ddgs(query: str, links: list, target_link_count: int):
    if DDGS is None:
        return
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max(20, target_link_count))
            for item in results:
                href = item.get('href') or item.get('url')
                if href and href.startswith('http') and href not in links:
                    links.append(href)
                if len(links) >= target_link_count:
                    break
    except Exception as e:
        print(f"[DEBUG] DDGS search failed: {e}", file=sys.stderr)


def extract_source_text(link: str, headers: dict):
    """Fetch page html and extract main text with robust fallbacks."""
    response = requests.get(link, headers=headers, timeout=20)
    response.raise_for_status()
    page_html = response.text

    source_text = trafilatura.extract(page_html)
    if source_text is None:
        downloaded = trafilatura.fetch_url(link)
        if downloaded:
            source_text = trafilatura.extract(downloaded)

    if source_text is None:
        return None, None, None

    title = None
    html_text = None
    try:
        parsed = simple_json_from_html_string(page_html)
        title = parsed.get('title')
        html_text = parsed.get('content')
    except Exception:
        title = None
        html_text = None

    if not title:
        try:
            soup = BeautifulSoup(page_html, 'html.parser')
            title = soup.title.string.strip() if soup.title and soup.title.string else link
        except Exception:
            title = link

    return source_text, title, html_text


def search_handler(req, source_count = 8):
    query = req
    print(f"[DEBUG] Starting search for: {query}", file=sys.stderr)
    target_link_count = max(source_count * 4, source_count + 12)

    # GET LINKS - 使用 DuckDuckGo（对爬虫更友好）
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    links = []
    
    # 尝试 DuckDuckGo
    try:
        print(f"[DEBUG] Trying DuckDuckGo search...", file=sys.stderr)
        before_ddgs = len(links)
        collect_links_from_ddgs(query, links, target_link_count)
        print(f"[DEBUG] DDGS added {len(links)-before_ddgs} links (total {len(links)})", file=sys.stderr)

        encoded_q = quote_plus(query)
        if len(links) < target_link_count:
            ddg_urls = [f"https://lite.duckduckgo.com/lite/?q={encoded_q}&s={s}" for s in range(0, 180, 30)]
            ddg_urls += [
                f"https://duckduckgo.com/html/?q={encoded_q}",
                f"https://html.duckduckgo.com/html/?q={encoded_q}",
            ]
            for ddg_url in ddg_urls:
                html = fetch_search_html(ddg_url, headers=headers)
                soup = BeautifulSoup(html, 'html.parser')
                before = len(links)
                collect_links_from_duckduckgo(soup, links)
                print(f"[DEBUG] {ddg_url} added {len(links)-before} links (total {len(links)})", file=sys.stderr)
                if len(links) >= target_link_count:
                    break
    except Exception as e:
        print(f"[DEBUG] DuckDuckGo search failed: {e}", file=sys.stderr)
    
    # 如果 DuckDuckGo 失败，尝试 Google（可能会被阻止）
    if len(links) == 0:
        print(f"[DEBUG] Falling back to Google search...", file=sys.stderr)
        try:
            response = requests.get(f"https://www.google.com/search?q={quote_plus(query)}", headers=headers, timeout=10)
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            link_tags = soup.find_all('a')
            
            print(f"[DEBUG] Google found {len(link_tags)} link tags", file=sys.stderr)
            
            for link in link_tags:
                href = link.get('href')
                if href:
                    cleaned_href = None
                    if href.startswith('/url?q='):
                        cleaned_href = href.replace('/url?q=', '').split('&')[0]
                    elif href.startswith('http://') or href.startswith('https://'):
                        cleaned_href = href.split('&')[0]
                    
                    if cleaned_href and cleaned_href not in links and cleaned_href.startswith('http'):
                        links.append(cleaned_href)
                        print(f"[DEBUG] Found link: {cleaned_href}", file=sys.stderr)
        except Exception as e:
            print(f"[DEBUG] Google search failed: {e}", file=sys.stderr)

    print(f"[DEBUG] Total links collected: {len(links)}", file=sys.stderr)
    
    exclude_list = ["google", "facebook", "twitter", "instagram", "youtube", "tiktok","quora", "duckduckgo"]
    filtered_links = []
    
    for link in links:
        try:
            hostname = urlparse(link).hostname
            if hostname:
                parts = hostname.split('.')
                if len(parts) >= 2:
                    domain = parts[-2]  # 获取主域名
                    if domain not in exclude_list:
                        filtered_links.append(link)
        except Exception as e:
            print(f"[DEBUG] Error parsing {link}: {e}", file=sys.stderr)
            continue

    print(f"[DEBUG] Filtered links: {len(filtered_links)}", file=sys.stderr)
    final_links = filtered_links#[:source_count]

    # SCRAPE TEXT FROM LINKS
    sources = []

    for link in final_links:
        print(f'[DEBUG] Will be loading link {link}', file=sys.stderr)
        try:
            source_text, source_title, html_text = extract_source_text(link, headers)
            if source_text is None:
                print(f'[DEBUG] Skipping {link} - no text extracted', file=sys.stderr)
                continue
        except Exception as e:
            print(f'[DEBUG] Exception loading {link}: {e}', file=sys.stderr)
            continue
        print(f'[DEBUG] Link Loaded: {link}', file=sys.stderr)
        if html_text is not None and len(html_text) < 400:
            print(f'[DEBUG] Skipping {link} - extracted html content too short', file=sys.stderr)
            continue

        if source_text:
            source_text = clean_source_text(source_text)
            print(f'[DEBUG] Going to call Ollama for cleaning...', file=sys.stderr)
            raw_source = source_text
            try:
                source_text = clean_source_gpt35(source_text[:8000])
                summary_text = summarize_text_identity(source_text, query)
                sources.append({
                    'url': link,
                    'text': f'Title: {source_title}\nSummary:' + summary_text,
                    'raw_source': raw_source,
                    'source': source_text,
                    'summary': summary_text
                })
                print(f'[DEBUG] Successfully processed source {len(sources)}/{source_count}', file=sys.stderr)
            except Exception as e:
                print(f'[DEBUG] Error processing source: {e}', file=sys.stderr)
                continue
        if len(sources) == source_count:
            break
    
    print(f"[DEBUG] Final sources count: {len(sources)}", file=sys.stderr)
    return {'sources': sources}
    
if __name__ == '__main__':
    import sys
    search_handler('What is Generative Engine Optimization?')
    import json
    print(json.dumps(search_handler(sys.argv[1]), indent = 2))
