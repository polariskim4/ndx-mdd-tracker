import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
import io
import time
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="나스닥 100 MDD 분석 (시총 보정)", layout="wide")

# 2. 티커 리스트 가져오기 (전처리 강화)
@st.cache_data(ttl=86400)
def get_ndx_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        html_data = io.StringIO(response.text)
        tables = pd.read_html(html_data)
        df = next((table for table in tables if any(c in table.columns for c in ['Ticker', 'Symbol'])), None)
        if df is not None:
            col = 'Ticker' if 'Ticker' in df.columns else 'Symbol'
            # 공백 제거 및 점(.)을 대시(-)로 통일
            return sorted(df[col].astype(str).str.strip().str.replace('.', '-', regex=False).unique().tolist())
    except:
        return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "PEP", "COST"]

# 3. 데이터 분석 및 시총 보정 (핵심 로직)
@st.cache_data(ttl=3600)
def fetch_analysis(years):
    tickers = get_ndx_tickers()
    # 주가 데이터는 한 번에 다운로드
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    if data.empty: return pd.DataFrame()

    results = []
    
    # 루프 내부에서 시총을 정밀하게 가져옵니다.
    for t in tickers:
        try:
            close_series = data['Close'][t].dropna()
            if len(close_series) < 10: continue
            
            cur_price = close_series.iloc[-1]
            mdd = ((cur_price - data['High'][t].max()) / data['High'][t].max()) * 100
            rec = ((cur_price - data['Low'][t].min()) / data['Low'][t].min()) * 100
            score = round(abs(mdd) - rec, 1)

            # --- 시가총액 0원 방어 로직 ---
            mkt_cap = 0
            t_obj = yf.Ticker(t)
            
            # 경로 1: fast_info (빠름)
            try: mkt_cap = t_obj.fast_info.get('market_cap', 0)
            except: pass
            
            # 경로 2: info (기본값)
            if not mkt_cap or mkt_cap == 0:
                try: mkt_cap = t_obj.info.get('marketCap', 0)
                except: pass
            
            # 경로 3: 강제 계산 (발행주식수 * 현재가)
            if not mkt_cap or mkt_cap == 0:
                try:
                    shares = t_obj.info.get('sharesOutstanding') or t_obj.info.get('floatShares')
                    if shares: mkt_cap = shares * cur_price
                except: pass
            
            mkt_cap_bn = round(mkt_cap / 1e9, 1) if mkt_cap else 0
            # ---------------------------

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, "현재가": cur_price, "MDD": mdd, 
                "회복률": rec, "점수": score, "시총($B)": mkt_cap_bn
            })
        except: continue
    return pd.DataFrame(results)

# 4. 메인 UI
st.title("📈 나스닥 100 실시간 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tabs = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

def render_tab(years, target_tab):
    with target_tab:
        with st.spinner(f"나스닥 100 {years}년치 분석 및 시총 보정 중..."):
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

render_tab(1, tabs[0])
render_tab(2, tabs[1])
render_tab(3, tabs[2])
