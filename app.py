import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
import io
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="나스닥 100 실시간 MDD 분석", page_icon="💻", layout="wide")

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
            return sorted(df[col].astype(str).str.strip().str.replace('.', '-', regex=False).unique().tolist())
    except:
        # 실패 시 기본 우량주 리스트 반환
        return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "PEP", "COST"]

# 3. 데이터 분석 함수 (시총 제거로 속도 최적화 및 고가/저가 추가)
@st.cache_data(ttl=3600)
def fetch_analysis(years):
    tickers = get_ndx_tickers()
    # 주가 데이터 일괄 다운로드 (매우 빠름)
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    if data.empty: return pd.DataFrame()

    results = []
    
    for t in tickers:
        try:
            close_series = data['Close'][t].dropna()
            if len(close_series) < 10: continue
            
            high_val = data['High'][t].max()
            low_val = data['Low'][t].min()
            cur_price = close_series.iloc[-1]
            
            # 지표 계산
            mdd = ((cur_price - high_val) / high_val) * 100
            rec = ((cur_price - low_val) / low_val) * 100
            score = round(abs(mdd) - rec, 1)

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, 
                "현재가": cur_price, 
                "고가/저가": f"${high_val:.2f} / ${low_val:.2f}", # 신규 추가
                "MDD": mdd, 
                "회복률": rec, 
                "점수": score
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
        with st.spinner(f"나스닥 100 {years}년치 데이터 분석 중..."):
            df = fetch_analysis(years)
            if not df.empty:
                # 칼럼 순서 정의
                display_cols = ["신호", "티커", "현재가", "고가/저가", "MDD", "회복률", "점수"]
                
                st.dataframe(
                    df[display_cols].sort_values("점수", ascending=False),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "현재가": st.column_config.NumberColumn(format="$%.2f"),
                        "고가/저가": st.column_config.TextColumn("기간 내 고가 / 저가"),
                        "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                        "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                        "점수": st.column_config.NumberColumn(format="%.1f"),
                    }
                )

render_tab(1, tabs[0])
render_tab(2, tabs[1])
render_tab(3, tabs[2])
