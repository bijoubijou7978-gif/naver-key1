import streamlit as st
import urllib.request
import json
import pandas as pd
import datetime

# 페이지 설정
st.set_page_config(page_title="Naver Trend Dashboard", layout="wide")

# 네이버 API 설정
CLIENT_ID = "xjFBtmULT86TZ40K0ltj"
CLIENT_SECRET = "sKqpaVlmzS"

def fetch_naver_trend(keywords, start_date, end_date, device=None):
    url = "https://openapi.naver.com/v1/datalab/search"
    keyword_groups = [{"groupName": k, "keywords": [k]} for k in keywords]
    body = {
        "startDate": start_date.strftime('%Y-%m-%d'),
        "endDate": end_date.strftime('%Y-%m-%d'),
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
        return json.loads(response.read().decode('utf-8'))
    except:
        return None

def fetch_total_results(keyword):
    encText = urllib.parse.quote(keyword)
    url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display=1"
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", CLIENT_ID)
    request.add_header("X-Naver-Client-Secret", CLIENT_SECRET)
    try:
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode('utf-8'))
        return data.get('total', 0)
    except:
        return 0

# UI 구성
st.title("🚀 Naver Trend Dashboard")
st.markdown("키워드별 PC/모바일 검색 트렌드 분석 도구")

with st.sidebar:
    st.header("🔍 검색 설정")
    keyword_input = st.text_input("키워드 (쉼표로 구분)", "주식, 캠핑")
    keywords = [k.strip() for k in keyword_input.split(",") if k.strip()]
    
    col1, col2 = st.columns(2)
    start_date = col1.date_input("시작일", datetime.date.today() - datetime.timedelta(days=365))
    end_date = col2.date_input("종료일", datetime.date.today())
    
    analyze_btn = st.button("분석하기", use_container_width=True)

if analyze_btn and keywords:
    # 데이터 가져오기
    with st.spinner('데이터를 분석 중입니다...'):
        # 볼륨 카드 표시
        st.subheader("📊 콘텐츠 규모 (전체 게시글 수)")
        cols = st.columns(len(keywords))
        for i, kw in enumerate(keywords):
            total = fetch_total_results(kw)
            cols[i].metric(label=kw, value=f"{total:,}")

        # 차트 데이터 가져오기
        res_total = fetch_naver_trend(keywords, start_date, end_date)
        
        if res_total:
            st.subheader("📈 검색 트렌드 추이")
            
            # 데이터프레임 변환
            all_data = []
            for result in res_total['results']:
                title = result['title']
                for d in result['data']:
                    all_data.append({
                        'Date': d['period'],
                        'Keyword': title,
                        'Ratio': d['ratio']
                    })
            
            df = pd.DataFrame(all_data)
            df['Date'] = pd.to_datetime(df['Date'])
            
            # 멀티셀렉트로 키워드 필터링
            selected_keywords = st.multiselect("확인할 키워드 선택", keywords, default=keywords)
            filtered_df = df[df['Keyword'].isin(selected_keywords)]
            
            # 차트 그리기
            st.line_chart(filtered_df.pivot(index='Date', columns='Keyword', values='Ratio'))
        else:
            st.error("데이터를 가져오는 데 실패했습니다. API 설정을 확인해 주세요.")
else:
    st.info("왼쪽 사이드바에서 키워드를 입력하고 '분석하기' 버튼을 눌러주세요.")
