import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
import io
import time
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="나스닥 100 실시간 MDD 분석", page_icon="📈", layout="wide")

# 2. 티커 리스트 가져오기 (24시간 캐싱)
@st.cache_data(ttl=86400)
def get_ndx_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        html_data = io.StringIO(response.text)
        tables = pd.read_html(html_data)
        df = next((table for table in tables if 'Ticker' in table.columns or 'Symbol' in table.columns), None)
        if df is not None:
            col_name = 'Ticker' if 'Ticker' in df.columns else 'Symbol'
            return sorted(df[col_name].str.replace('.', '-', regex=False).tolist())
    except:
        return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "PEP", "COST"]

# 3. 시가총액 수집 (0원 방지 보정 로직)
@st.cache_data(ttl=86400) # 시총은 하루에 한 번만 성공하면 재사용
def get_robust_market_caps(tickers):
    caps = {}
    # 일괄 객체 생성
    tickers_obj = yf.Tickers(' '.join(tickers))
    
    # 1차 시도: fast_info (가장 빠름)
    for t in tickers:
        try:
            val = tickers_obj.tickers[t].fast_info.get('market_cap', 0)
            caps[t] = val if val else 0
        except:
            caps[t] = 0
            
    # 2차 시도: 0으로 나온 종목들만 개별 정밀 재요청
    zero_tickers = [t for t, v in caps.items() if v == 0]
    if zero_tickers:
        for t in zero_tickers:
            try:
                # 개별 호출은 서버가 더 잘 대답해줍니다.
                time.sleep(0.1) # 0.1초씩 쉬면서 요청
                info = yf.Ticker(t).info
                val = info.get('marketCap') or info.get('enterpriseValue', 0)
                if val: caps[t] = val
            except:
                continue
                
    return {t: round(val / 1e9, 1) for t, val in caps.items()}

# 4. 분석 함수
@st.cache_data(ttl=3600)
def fetch_analysis(years):
    tickers = get_ndx_tickers()
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    if data.empty: return pd.DataFrame()

    # 시총 데이터 로드 (보정 함수 호출)
    mkt_caps = get_robust_market_caps(tickers)
    
    results = []
    for t in tickers:
        try:
            close_series = data['Close'][t].dropna()
            if len(close_series) < 5: continue
            
            high_val = data['High'][t].max()
            low_val = data['Low'][t].min()
            current_val = close_series.iloc[-1]
            
            mdd = ((current_val - high_val) / high_val) * 100
            rec = ((current_val - low_val) / low_val) * 100
            score = round(abs(mdd) - rec, 1)

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, "현재가": current_val, "MDD": mdd, 
                "회복률": rec, "점수": score,
                "시총($B)": mkt_caps.get(t, 0)
            })
        except: continue
    return pd.DataFrame(results)

# 5. UI 구성
st.title("📈 나스닥 100 실시간 MDD 분석 (시총 보정 완료)")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tabs = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

for i, tab in enumerate(tabs):
    years = i + 1
    with tab:
        df = fetch_analysis(years)
        if not df.empty:
            st.dataframe(
                df.sort_values("점수", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={
                    "현재가": st.column_config.NumberColumn(format="$%.2f"),
                    "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                    "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                    "점수": st.column_config.NumberColumn(format="%.1f"),
                    "시총($B)": st.column_config.NumberColumn(format="$%.1f B")
                }
            )
