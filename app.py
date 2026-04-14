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

# 2. 티커 리스트 가져오기 (전처리 강화)
@st.cache_data(ttl=86400)
def get_ndx_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        html_data = io.StringIO(response.text)
        tables = pd.read_html(html_data)
        # 나스닥 테이블은 보통 첫 번째 혹은 두 번째에 위치
        df = next((table for table in tables if any(c in table.columns for c in ['Ticker', 'Symbol'])), None)
        if df is not None:
            col = 'Ticker' if 'Ticker' in df.columns else 'Symbol'
            # 티커에서 점(.)을 대시(-)로 바꾸고 공백 제거
            return sorted(df[col].astype(str).str.replace('.', '-', regex=False).str.strip().unique().tolist())
    except:
        pass
    return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "PEP", "COST"]

# 3. 데이터 분석 및 시총 보정 로직
@st.cache_data(ttl=3600)
def fetch_analysis(years):
    tickers = get_ndx_tickers()
    # 1. 주가 데이터 일괄 다운로드
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    if data.empty: return pd.DataFrame()

    results = []
    
    for t in tickers:
        try:
            close_series = data['Close'][t].dropna()
            if len(close_series) < 10: continue
            
            high_val = data['High'][t].max()
            low_val = data['Low'][t].min()
            current_val = close_series.iloc[-1]
            
            mdd = ((current_val - high_val) / high_val) * 100
            rec = ((current_val - low_val) / low_val) * 100
            chg = ((current_val - close_series.iloc[0]) / close_series.iloc[0]) * 100
            score = round(abs(mdd) - rec, 1)

            # --- 시가총액 수집 4단계 경로 (보정 강화) ---
            mkt_cap = 0
            ticker_obj = yf.Ticker(t)
            
            # 경로 1: fast_info (가장 빠름)
            try: mkt_cap = ticker_obj.fast_info.get('market_cap', 0)
            except: pass
            
            # 경로 2: info (전통적 방식)
            if not mkt_cap:
                try: mkt_cap = ticker_obj.info.get('marketCap', 0)
                except: pass
                
            # 경로 3: 유동 시가총액 (floatShares * currentPrice)
            if not mkt_cap:
                try:
                    info = ticker_obj.info
                    mkt_cap = (info.get('floatShares', 0) or info.get('sharesOutstanding', 0)) * current_val
                except: pass
            
            # 경로 4: 기업 가치 (Enterprise Value) 대체
            if not mkt_cap:
                try: mkt_cap = ticker_obj.info.get('enterpriseValue', 0)
                except: pass

            mkt_cap_bn = round(mkt_cap / 1e9, 1) if mkt_cap else 0
            # ------------------------------------------

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, "현재가": current_val, "MDD": mdd, 
                "회복률": rec, "수익률": chg, "점수": score,
                "시총($B)": mkt_cap_bn
            })
        except: continue
    return pd.DataFrame(results)

# 4. UI 및 탭 렌더링
st.title("📈 나스닥 100 실시간 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tabs = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

def render_tab(years, target_tab):
    with target_tab:
        with st.spinner(f"나스닥 100 종목 분석 및 시총 보정 중..."):
            df = fetch_analysis(years)
            if not df.empty:
                st.dataframe(
                    df.sort_values("점수", ascending=False),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "현재가": st.column_config.NumberColumn(format="$%.2f"),
                        "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                        "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                        "수익률": st.column_config.NumberColumn(format="%.1f%%"),
                        "점수": st.column_config.NumberColumn(format="%.1f"),
                        "시총($B)": st.column_config.NumberColumn(format="$%.1f B")
                    }
                )

render_tab(1, tabs[0])
render_tab(2, tabs[1])
render_tab(3, tabs[2])
