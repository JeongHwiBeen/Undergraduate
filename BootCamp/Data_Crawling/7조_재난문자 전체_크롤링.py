# -*- coding: utf-8 -*-
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import warnings
warnings.filterwarnings('ignore')

options = webdriver.ChromeOptions() # 어떻게 접속하겠다는 옵션
options.add_argument('--no-sandbox') # 보안 기능인 샌드박스 비활성화
options.add_argument('--disable-dev-shm-usage') #dev/shm 디렉토리 사용 안함

service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service = service, options=options)

def m_collector(currentPage):
    
    # 기본 셋팅 - 1페이지부터 시작
    
    url = f'https://www.safetydata.go.kr/disaster-data/disasterNotification?searchStartDttm=&searchEndDttm=&keyword=&orderBy=&currentPage={currentPage}&cntPerPage=10&pageSize=10'

    driver.get(url)
    html_source = driver.page_source 
    soup = BeautifulSoup(html_source,'html.parser')
    pre_total = soup.find('p', {'class': 'board-count'}).text
    total = int(re.sub('[^0-9]','', pre_total))
    
    if total % 10 == 0:
        last_page = total // 10
    else:
        last_page = (total // 10) + 1
        
    data_pages = []
    print('재난문자 수집 시작...') 
        
    for i in range( 1, last_page + 1 ):
        SCROLL_PAUSE_TIME = 3
        currentPage = str(i)
        new_url = f'https://www.safetydata.go.kr/disaster-data/disasterNotification?searchStartDttm=&searchEndDttm=&keyword=&orderBy=&currentPage={currentPage}&cntPerPage=10&pageSize=10'
                
        driver.get(new_url)   # url 띄우는거
        time.sleep(3) # 3정도 쉬기
        
        # 사람인 척 하기 - > 동적 이벤트 주기 - > 스크롤 내리기(자바스크립트 명령어)
        driver.execute_script('window.scrollTo(0,800)')
        time.sleep(3)
        
        # 데이터 수집 시작
        html_source = driver.page_source  # 열려있는 html소스 받기
        soup = BeautifulSoup(html_source,'html.parser')
        
        # 제목 추출
        titles = soup.find_all('a', {'class':'tableHover'})
        title_list = [title.text for title in titles] # for문은 리스트안에서 실행

        # 등록일 추출
        crol_dates = soup.find_all('td', {'class':'cell-date'})
        crol_list = [ crol_date.text for crol_date in crol_dates ]
        
        #데이터 프레임 저장    
        df = pd.DataFrame({'제목':title_list, '등록일':crol_list})
        print(f'{i}페이지 자료 수집 완료')
        data_pages.append(df)

        
    data = pd.concat(data_pages, ignore_index=True)
    data.to_csv(f'재난문자_.csv', encoding='utf-8-sig')
    
    print('문자 수집 완료')


m_collector(1)

driver.close()
