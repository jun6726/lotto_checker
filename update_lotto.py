import requests
import csv
import os

CSV_FILE = "lotto_numbers.csv"
API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"

def get_last_round():
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
    last_round = get_last_round()
    current_round = last_round + 1
    new_rows = []
    
    print(f"Current last round: {last_round}")
    
    while True:
        print(f"Checking round {current_round}...")
        try:
            response = requests.get(API_URL.format(current_round))
            if response.status_code != 200:
                print("Failed to connect to API")
                break
                
            data = response.json()
            if data.get("returnValue") != "success":
                print(f"Round {current_round} not available yet.")
                break
                
            # API date format is YYYY-MM-DD, CSV uses YYYY.MM.DD
            date_str = data["drwNoDate"].replace("-", ".")
            
            row = {
                "round": data["drwNo"],
                "n1": data["drwtNo1"],
                "n2": data["drwtNo2"],
                "n3": data["drwtNo3"],
                "n4": data["drwtNo4"],
                "n5": data["drwtNo5"],
                "n6": data["drwtNo6"],
                "bonus": data["bnusNo"],
                "dates": date_str
            }
            new_rows.append(row)
            print(f"Found new round: {current_round}")
            current_round += 1
        except Exception as e:
            print(f"Error: {e}")
            break
        
    if new_rows:
        # 기존 데이터 읽기
        existing_rows = []
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)
        
        # 새 데이터를 위로 (내림차순 정렬 유지)
        # new_rows는 1199, 1200 순서로 들어있으므로 역순으로 뒤집어서 1200, 1199가 되게 함
        new_rows.sort(key=lambda x: x["round"], reverse=True)
        
        all_rows = new_rows + existing_rows
        
        # CSV 저장
        with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
            fieldnames = ["round", "n1", "n2", "n3", "n4", "n5", "n6", "bonus", "dates"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)
            
        print(f"Successfully updated {len(new_rows)} rounds.")
    else:
        print("No new data to update.")

if __name__ == "__main__":
    update_lotto()
