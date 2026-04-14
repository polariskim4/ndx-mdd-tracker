import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="나스닥 100 섹터별 분석", layout="wide")

# 섹터 한글 변환 맵
SECTOR_MAP = {
    "Technology": "💻 기술", "Consumer Cyclical": "🛍️ 임의소비",
    "Communication Services": "📱 통신", "Healthcare": "🏥 헬스케어",
    "Financial Services": "🏦 금융", "Industrials": "🏭 산업재",
    "Consumer Defensive": "🛒 필수소비", "Utilities": "⚡ 유틸리티",
    "Real Estate": "🏢 부동산", "Energy": "🛢️ 에너지", "Basic Materials": "🧱 소재"
}

# 2. 나스닥 100 핵심 티커 리스트 (차단 방지를 위해 직접 제공)
def get_ndx_list():
    return [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP",
        "AZN", "LIN", "AMD", "ADBE", "CSCO", "TMUS", "CMCSA", "TXN", "INTU", "AMAT",
        "ISRG", "MU", "QCOM", "AMGN", "HON", "LRCX", "BKNG", "PANW", "VRTX", "SBUX"
    ]

# 3. 데이터 수집 및 분석 (최적화 버전)
@st.cache_data(ttl=3600)
def fetch_ndx_data(years):
    tickers = get_ndx_list()
    # 주가 데이터 일괄 다운로드
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    
    if data.empty:
        return pd.DataFrame()

    results = []
    # 시총과 섹터를 가져올 때 타임아웃 방지를 위해 yf.Tickers 사용
    bulk_info = yf.Tickers(' '.join(tickers))
    
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

            # 티커별 상세 정보 추출
            t_info = bulk_info.tickers[t].info
            s_raw = t_info.get('sector', '기타')
            mkt_cap = (t_info.get('marketCap') or 0) / 1e9

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, "섹터": SECTOR_MAP.get(s_raw, s_raw), "현재가": cur,
                "MDD": mdd, "회복률": rec, "점수": score, "시총($B)": mkt_cap
            })
        except:
            continue
            
    return pd.DataFrame(results)

# 4. 화면 구성
st.title("📈 나스닥 100 섹터별 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"Last Update (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tab1, tab2, tab3 = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

def render_tab(years, tab_obj):
    with tab_obj:
        with st.spinner(f"{years}년 데이터 분석 중..."):
            df = fetch_ndx_data(years)
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
                st.error("현재 데이터 서버 응답이 없습니다. 1분 후 다시 시도해 주세요.")

render_tab(1, tab1)
render_tab(2, tab2)
render_tab(3, tab3)
