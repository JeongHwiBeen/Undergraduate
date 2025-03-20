from urllib.request import urlopen
from urllib.parse import quote
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import pandas as pd

def get_html(url):
    """HTML 데이터를 UTF-8로 디코딩하여 가져옴"""
    try:
        response = urlopen(url)
        html = response.read().decode("utf-8", errors="replace")
        return html
    except Exception as e:
        print(f"Error: {e}. Retrying...")
        time.sleep(1)
        return get_html(url)

def load_search_terms_with_names(file_path):
    """Load search terms and corresponding names from a CSV file."""
    try:
        data = pd.read_excel(file_path)
        print("[DEBUG] File preview:")
        print(data.head())  # 파일 내용을 확인
    except FileNotFoundError as e:
        print(f"[ERROR] File not found: {e}")
        return [], []
    except Exception as e:
        print(f"[ERROR] Failed to load file: {e}")
        return [], []

    try:
        search_terms = data.iloc[0:, 9].dropna().tolist()  # J열에서 검색식 추출
        file_names = data.iloc[0:, 2].dropna().tolist()  # C열에서 파일 이름 추출
    except KeyError as e:
        print(f"[ERROR] Column not found: {e}")
        return [], []

    if len(search_terms) != len(file_names):
        print("[ERROR] Search terms and file names count mismatch!")
        return [], []

    print(f"[DEBUG] Search terms loaded: {search_terms}")
    print(f"[DEBUG] File names loaded: {file_names}")
    return search_terms, file_names

def generate_date_ranges(years):
    date_ranges = []
    for year in years:
        date_ranges.append((f"{year}/01/01", f"{year}/03/31"))
        date_ranges.append((f"{year}/04/01", f"{year}/06/30"))
        if year == 2024:  
            date_ranges.append((f"{year}/07/01", f"{year}/08/31"))
        else:
            date_ranges.append((f"{year}/07/01", f"{year}/09/30"))
            date_ranges.append((f"{year}/10/01", f"{year}/12/31"))
    return date_ranges

def update_search_term_with_date(search_base, start_date, end_date):
    """기존 날짜 조건을 제거하고 새 날짜 조건을 추가."""
    if "PDAT" in search_base:
        search_base = search_base.split("AND")
        del search_base[-1]
        merged_search_base = ''.join(search_base)
        return f"{merged_search_base} AND ({start_date}[PDAT] : {end_date}[PDAT])"
    elif "Date - Publication" in search_base:
        search_base = search_base.split("AND")
        del search_base[-1]
        merged_search_base = ''.join(search_base)
        return f"{merged_search_base} AND ({start_date}[Date - Publication] : {end_date}[Date - Publication])"
    else:
        raise ValueError("Search term does not contain a valid date field.")

def fetch_page_pmids(url, page_number):
    """특정 페이지에서 PMID 추출"""
    try:
        html = get_html(url)
        soup = BeautifulSoup(html, "html.parser")
        titles = soup.find_all("a", {"class": "docsum-title"})
        pmids = [title["data-article-id"] for title in titles]
        print(f"[INFO] Page {page_number} fetched successfully.")
        return pmids
    except Exception as e:
        print(f"[ERROR] Failed to fetch page {page_number}: {e}")
        return []

def crawling_pmid(searchwordlist):
    """검색어를 기반으로 PMID 추출"""
    pmids = set()

    for searchword in searchwordlist:
        print("[INFO] Starting scraping for search word...")
        url_searchpage = base_url + "?term=" + quote(searchword)
        first_page = get_html(url_searchpage)
        soup = BeautifulSoup(first_page, "html.parser")
        pagination = soup.find("label", {"class": "of-total-pages"})

        if pagination:
            total_pages_text = pagination.text.strip().split()[-1]
            total_pages = int(total_pages_text.replace(",", ""))
        else:
            total_pages = 1

        print(f"[INFO] Total pages to scrape: {total_pages}")

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_page = {
                executor.submit(fetch_page_pmids, base_url + f"?term={quote(searchword)}&page={i + 1}", i + 1): i + 1
                for i in range(total_pages)
            }

            for future in as_completed(future_to_page):
                page_number = future_to_page[future]
                try:
                    page_pmids = future.result()
                    pmids.update(page_pmids)
                    print(f"[INFO] Page {page_number} processed.")
                except Exception as e:
                    print(f"[ERROR] Exception while processing page {page_number}: {e}")

    return list(pmids)

def save_results_to_csv(filename, pmids):
    """PMID를 CSV 파일로 저장."""
    df = pd.DataFrame(pmids, columns=["PMID"])
    df["Title"] = ""
    df["Authors"] = ""
    df["Affiliations"] = ""
    df["Journal"] = ""
    df["Publication Date"] = ""
    df["Abstract"] = ""
    df["Keywords"] = ""
    df["URL"] = ""
    df["DOI"] = ""
    df.to_csv(filename, index=False)
    print(f"[INFO] Results saved to {filename}")

def crawling_pmid_by_date_ranges(date_ranges, search_bases):
    all_pmids = []
    for search_base in search_bases:
        for start_date, end_date in date_ranges:
            try:
                search_term = update_search_term_with_date(search_base, start_date, end_date)
            except ValueError as e:
                print(f"[ERROR] {e}")
                continue

            print(f"[INFO] Crawling for date range: {start_date} to {end_date}")
            pmids = crawling_pmid([search_term])
            print(f"[INFO] {start_date} to {end_date}: {len(pmids)} PMIDs collected.")
            all_pmids.extend(pmids)

    print(f"[INFO] Total PMIDs collected: {len(all_pmids)}")
    return all_pmids

if __name__ == "__main__":
    start_time = time.time()

    # 기본 설정
    base_url = "https://pubmed.ncbi.nlm.nih.gov/"
    input_file = "./Pubmed_progress.xlsx"

    # 검색식과 파일 이름 로드
    search_base, file_names = load_search_terms_with_names(input_file)
    print(f"[INFO] Loaded {len(search_base)} search terms and file names.")

    # 연도별 3개월 단위로 날짜 범위 생성
    years = range(2012, 2025)
    date_ranges = generate_date_ranges(years)
    
    # 검색식별로 PMID 추출 및 저장
    for i, (search_term, file_name) in enumerate(zip(search_base, file_names), start=1):
        print(f"[INFO] Processing search term {i}/{len(search_base)}...")
        pmids = crawling_pmid_by_date_ranges(date_ranges, [search_term])
        pmids = list(set(pmids))
        print(f"[INFO] {len(pmids)} PMIDs collected for search term {i}.")
        
        # 파일 이름 지정
        output_file = f"{file_name}.csv"
        save_results_to_csv(output_file, pmids)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"[INFO] Total elapsed time: {elapsed_time:.2f} seconds")