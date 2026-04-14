import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="나스닥 100 섹터 분석기", layout="wide")

# 섹터 한글화 맵
SECTOR_MAP = {
    "Technology": "💻 기술", "Consumer Cyclical": "🛍️ 임의소비",
    "Communication Services": "📱 통신", "Healthcare": "🏥 헬스케어",
    "Financial Services": "🏦 금융", "Industrials": "🏭 산업재",
    "Consumer Defensive": "🛒 필수소비", "Utilities": "⚡ 유틸리티",
    "Real Estate": "🏢 부동산", "Energy": "🛢️ 에너지", "Basic Materials": "🧱 소재"
}

# 2. 분석 티커 리스트 (안정성이 검증된 핵심 25개 종목)
def get_safe_tickers():
    return ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP", 
            "NFLX", "ADBE", "AMD", "QCOM", "INTU", "AMAT", "ISRG", "MU", "TXN", "HON",
            "BKNG", "PANW", "VRTX", "SBUX", "GILD"]

@st.cache_data(ttl=3600)
def fetch_final_data(years):
    tickers = get_safe_tickers()
    try:
        # 주가 데이터 일괄 다운로드 (속도 및 차단 방지 최적화)
        data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
        if data.empty: return pd.DataFrame()
        
        # 섹터 정보 일괄 조회를 위한 객체
        tickers_obj = yf.Tickers(' '.join(tickers))
        
        results = []
        for t in tickers:
            try:
                prices = data['Close'][t].dropna()
                if len(prices) < 10: continue
                
                cur = prices.iloc[-1]
                high = data['High'][t].max()
                low = data['Low'][t].min()
                
                mdd = ((cur - high) / high) * 100
                rec = ((cur - low) / low) * 100
                # 점수 계산 및 소수점 한 자리 통일
                score = round(abs(mdd) - rec, 1)

                # 섹터 및 시총 정보 추출
                info = tickers_obj.tickers[t].info
                s_raw = info.get('sector', '기타')
                mkt_cap = (info.get('marketCap') or 0) / 1e9

                results.append({
                    "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                    "티커": t, 
                    "섹터": SECTOR_MAP.get(s_raw, s_raw),
                    "현재가": cur, 
                    "MDD": mdd, 
                    "회복률": rec, 
                    "점수": score,
                    "시총($B)": mkt_cap
                })
            except: continue
        return pd.DataFrame(results)
    except:
        return pd.DataFrame()

# 3. UI 구성
st.title("📈 나스닥 100 섹터별 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tabs = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

def render_tab(years, target_tab):
    with target_tab:
        with st.spinner(f"{years}년 데이터를 불러오는 중..."):
            df = fetch_final_data(years)
            if not df.empty:
                st.dataframe(
                    df.sort_values("점수", ascending=False),
                    use_container_width=True, hide_index=True,
                    column_order=["신호", "티커", "섹터", "현재가", "MDD", "회복률", "점수", "시총($B)"],
                    column_config={
                        "현재가": st.column_config.NumberColumn(format="$%.2f"),
                        "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                        "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                        "점수": st.column_config.NumberColumn(format="%.1f"), # 소수점 한 자리 고정
                        "시총($B)": st.column_config.NumberColumn(format="$%.1f B")
                    }
                )
            else:
                st.error("데이터 서버 응답이 지연되고 있습니다. 잠시 후 [Clear Cache]를 눌러주세요.")

render_tab(1, tabs[0])
render_tab(2, tabs[1])
render_tab(3, tabs[2])
