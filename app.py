from flask import Flask, render_template, request, jsonify
import urllib.request
import json
import os

app = Flask(__name__)

# 네이버 API 설정 (제공해주신 정보 사용)
CLIENT_ID = "xjFBtmULT86TZ40K0ltj"
CLIENT_SECRET = "sKqpaVlmzS"

def fetch_naver_trend(keywords, start_date, end_date, device=None):
    url = "https://openapi.naver.com/v1/datalab/search"
    
    # 키워드 그룹 생성 (각 키워드를 하나의 그룹으로 처리)
    keyword_groups = [{"groupName": k, "keywords": [k]} for k in keywords]
    
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": "date",
        "keywordGroups": keyword_groups
    }
    
    if device:
        body["device"] = device

    body_json = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", CLIENT_ID)
    request.add_header("X-Naver-Client-Secret", CLIENT_SECRET)
    request.add_header("Content-Type", "application/json")

    try:
        response = urllib.request.urlopen(request, data=body_json)
        if response.getcode() == 200:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

def fetch_total_results(keyword):
    """검색 결과 총 개수(블로그)를 가져옴"""
    try:
        # 네이버 검색 API 정석 URL
        encText = urllib.parse.quote(keyword)
        url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display=1"
        
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", CLIENT_ID)
        request.add_header("X-Naver-Client-Secret", CLIENT_SECRET)
        
        response = urllib.request.urlopen(request)
        rescode = response.getcode()
        
        if rescode == 200:
            response_body = response.read()
            data = json.loads(response_body.decode('utf-8'))
            total = data.get('total', 0)
            print(f"Keyword: {keyword}, Total Results: {total}") # 서버 로그 확인용
            return total
        else:
            print(f"Error: API returned code {rescode}")
            return 0
    except Exception as e:
        print(f"Search API Error: {e}")
        return 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/trend', methods=['POST'])
def get_trend():
    data = request.json
    keywords = data.get('keywords', [])
    start_date = data.get('startDate')
    end_date = data.get('endDate')

    # 전체, PC, 모바일 데이터 각각 호출
    total_data = fetch_naver_trend(keywords, start_date, end_date)
    pc_data = fetch_naver_trend(keywords, start_date, end_date, device="pc")
    mo_data = fetch_naver_trend(keywords, start_date, end_date, device="mo")

    # 키워드별 게시글 총 개수(데이터 규모) 추가
    volume_stats = {}
    for kw in keywords:
        volume_stats[kw] = fetch_total_results(kw)

    return jsonify({
        "total": total_data,
        "pc": pc_data,
        "mo": mo_data,
        "volumes": volume_stats
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)
