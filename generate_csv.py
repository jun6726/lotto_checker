from flask import Flask, render_template, request
import csv

app = Flask(__name__)

def load_lotto():
    with open("lotto.csv", "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    nums = []

    if request.method == "POST":
        user_input = request.form["numbers"]
        nums = list(map(int, user_input.replace(",", " ").split()))
        nums = set(nums)

        rows = load_lotto()
        for row in rows:
            draw = {
                int(row["n1"]), int(row["n2"]), int(row["n3"]),
                int(row["n4"]), int(row["n5"]), int(row["n6"]),
                int(row["bonus"])
            }

            matched = nums & draw
            if matched:
                results.append({
                    "round": row["round"],
                    "date": row["date"],
                    "matched": sorted(list(matched)),
                    "count": len(matched)
                })

    return render_template("index.html", nums=sorted(nums), results=results)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
