import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
import io
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="나스닥 100 섹터별 MDD", page_icon="📈", layout="wide")

SECTOR_MAP = {
    "Technology": "💻 기술", "Consumer Cyclical": "🛍️ 임의소비",
    "Communication Services": "📱 통신", "Healthcare": "🏥 헬스케어",
    "Financial Services": "🏦 금융", "Industrials": "🏭 산업재",
    "Consumer Defensive": "🛒 필수소비", "Utilities": "⚡ 유틸리티",
    "Real Estate": "🏢 부동산", "Energy": "🛢️ 에너지", "Basic Materials": "🧱 소재"
}

@st.cache_data(ttl=86400)
def get_ndx_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        tables = pd.read_html(io.StringIO(resp.text))
        df = next((t for t in tables if 'Ticker' in t.columns or 'Symbol' in t.columns), None)
        if df is not None:
            col = 'Ticker' if 'Ticker' in df.columns else 'Symbol'
            return sorted(df[col].str.replace('.', '-', regex=False).tolist())
    except:
        return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "COST", "PEP"]

@st.cache_data(ttl=3600)
def fetch_data(years):
    tickers = get_ndx_tickers()
    # 1. 주가 데이터 한꺼번에 다운로드 (속도 향상)
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    if data.empty: return pd.DataFrame()

    # 2. 섹터 및 시총 정보 한꺼번에 가져오기
    tickers_obj = yf.Tickers(' '.join(tickers))
    
    results = []
    for t in tickers:
        try:
            close_s = data['Close'][t].dropna()
            if len(close_s) < 10: continue
            
            cur = close_s.iloc[-1]
            high = data['High'][t].max()
            low = data['Low'][t].min()
            
            mdd = ((cur - high) / high) * 100
            rec = ((cur - low) / low) * 100
            score = round(abs(mdd) - rec, 1)
            
            # info 호출 최소화 (에러 방지용)
            info = tickers_obj.tickers[t].info
            s_raw = info.get('sector', '기타')
            mkt_cap = (info.get('marketCap') or 0) / 1e9

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, "섹터": SECTOR_MAP.get(s_raw, s_raw), "현재가": cur,
                "MDD": mdd, "회복률": rec, "점수": score, "시총($B)": mkt_cap
            })
        except: continue
    return pd.DataFrame(results)

# UI 구성
st.title("📈 나스닥 100 섹터별 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tabs = st.tabs(["1년 분석", "2년 분석", "3년 분석"])
for i, tab in enumerate(tabs):
    with tab:
        with st.spinner(f"{i+1}년 데이터를 분석 중입니다..."):
            df = fetch_data(i+1)
            if not df.empty:
                st.dataframe(
                    df.sort_values("점수", ascending=False),
                    use_container_width=True, hide_index=True,
                    column_order=["신호", "티커", "섹터", "현재가", "MDD", "회복률", "점수", "시총($B)"],
                    column_config={
                        "현재가": st.column_config.NumberColumn(format="$%.2f"),
                        "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                        "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                        "시총($B)": st.column_config.NumberColumn(format="$%.1f B")
                    }
                )
            else:
                st.error("데이터를 가져오지 못했습니다. 잠시 후 [Clear Cache]를 시도해 주세요.")
