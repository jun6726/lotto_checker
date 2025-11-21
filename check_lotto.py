import sys
import csv

if len(sys.argv) != 7:
    print("사용법: python3 check_lotto.py 1 2 3 4 5 6")
    sys.exit(1)

user_numbers = set(map(int, sys.argv[1:]))

csv_file = "lotto_numbers.csv"

found_matches = []

with open(csv_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)

    for row in reader:
        # 회차의 6개 + 보너스 1개 = 총 7개 번호
        draw_numbers = {
            int(row['n1']), int(row['n2']), int(row['n3']),
            int(row['n4']), int(row['n5']), int(row['n6']),
            int(row['bonus'])  # 보너스 번호도 포함
        }

        # 사용자의 6개 번호와 회차 7개 번호의 교집합 확인
        matched = user_numbers & draw_numbers

        if matched:  # 교집합 1개라도 있으면 True
            found_matches.append((row['round'], matched))

# 결과 출력
if found_matches:
    print("\n===== 일치한 회차 =====\n")
    for round_no, nums in found_matches:
        print(f"- {round_no}회차: 일치번호 {sorted(nums)}")
else:
    print("일치하는 번호가 있는 회차가 없습니다.")
