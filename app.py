from flask import Flask, render_template, request, redirect, url_for, make_response
import csv
from collections import Counter
import update_lotto

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
    latest_round_info = None
    error_message = None
    user_input = ""
    
    # 항상 추천 번호 계산 (GET, POST 모두)
    rows = load_lotto()
    
    # 최근 당첨 내역 조회
    try:
        history_count = int(request.values.get("history_count", 5))
    except ValueError:
        history_count = 5
        
    recent_history = rows[:history_count] if rows else []
    
    if rows:
        latest_round_info = {
            "round": rows[0]["round"],
            "date": rows[0].get("dates", "-")
        }

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
            # 라인별 유효성 검사
            lines = user_input.strip().split('\n')
            for i, line in enumerate(lines):
                line_nums = line.replace(",", " ").split()
                if not line_nums:
                    continue
                if len(line_nums) < 6:
                    error_message = f"{i + 1}번째 줄에 숫자가 부족합니다. (최소 6개 필요)"
                    break
            
            if not error_message:
                # Display formatting and search set preparation
                lines = user_input.strip().split('\n')
                for i, line in enumerate(lines):
                    line_vals = [int(x) for x in line.replace(",", " ").split()]
                    if not line_vals:
                        continue
                    
                    current_nums = sorted(line_vals)
                    nums.append(", ".join(map(str, current_nums)))
                    current_set = set(line_vals)
                    
                    line_matches = []
                    
                    for row in rows:
                        # 당첨 번호 6개
                        draw = {
                            int(row["n1"]), int(row["n2"]), int(row["n3"]),
                            int(row["n4"]), int(row["n5"]), int(row["n6"])
                        }
                        bonus = int(row["bonus"])

                        # 일치하는 번호 확인
                        matched = current_set & draw
                        matched_count = len(matched)
                        
                        # 5개 일치했을 때만 보너스 확인
                        bonus_matched = (matched_count == 5) and (bonus in current_set)
                        
                        # 3개 이상 일치하면 결과에 추가
                        if matched_count >= 3:
                            rank = get_rank(matched_count, bonus_matched)
                            
                            matched_str = ", ".join(map(str, sorted(list(matched))))
                            if bonus_matched:
                                matched_str += f" ({bonus})"
                            
                            line_matches.append({
                                "round": row["round"],
                                "matched": matched_str,
                                "count": matched_count,
                                "rank": rank
                            })
                    
                    # 결과가 있으면 추가
                    if line_matches:
                        # 등수 오름차순 (1등 -> 5등), 그 다음 회차 내림차순 (최신 -> 과거)
                        line_matches.sort(key=lambda x: (int(x['rank'][0]), -int(x['round'])))
                        results.append({
                            "line_index": i + 1,
                            "numbers": ", ".join(map(str, current_nums)),
                            "matches": line_matches
                        })

    response = make_response(render_template("index.html",
                         nums=nums,
                         results=results,
                         recommended=recommended_numbers,
                         recent=recent_numbers,
                         recent_count=recent_count,
                         latest_round=latest_round_info,
                         error_message=error_message,
                         user_input=user_input,
                         recent_history=recent_history,
                         history_count=history_count))
    
    # 브라우저 캐시 방지
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response


@app.route("/update", methods=["POST"])
def update_data():
    update_lotto.update_lotto()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True, port=5001)
