import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen
import time
from bs4 import BeautifulSoup
import signal
import sys
from threading import Event

# Stop event to signal threads to terminate
stop_event = Event()
def signal_handler(sig, frame):
    """Handle keyboard interrupt (Ctrl+C)."""
    print("\n[INFO] KeyboardInterrupt detected. Gracefully stopping...")
    stop_event.set()  # Signal threads to stop

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

def get_html(url):
    """HTML 데이터를 UTF-8로 디코딩하여 가져옴"""
    if stop_event.is_set():
        raise KeyboardInterrupt

    try:
        response = urlopen(url)
        html = response.read().decode("utf-8", errors="replace")
        return html
    except Exception as e:
        print(f"Error: {e}. Retrying...")
        time.sleep(1)
        return get_html(url)

def parse_paper_details(pmid, current, total):
    """PMID에 대한 상세 정보를 크롤링"""
    if stop_event.is_set():
        raise KeyboardInterrupt  # Gracefully handle stop signal

    try:
        url_paperpage = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        html = get_html(url_paperpage)
        soup = BeautifulSoup(html, "html.parser")

        # Title
        title = soup.find("h1", {"class": "heading-title"})
        title = title.text.strip() if title else "No title"

        # Authors
        author_section = soup.find("div", {"class": "authors-list"})
        authors = []
        if author_section:
            for author_item in author_section.find_all("span", {"class": "authors-list-item"}):
                author_name_tag = author_item.find("a", {"class": "full-name"})
                if author_name_tag:
                    authors.append(author_name_tag.text.strip())
        authors = ", ".join(authors) if authors else "No authors"

        # Affiliations
        affiliation_section = soup.find("ul", {"class": "item-list"})
        affiliations = []
        if affiliation_section:
            for li in affiliation_section.find_all("li"):
                sup_tag = li.find("sup", {"class": "key"})
                if sup_tag:
                    sup_tag.decompose()
                affiliations.append(li.get_text(strip=True))
        affiliations = "; ".join(affiliations) if affiliations else "No affiliations"

        # Journal
        journal = soup.find("span", {"class": "journal"})
        journal = journal.text.strip() if journal else "No journal"

        # Publication Date
        pub_date = soup.find("span", {"class": "cit"})
        pub_date = pub_date.text.split(";")[0].strip() if pub_date else "No date"

        # Abstract
        abstract_section = soup.find("div", {"class": "abstract-content selected", "id": "eng-abstract"})
        abstract = abstract_section.get_text(separator=" ", strip=True) if abstract_section else "No abstract"

        # Keywords
        keywords_section = soup.find("div", {"class": "abstract"})
        if keywords_section and "Keywords:" in keywords_section.text:
            keywords = keywords_section.text.split("Keywords:")[1].strip()
        else:
            keywords = "No keywords"

        # DOI
        doi_value = "No DOI"
        all_links = soup.find_all("a", href=True)
        for link in all_links:
            href = link["href"]
            if "doi.org" in href:
                doi_value = href.split("doi.org/")[-1]
                break
        global i
        progress = (i / total) * 100
        print(f"[INFO] Progress: {progress:.2f}% ({i}/{total})")
        i += 1
        return {
            "PMID": pmid,
            "Title": title,
            "Authors": authors,
            "Affiliations": affiliations,
            "Journal": journal,
            "Publication Date": pub_date,
            "Abstract": abstract,
            "Keywords": keywords,
            "URL": url_paperpage,
            "DOI": doi_value,
        }
    except KeyboardInterrupt:
        raise  # Re-raise interrupt for graceful handling
    except Exception as e:
        print(f"[ERROR] Failed to process PMID {pmid}: {e}")
        return None

def fetch_details_and_resume(file_path):
    """중단된 작업을 재개"""
    global stop_event
    # CSV 파일 로드
    df = pd.read_csv(file_path)
    print(f"[INFO] Loaded file: {file_path}")
    
    # 처리되지 않은 행 필터링
    incomplete_rows = df[df["Title"].isnull()]
    total_remaining = len(incomplete_rows)
    
    if total_remaining == 0:
        print("[INFO] No remaining rows to process.")
        return

    print(f"[INFO] Remaining rows to process: {total_remaining}")
    results = []

    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_index = {
                executor.submit(parse_paper_details, row["PMID"], i + 1, total_remaining): i
                for i, row in incomplete_rows.iterrows()
            }

            for future in as_completed(future_to_index):
                index = future_to_index[future]
                if stop_event.is_set():
                    print("\n[INFO] Stopping further tasks...")
                    break  # Stop processing if interrupted

                try:
                    paper_details = future.result()
                    if paper_details:
                        results.append((index, paper_details))
                except KeyboardInterrupt:
                    print("\n[INFO] Interrupt detected. Stopping tasks.")
                    break
                except Exception as e:
                    print(f"[ERROR] Exception while processing index {index}: {e}")
    except KeyboardInterrupt:
        print("\n[INFO] KeyboardInterrupt detected. Saving progress...")
        save_partial_results(file_path, df, results)
        sys.exit(0)

    # 결과를 DataFrame에 업데이트
    for index, details in results:
        for key, value in details.items():
            df.at[index, key] = value

    # 저장
    df.to_csv(file_path, index=False)
    print(f"[INFO] Updated CSV saved to {file_path}")

def save_partial_results(file_path, df, results):
    """진행 사항을 파일에 저장"""
    for index, details in results:
        for key, value in details.items():
            df.at[index, key] = value
    df.to_csv(file_path, index=False)
    print(f"[INFO] Partial progress saved to {file_path}")

if __name__ == "__main__":
    i = 1
    input_file2 = "./DONE_합성생물학.csv"  # 작업할 파일 경로
    try:
        fetch_details_and_resume(input_file2)
    except KeyboardInterrupt:
        print("[INFO] Program interrupted by user. Progress saved.")
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
    
