import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="나스닥 100 섹터 분석", layout="wide")

# 섹터 한글 맵
SECTOR_MAP = {
    "Technology": "💻 기술", "Consumer Cyclical": "🛍️ 임의소비",
    "Communication Services": "📱 통신", "Healthcare": "🏥 헬스케어",
    "Financial Services": "🏦 금융", "Industrials": "🏭 산업재",
    "Consumer Defensive": "🛒 필수소비", "Utilities": "⚡ 유틸리티",
    "Real Estate": "🏢 부동산", "Energy": "🛢️ 에너지", "Basic Materials": "🧱 소재"
}

# 티커 리스트 (차단 방지를 위해 직접 입력 방식 병행)
def get_safe_tickers():
    return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "COST", "PEP", 
            "ADBE", "CSCO", "TMUS", "CMCSA", "INTC", "INTU", "AMAT", "QCOM", "TXN", "AMGN"]

@st.cache_data(ttl=3600)
def fetch_mdd_data(years):
    tickers = get_safe_tickers()
    # 데이터 다운로드
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    if data.empty: return pd.DataFrame()

    results = []
    # 개별 티커 분석
    for t in tickers:
        try:
            # 주가 정보
            close_s = data['Close'][t].dropna()
            if len(close_s) < 5: continue
            
            cur = close_s.iloc[-1]
            high = data['High'][t].max()
            low = data['Low'][t].min()
            
            mdd = ((cur - high) / high) * 100
            rec = ((cur - low) / low) * 100
            score = round(abs(mdd) - rec, 1)

            # 섹터 정보 (간소화 호출)
            info = yf.Ticker(t).info
            raw_s = info.get('sector', '기타')
            mkt_cap = (info.get('marketCap') or 0) / 1e9

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, 
                "섹터": SECTOR_MAP.get(raw_s, raw_s),
                "현재가": cur, 
                "MDD": mdd, 
                "회복률": rec, 
                "점수": score, 
                "시총($B)": mkt_cap
            })
        except: continue
    return pd.DataFrame(results)

# 메인 UI
st.title("📈 나스닥 100 섹터별 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"Last Update (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tab1, tab2, tab3 = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

def show_analysis(years, tab):
    with tab:
        with st.spinner("데이터 분석 중..."):
            df = fetch_mdd_data(years)
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
                st.error("현재 야후 파이낸스 연결이 원활하지 않습니다. 잠시 후 새로고침 해주세요.")

show_analysis(1, tab1)
show_analysis(2, tab2)
show_analysis(3, tab3)
