import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
import io
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="나스닥 100 실시간 분석", page_icon="📈", layout="wide")

SECTOR_MAP = {
    "Technology": "💻 기술", "Consumer Cyclical": "🛍️ 임의소비재",
    "Communication Services": "📱 커뮤니케이션", "Healthcare": "🏥 헬스케어",
    "Financial Services": "🏦 금융", "Industrials": "🏭 산업재",
    "Consumer Defensive": "🛒 필수소비재", "Utilities": "⚡ 유틸리티",
    "Real Estate": "🏢 부동산", "Energy": "🛢️ 에너지", "Basic Materials": "🧱 소재"
}

# 2. 티커 리스트 가져오기 (실패 대비 비상용 리스트 포함)
@st.cache_data(ttl=86400)
def get_ndx_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        tables = pd.read_html(io.StringIO(response.text))
        df = next((table for table in tables if 'Ticker' in table.columns or 'Symbol' in table.columns), None)
        if df is not None:
            col = 'Ticker' if 'Ticker' in df.columns else 'Symbol'
            return sorted(df[col].str.replace('.', '-', regex=False).tolist())
    except:
        return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "COST", "PEP"]

# 3. 데이터 분석 함수
@st.cache_data(ttl=3600)
def fetch_analysis(years):
    tickers = get_ndx_tickers()
    # 주가 데이터 일괄 다운로드
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    
    if data.empty:
        return pd.DataFrame()

    results = []
    # 시총/섹터 조회를 위한 객체
    tickers_obj = yf.Tickers(' '.join(tickers))
    
    for t in tickers:
        try:
            close_s = data['Close'][t].dropna()
            if len(close_s) < 5: continue
            
            cur = close_s.iloc[-1]
            mdd = ((cur - data['High'][t].max()) / data['High'][t].max()) * 100
            rec = ((cur - data['Low'][t].min()) / data['Low'][t].min()) * 100
            score = round(abs(mdd) - rec, 1)
            
            info = tickers_obj.tickers[t].info
            sector = SECTOR_MAP.get(info.get('sector', '기타'), info.get('sector', '기타'))
            mkt_cap = (info.get('marketCap') or 0) / 1e9

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, "섹터": sector, "현재가": cur, "MDD": mdd, 
                "회복률": rec, "점수": score, "시총($B)": mkt_cap
            })
        except: continue
    return pd.DataFrame(results)

# 4. UI 출력
st.title("📈 나스닥 100 실시간 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"Last Update (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tabs = st.tabs(["1년 분석", "2년 분석", "3년 분석"])
for i, tab in enumerate(tabs):
    with tab:
        df = fetch_analysis(i+1)
        if not df.empty:
            st.dataframe(df.sort_values("점수", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.warning("데이터를 불러오는 중입니다. 잠시만 기다려주세요 (약 10~20초 소요)")
