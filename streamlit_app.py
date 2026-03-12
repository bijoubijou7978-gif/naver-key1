import streamlit as st
import urllib.request
import json
import pandas as pd
import datetime
import time
import hmac
import hashlib
import base64

# 페이지 설정
st.set_page_config(page_title="Naver Pro Keyword Master", layout="wide", initial_sidebar_state="expanded")

# 프리미엄 디자인을 위한 커스텀 CSS 주입 (밝은/어두운 테마 모두 대응)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
    }
    
    /* 헤더 스타일 */
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 2rem;
        color: #03c75a; /* 네이버 그린 */
    }
    
    /* 카드 스타일 */
    [data-testid="stMetricValue"] {
        color: #03c75a !important;
    }
    
    /* 버튼 스타일 가시성 확보 */
    .stButton > button {
        background-color: #03c75a !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
    }
    
    .stButton > button:hover {
        background-color: #02b350 !important;
        box-shadow: 0 4px 12px rgba(3, 199, 90, 0.2) !important;
    }

    /* 테이블 가독성 강화 */
    div[data-testid="stTable"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

# (기존) 네이버 오픈 API 설정
CLIENT_ID = "xjFBtmULT86TZ40K0ltj"
CLIENT_SECRET = "sKqpaVlmzS"

# (신규) 네이버 검색광고 API 설정
AD_CUSTOMER_ID = "4185827"
AD_ACCESS_KEY = "0100000000feae58d8e1a8357d1bfce4f4d68d6f1566c3112dba3bcc88f0f676e77c5b98ea"
AD_SECRET_KEY = "AQAAAAD+rljY4ag1fRv85PTWjW8V5Cr6JejY7N1E0Ph6K4eiiQ=="

def generate_signature(timestamp, method, uri, secret_key):
    message = f"{timestamp}.{method}.{uri}"
    hash = hmac.new(bytes(secret_key, "utf-8"), bytes(message, "utf-8"), hashlib.sha256)
    return base64.b64encode(hash.digest()).decode("utf-8")

def fetch_actual_search_volume(keywords):
    """네이버 검색광고 API를 사용하여 실제 PC/모바일 월간 조회수를 가져옴"""
    if not keywords:
        return []
        
    timestamp = str(int(time.time() * 1000))
    method = "GET"
    uri = "/keywordstool"
    
    # 파라미터 구성 (공백을 %20으로, 콤마는 유지하여 인코딩)
    # 네이버 API는 공백이 +로 인코딩되면 400 에러를 낼 수 있음
    kw_str = ",".join(keywords[:5])
    kw_encoded = urllib.parse.quote(kw_str, safe=",")
    full_url = f"https://api.searchad.naver.com{uri}?hintKeywords={kw_encoded}&showDetail=1"
    
    signature = generate_signature(timestamp, method, uri, AD_SECRET_KEY)
    
    request = urllib.request.Request(full_url)
    request.add_header("X-Timestamp", timestamp)
    request.add_header("X-API-KEY", AD_ACCESS_KEY)
    request.add_header("X-Customer", AD_CUSTOMER_ID)
    request.add_header("X-Signature", signature)
    
    try:
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode('utf-8'))
        return data.get('keywordList', [])
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_body)
            # 네이버 API는 보통 {"code": "...", "message": "..."} 형태의 에러를 반환함
            detail = error_json.get('message', error_body)
        except:
            detail = error_body
            
        st.error(f"검색광고 API 오류 ({e.code}): {detail}")
        return []
    except Exception as e:
        st.error(f"검색광고 API 오류: {e}")
        return []

def fetch_naver_trend(keywords, start_date, end_date):
    url = "https://openapi.naver.com/v1/datalab/search"
    keyword_groups = [{"groupName": k, "keywords": [k]} for k in keywords]
    body = {
        "startDate": start_date.strftime('%Y-%m-%d'),
        "endDate": end_date.strftime('%Y-%m-%d'),
        "timeUnit": "date",
        "keywordGroups": keyword_groups
    }
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

def fetch_related_keywords(keyword):
    encText = urllib.parse.quote(keyword)
    url = f"https://ac.search.naver.com/nx/ac?q={encText}&r_format=json&t_koreng=1&q_enc=UTF-8&st=100&r_lt=100"
    try:
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode('utf-8'))
        items = data['items'][0]
        return [item[0] for item in items]
    except:
        return []

# 메인 UI
st.title("💎 Naver Pro Keyword Master")
st.markdown("정식 검색광고 API 연동으로 정확한 월간 조회수를 제공합니다.")

if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False
    st.session_state.table_data = []
    st.session_state.related_volumes = {}
    st.session_state.cached_related = []
    st.session_state.current_main_kw = ""

with st.sidebar:
    st.header("⚙️ 분석 설정")
    keyword_input = st.text_input("분석 키워드 (최대 5개 권장)", "주식, 캠핑")
    keywords_list = [k.strip() for k in keyword_input.split(",") if k.strip()]
    
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Trend 시작일", datetime.date.today() - datetime.timedelta(days=30))
    end_date = col2.date_input("Trend 종료일", datetime.date.today())
    
    if st.button("실시간 조회수 분석 실행", use_container_width=True):
        st.session_state.analyzed = True
        st.session_state.current_keywords = keywords_list
        st.session_state.related_volumes = {}
        
        with st.spinner('네이버 광고자 데이터를 긁어오는 중...'):
            if len(keywords_list) > 5:
                st.warning("네이버 광고 API는 한 번에 최대 5개 키워드만 조회 가능합니다. 상위 5개만 분석합니다.")
                keywords_list = keywords_list[:5]
                
            # 실제 조회수 데이터 (Search Ad API)
            ad_data_list = fetch_actual_search_volume(keywords_list)
            ad_lookup = {item['relKeyword']: item for item in ad_data_list}
            
            table_data = []
            for i, kw in enumerate(keywords_list):
                # 블로그 수
                blog_count = fetch_total_results(kw, start_date, end_date)
                
                # 광고 API에서 가져온 실제 숫자 (없으면 0)
                target_ad = ad_lookup.get(kw, {})
                pc_vol = str(target_ad.get('monthlyPcQcCnt', '0')).replace('< ', '')
                mo_vol = str(target_ad.get('monthlyMobileQcCnt', '0')).replace('< ', '')
                
                # 숫자로 변환
                pc_num = int(pc_vol) if pc_vol.isdigit() else 10 # 미미한 수치는 10으로 처리
                mo_num = int(mo_vol) if mo_vol.isdigit() else 10
                
                # 경쟁 지수 계산 (블로그 수 / 총 조회수)
                total_vol = pc_num + mo_num
                comp_ratio = blog_count / total_vol if total_vol > 0 else 0
                
                # 등급 평가
                if comp_ratio < 0.1: rating = "⭐ 매우 낮음 (꿀)"
                elif comp_ratio < 0.5: rating = "✅ 낮음"
                elif comp_ratio < 2.0: rating = "⚠️ 보통"
                else: rating = "🔥 높음 (치열)"
                
                table_data.append({
                    "NO": i + 1,
                    "키워드": kw,
                    "월간 PC": pc_num,
                    "월간 Mobile": mo_num,
                    "총 합계": total_vol,
                    "블로그수": blog_count,
                    "경쟁 지수": round(comp_ratio, 2),
                    "등급": rating
                })
            st.session_state.table_data = table_data
            st.session_state.all_trend = fetch_naver_trend(keywords_list, start_date, end_date)
            # 메인 키워드 기준으로 연관 검색어 세션 저장
            st.session_state.current_main_kw = keywords_list[0]
            st.session_state.cached_related = fetch_related_keywords(keywords_list[0])
            st.rerun() # 세션 반영을 위해 리런

if st.session_state.analyzed:
    st.markdown("### 📋 정밀 키워드 분석 리포트")
    
    df = pd.DataFrame(st.session_state.table_data)
    
    # 데이터프레임 시각화 설정
    st.dataframe(
        df,
        column_config={
            "월간 PC": st.column_config.NumberColumn(format="%d"),
            "월간 Mobile": st.column_config.NumberColumn(format="%d"),
            "총 합계": st.column_config.NumberColumn(format="%d"),
            "블로그수": st.column_config.NumberColumn(format="%d"),
            "경쟁 지수": st.column_config.NumberColumn(format="%.2f"),
            "등급": st.column_config.TextColumn("상태"),
        },
        hide_index=True,
        use_container_width=True
    )
    
    # 엑셀/CSV 다운로드 버튼
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📄 분석 리포트 다운로드 (CSV)",
        data=csv,
        file_name=f"naver_keyword_report_{datetime.date.today()}.csv",
        mime="text/csv",
    )
    
    st.caption("※ 조회수 데이터는 최근 30일간의 네이버 검색광고 공식 집계 데이터입니다.")

    # 연관 검색어 섹션
    main_kw = st.session_state.current_main_kw
    st.divider()
    st.subheader(f"🔍 '{main_kw}' 연관/추천 키워드 조회")
    
    related = st.session_state.cached_related
    
    if related:
        related_filtered = [r for r in related if r != main_kw]
        cols = st.columns(min(len(related_filtered), 4))
        
        for idx, r_kw in enumerate(related_filtered[:8]):
            with cols[idx % 4]:
                if st.button(r_kw, key=f"btn_{r_kw}", use_container_width=True):
                    # 연관검색어도 광고 API로 조회수 가져오기
                    with st.spinner('조회 중...'):
                        ad_res = fetch_actual_search_volume([r_kw])
                        if ad_res:
                            # 여러 결과 중 클릭한 키워드와 정확히 일치하는 것 찾기
                            match = next((item for item in ad_res if item['relKeyword'].replace(" ", "") == r_kw.replace(" ", "")), ad_res[0])
                            
                            p_raw = str(match.get('monthlyPcQcCnt', '0')).replace('<', '').strip()
                            m_raw = str(match.get('monthlyMobileQcCnt', '0')).replace('<', '').strip()
                            
                            # 비어있거나 숫자가 아니면 10으로 처리
                            p = int(p_raw) if p_raw.isdigit() else 10
                            m = int(m_raw) if m_raw.isdigit() else 10
                            
                            st.session_state.related_volumes[r_kw] = p + m
                
                if r_kw in st.session_state.related_volumes:
                    vol = st.session_state.related_volumes[r_kw]
                    st.markdown(f"<div style='text-align:center; color:#FF4B4B; font-weight:bold;'>📈 {vol:,}회</div>", unsafe_allow_html=True)
                    # 분석 추가 버튼
                    if st.button("➕ 분석 추가", key=f"add_{r_kw}", use_container_width=True):
                        new_input = keyword_input + f", {r_kw}"
                        st.info(f"'{r_kw}'가 추가되었습니다. 상단 버튼을 다시 눌러주세요.")
    
    if st.session_state.all_trend:
        st.divider()
        st.subheader("📈 최근 트렌드 변화 지수 (Naver DataLab)")
        chart_data = []
        for res in st.session_state.all_trend['results']:
            for d in res['data']:
                chart_data.append({'날짜': d['period'], '키워드': res['title'], '관심도': d['ratio']})
        chart_df = pd.DataFrame(chart_data)
        
        # 차트 가독성 개선
        pivot_df = chart_df.pivot(index='날짜', columns='키워드', values='관심도')
        st.line_chart(pivot_df, height=400)
        st.caption("※ 데이터랩 데이터는 선택한 기간 중 최대 검색량을 100으로 둔 상대적 수치입니다.")
else:
    st.info("왼쪽 대시보드에서 키워드를 입력하고 '실시간 조회수 분석'을 시작하세요.")
