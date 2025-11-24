import requests
import csv
import os
import pandas as pd
import re

CSV_FILE = "lotto_numbers.csv"
# 엑셀 다운로드 URL (실제로는 HTML 테이블 형식의 파일)
DOWNLOAD_URL = "https://www.dhlottery.co.kr/gameResult.do?method=allWinExel&gubun=byWin&nowPage=&drwNoStart={}&drwNoEnd={}"
LATEST_ROUND_URL = "https://www.dhlottery.co.kr/gameResult.do?method=byWin"

def get_last_saved_round():
    if not os.path.exists(CSV_FILE):
        return 0
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            return 0
        # CSV 파일이 최신 회차가 위에 있다고 가정 (내림차순)
        return int(rows[0]["round"])

def get_latest_round_from_web():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(LATEST_ROUND_URL, headers=headers)
        if response.status_code != 200:
            return None
        # "<h4>1199회 당첨결과</h4>" 패턴 찾기
        match = re.search(r'<h4>(\d+)회 당첨결과</h4>', response.text)
        if match:
            return int(match.group(1))
        return None
    except Exception as e:
        print(f"Error fetching latest round: {e}")
        return None

def update_lotto():
    last_saved = get_last_saved_round()
    latest_web = get_latest_round_from_web()
    
    if latest_web is None:
        print("Could not determine latest round from web.")
        return

    print(f"Last saved round: {last_saved}")
    print(f"Latest web round: {latest_web}")

    if latest_web <= last_saved:
        print("Already up to date.")
        return

    start_round = last_saved + 1
    end_round = latest_web
    
    print(f"Downloading data from round {start_round} to {end_round}...")
    
    download_url = DOWNLOAD_URL.format(start_round, end_round)
    
    try:
        # pandas로 HTML 테이블 읽기 (dhlottery 엑셀은 HTML 형식임)
        # header=1: 두 번째 줄(인덱스 1)을 헤더로 사용 (첫 번째 줄은 결합된 셀 등일 수 있음)
        dfs = pd.read_html(download_url, header=1, encoding='euc-kr') 
        
        if not dfs:
            print("No tables found in the downloaded file.")
            return
            
        df = dfs[1] # 보통 두 번째 테이블이 실제 데이터임 (첫 번째는 헤더나 다른 정보일 수 있음)
        # 만약 테이블 구조가 바뀌었다면 dfs[0]일 수도 있으니 확인 필요하지만, 보통 본문 데이터는 뒤에 옴
        # 안전하게 '회차' 컬럼이 있는 테이블을 찾자
        
        target_df = None
        for d in dfs:
            if '회차' in d.columns:
                target_df = d
                break
        
        if target_df is None:
            # 헤더가 0번째 줄일 수도 있음
            dfs = pd.read_html(download_url, header=0, encoding='euc-kr')
            for d in dfs:
                if '회차' in d.columns:
                    target_df = d
                    break
        
        if target_df is None:
            print("Could not find data table.")
            return
            
        df = target_df
        
        new_rows = []
        for _, row in df.iterrows():
            try:
                # 데이터 추출 (NaN 체크)
                if pd.isna(row['회차']):
                    continue
                    
                round_no = int(row['회차'])
                date_str = str(row['추첨일']).replace('.', '.') # YYYY.MM.DD 형식 유지
                
                # 당첨번호와 보너스 번호 추출
                # 컬럼명이 '1', '2', '3', '4', '5', '6', '보너스' 인지 확인
                # 혹은 위치 기반으로 추출 (뒤에서 7개)
                
                # iloc을 사용하여 안전하게 추출 (마지막 7개 컬럼이 번호들임)
                # 구조: 년도, 회차, 추첨일, ... , 1, 2, 3, 4, 5, 6, 보너스
                n1 = int(row.iloc[-7])
                n2 = int(row.iloc[-6])
                n3 = int(row.iloc[-5])
                n4 = int(row.iloc[-4])
                n5 = int(row.iloc[-3])
                n6 = int(row.iloc[-2])
                bonus = int(row.iloc[-1])
                
                new_rows.append({
                    "round": round_no,
                    "n1": n1,
                    "n2": n2,
                    "n3": n3,
                    "n4": n4,
                    "n5": n5,
                    "n6": n6,
                    "bonus": bonus,
                    "dates": date_str
                })
            except (ValueError, IndexError) as e:
                print(f"Skipping row due to error: {e}")
                continue

        if new_rows:
            # 회차 내림차순 정렬
            new_rows.sort(key=lambda x: x["round"], reverse=True)
            
            # 기존 데이터 읽기
            existing_rows = []
            if os.path.exists(CSV_FILE):
                with open(CSV_FILE, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    existing_rows = list(reader)
            
            # 중복 제거 및 병합
            existing_rounds = {int(r["round"]) for r in existing_rows}
            final_new_rows = [r for r in new_rows if r["round"] not in existing_rounds]
            
            if not final_new_rows:
                print("No new rounds to add (all duplicates).")
                return

            all_rows = final_new_rows + existing_rows
            
            # CSV 저장
            with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
                fieldnames = ["round", "n1", "n2", "n3", "n4", "n5", "n6", "bonus", "dates"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_rows)
                
            print(f"Successfully updated {len(final_new_rows)} rounds.")
        else:
            print("No valid data found in the downloaded file.")

    except Exception as e:
        print(f"Error processing excel file: {e}")

if __name__ == "__main__":
    update_lotto()
