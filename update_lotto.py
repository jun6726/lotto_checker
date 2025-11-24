import requests
import csv
import os
import pandas as pd
import re

CSV_FILE = "lotto_numbers.csv"
# 엑셀 다운로드 URL (실제로는 HTML 테이블 형식)
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

def update_lotto():
    last_saved = get_last_saved_round()
    
    # 최신 회차를 웹에서 스크래핑하는 대신, 충분히 큰 숫자로 요청하면 
    # 서버가 알아서 최신 회차까지만 반환해주는 것을 확인했습니다.
    start_round = last_saved + 1
    end_round = 9999 # 충분히 큰 수
    
    print(f"Last saved round: {last_saved}")
    print(f"Downloading data from round {start_round} to {end_round} (max)...")
    
    download_url = DOWNLOAD_URL.format(start_round, end_round)
    
    try:
        # SSL 인증서 오류 방지를 위해 requests로 먼저 다운로드
        # verify=False 옵션 사용
        import urllib3
        from io import StringIO
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.get(download_url, verify=False)
        if response.status_code != 200:
            print(f"Failed to download file. Status code: {response.status_code}")
            return
            
        # 인코딩 설정 (동행복권 사이트는 euc-kr 사용)
        response.encoding = 'euc-kr'
            
        # pandas로 HTML 테이블 읽기 (response.text 사용)
        # header=None으로 읽어서 구조적 문제 회피
        dfs = pd.read_html(StringIO(response.text), header=None) 
        
        if not dfs:
            print("No tables found in the downloaded file.")
            return
            
        # 데이터가 있는 테이블 찾기
        # '회차'만 찾으면 제목 테이블(Table 0)이 걸릴 수 있음.
        # '추첨일'이나 '당첨번호'가 포함된 테이블을 찾는다.
        target_df = None
        for i, d in enumerate(dfs):
            # 상위 5행을 문자열로 변환하여 검색
            head_str = d.head().astype(str)
            if head_str.apply(lambda x: x.str.contains('추첨일').any()).any() and head_str.apply(lambda x: x.str.contains('당첨번호').any()).any():
                target_df = d
                print(f"Found data table at index {i}")
                break
        
        if target_df is None:
            print("Could not find table with '추첨일' and '당첨번호'. Trying fallback.")
            # 제목 테이블(Table 0)을 피하기 위해 Table 1을 우선 시도
            if len(dfs) > 1:
                target_df = dfs[1]
                print("Using Table 1 as fallback.")
            else:
                target_df = dfs[0]
                print("Using Table 0 as fallback.")
            
        df = target_df
        # print(df.head()) # 디버깅용
        
        new_rows = []
        for idx, row in df.iterrows():
            try:
                # 데이터 유효성 검사: 회차(1번 컬럼)가 숫자인지 확인
                val = str(row[1])
                if not val.isdigit():
                    # print(f"Row {idx}: '{val}' is not a digit. Skipping.")
                    continue
                    
                round_no = int(val)
                
                # 이미 저장된 회차보다 작거나 같으면 스킵 (중복 방지)
                if round_no <= last_saved:
                    # print(f"Row {idx}: Round {round_no} <= {last_saved}. Skipping.")
                    continue

                date_str = str(row[2]) # YYYY.MM.DD
                
                # 당첨번호 추출 (뒤에서 7개 컬럼)
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
                print(f"Found new round: {round_no}")
            except (ValueError, IndexError) as e:
                print(f"Error parsing row {idx}: {e}")
                continue

        if new_rows:
            # ==========================================
            # [CSV 갱신 부분]
            # ==========================================
            
            # 1. 새 데이터를 회차 내림차순 정렬
            new_rows.sort(key=lambda x: x["round"], reverse=True)
            
            # 2. 기존 데이터 읽기
            existing_rows = []
            if os.path.exists(CSV_FILE):
                with open(CSV_FILE, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    existing_rows = list(reader)
            
            # 3. 중복 제거 (이미 있는 회차는 제외)
            existing_rounds = {int(r["round"]) for r in existing_rows}
            final_new_rows = [r for r in new_rows if r["round"] not in existing_rounds]
            
            if not final_new_rows:
                print("No new rounds to add (all duplicates).")
                return

            # 4. 새 데이터 + 기존 데이터 합치기
            all_rows = final_new_rows + existing_rows
            
            # 5. CSV 파일에 쓰기 (덮어쓰기)
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
