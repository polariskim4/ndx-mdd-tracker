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

# 2. 티커 리스트 가져오기 (User-Agent 강화)
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
            # 티커 전처리 (점 -> 대시)
            return sorted(df[col_name].str.replace('.', '-', regex=False).unique().tolist())
    except:
        pass
    return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "PEP", "COST"]

# 3. 데이터 분석 및 시총 보정 (S&P 100 성공 로직 적용)
@st.cache_data(ttl=3600)
def fetch_analysis(years):
    tickers = get_ndx_tickers()
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    if data.empty: return pd.DataFrame()

    # 시총 조회를 위한 전체 Tickers 객체 생성
    tickers_obj = yf.Tickers(' '.join(tickers))
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

            # --- 시가총액 3중 방어 (S&P 100 성공 버전) ---
            mkt_cap = 0
            try:
                t_info = tickers_obj.tickers[t].info
                # 1. marketCap 우선, 없으면 totalAssets 시도
                mkt_cap = t_info.get('marketCap') or t_info.get('totalAssets') or 0
                
                # 2. 여전히 0이면 fast_info 시도
                if not mkt_cap:
                    mkt_cap = tickers_obj.tickers[t].fast_info.get('market_cap', 0)
            except:
                mkt_cap = 0
            
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

# 4. 메인 UI
st.title("📈 나스닥 100 실시간 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tab1, tab2, tab3 = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

def render_tab(years, target_tab):
    with target_tab:
        with st.spinner(f"나스닥 100 {years}년치 정밀 분석 중..."):
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

render_tab(1, tab1)
render_tab(2, tab2)
render_tab(3, tab3)
