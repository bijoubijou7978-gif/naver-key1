import streamlit as st
import urllib.request
import json
import pandas as pd
import datetime

# 페이지 설정
st.set_page_config(page_title="Naver Keyword Pro", layout="wide")

# 네이버 API 설정 (ID/Secret)
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

def fetch_total_results(keyword, start_date, end_date):
    encText = urllib.parse.quote(keyword)
    s_date = start_date.strftime('%Y%m%d')
    e_date = end_date.strftime('%Y%m%d')
    url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display=1&startDate={s_date}&endDate={e_date}"
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", CLIENT_ID)
    request.add_header("X-Naver-Client-Secret", CLIENT_SECRET)
    try:
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode('utf-8'))
        return data.get('total', 0)
    except:
        return 0

# 메인 UI
st.title("📊 Naver Keyword Pro")
st.markdown("이미지 형식의 테이블 리포트를 생성합니다.")

with st.sidebar:
    st.header("⚙️ 설정")
    keyword_input = st.text_input("분석 키워드 (쉼표 구분)", "주식, 캠핑")
    keywords = [k.strip() for k in keyword_input.split(",") if k.strip()]
    
    col1, col2 = st.columns(2)
    start_date = col1.date_input("시작일", datetime.date.today() - datetime.timedelta(days=30))
    end_date = col2.date_input("종료일", datetime.date.today())
    
    analyze_btn = st.button("데이터 분석 실행", use_container_width=True)

if analyze_btn and keywords:
    with st.spinner('실시간 데이터를 집계 중입니다...'):
        # 각 디바이스별 데이터 호출
        res_pc = fetch_naver_trend(keywords, start_date, end_date, device='pc')
        res_mo = fetch_naver_trend(keywords, start_date, end_date, device='mo')
        
        table_data = []
        for i, kw in enumerate(keywords):
            # 블로그 콘텐츠 수
            blog_count = fetch_total_results(kw, start_date, end_date)
            
            # PC/모바일 지수 (기간 내 평균값 추출)
            pc_val = 0
            mo_val = 0
            
            if res_pc:
                for r in res_pc['results']:
                    if r['title'] == kw and r['data']:
                        pc_val = sum([d['ratio'] for d in r['data']]) / len(r['data'])
            
            if res_mo:
                for r in res_mo['results']:
                    if r['title'] == kw and r['data']:
                        mo_val = sum([d['ratio'] for d in r['data']]) / len(r['data'])
            
            table_data.append({
                "NO": i + 1,
                "키워드": kw,
                "PC 지수": round(pc_val, 2),
                "모바일 지수": round(mo_val, 2),
                "지수 합계": round(pc_val + mo_val, 2),
                "블로그 게시글수": blog_count
            })
        
        # 테이블 출력
        st.subheader("📋 검색 분석 결과 보고서")
        df = pd.DataFrame(table_data)
        
        # 스타일링된 테이블 출력
        st.table(df.set_index('NO'))
        
        st.caption("※ 지수는 기간 내 최대 검색량을 100으로 둔 상대적 수치입니다.")

        # 트렌드 차트 추가 (시각화 보조)
        st.divider()
        st.subheader("📈 시계열 트렌드 변화")
        all_trend = fetch_naver_trend(keywords, start_date, end_date)
        if all_trend:
            chart_data = []
            for res in all_trend['results']:
                for d in res['data']:
                    chart_data.append({'Date': d['period'], 'Keyword': res['title'], 'Value': d['ratio']})
            
            chart_df = pd.DataFrame(chart_data)
            st.line_chart(chart_df.pivot(index='Date', columns='Keyword', values='Value'))

else:
    st.info("왼쪽 대시보드에서 키워드를 입력하고 분석을 시작하세요.")
