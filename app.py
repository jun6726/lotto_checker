from flask import Flask, render_template, request
import csv
from collections import Counter

app = Flask(__name__)

def load_lotto():
    with open("lotto_numbers.csv", "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def get_most_frequent_numbers(rows, top_n=6, recent_count=None):
    """역대 당첨 번호 중 가장 많이 나온 번호 추출"""
    all_numbers = []
    
    # recent_count가 지정되면 최근 N회만 분석
    target_rows = rows[:recent_count] if recent_count else rows
    
    for row in target_rows:
        all_numbers.extend([
            int(row["n1"]), int(row["n2"]), int(row["n3"]),
            int(row["n4"]), int(row["n5"]), int(row["n6"])
        ])
    
    # 빈도수 계산
    counter = Counter(all_numbers)
    # 빈도가 높은 순으로 정렬
    most_common = counter.most_common(top_n)
    
    return most_common

def get_rank(matched_count, bonus_matched):
    """일치 개수와 보너스 일치 여부로 등수 판단"""
    if matched_count == 6:
        return "1등"
    elif matched_count == 5 and bonus_matched:
        return "2등"
    elif matched_count == 5:
        return "3등"
    elif matched_count == 4:
        return "4등"
    elif matched_count == 3:
        return "5등"
    else:
        return "-"

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    nums = []
    recommended_numbers = None
    recent_numbers = None
    recent_count = 20  # 기본값
    
    # 항상 추천 번호 계산 (GET, POST 모두)
    rows = load_lotto()
    recommended_numbers = get_most_frequent_numbers(rows, top_n=10)
    
    # GET 요청일 때도 기본 최근 회차 계산
    if request.method == "GET":
        recent_numbers = get_most_frequent_numbers(rows, top_n=10, recent_count=recent_count)

    if request.method == "POST":
        user_input = request.form.get("numbers", "")
        recent_count = int(request.form.get("recent_count", 20))
        
        # 최근 회차 빈도 계산
        recent_numbers = get_most_frequent_numbers(rows, top_n=10, recent_count=recent_count)
        
        # numbers 입력이 있을 때만 체크
        if user_input:
            nums = list(map(int, user_input.replace(",", " ").split()))
            nums = set(nums)
        
            for row in rows:
                # 당첨 번호 6개
                draw = {
                    int(row["n1"]), int(row["n2"]), int(row["n3"]),
                    int(row["n4"]), int(row["n5"]), int(row["n6"])
                }
                bonus = int(row["bonus"])

                # 일치하는 번호 확인
                matched = nums & draw
                matched_count = len(matched)
                
                # 5개 일치했을 때만 보너스 확인
                bonus_matched = (matched_count == 5) and (bonus in nums)
                
                # 3개 이상 일치하면 결과에 추가
                if matched_count >= 3:
                    rank = get_rank(matched_count, bonus_matched)
                    
                    results.append({
                        "round": row["round"],
                        "matched": ", ".join(map(str, sorted(list(matched)))),
                        "bonus": f"+ 보너스({bonus})" if bonus_matched else "",
                        "count": matched_count,
                        "rank": rank
                    })
            
            # 회차별 정렬 (최신 회차가 위로)
            results = sorted(results, key=lambda x: -int(x['round']))

    return render_template("index.html",
                         nums=", ".join(map(str, sorted(nums))) if nums else "",
                         results=results,
                         recommended=recommended_numbers,
                         recent=recent_numbers,
                         recent_count=recent_count)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
