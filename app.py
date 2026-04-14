import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="나스닥 100 섹터 분석", layout="wide")

SECTOR_MAP = {
    "Technology": "💻 기술", "Consumer Cyclical": "🛍️ 임의소비",
    "Communication Services": "📱 통신", "Healthcare": "🏥 헬스케어",
    "Financial Services": "🏦 금융", "Industrials": "🏭 산업재",
    "Consumer Defensive": "🛒 필수소비", "Utilities": "⚡ 유틸리티",
    "Real Estate": "🏢 부동산", "Energy": "🛢️ 에너지", "Basic Materials": "🧱 소재"
}

# 2. 안정적인 분석을 위한 핵심 티커 리스트
def get_verified_tickers():
    return [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP",
        "ADBE", "CSCO", "TMUS", "CMCSA", "TXN", "INTU", "AMAT", "QCOM", "ISRG", "MU",
        "AMGN", "HON", "LRCX", "BKNG", "PANW", "VRTX", "SBUX", "MDLZ", "GILD", "INTC"
    ]

# 3. 데이터 수집 함수 (안정성 강화)
@st.cache_data(ttl=3600)
def fetch_analysis_data(years):
    tickers = get_verified_tickers()
    # 일괄 다운로드로 속도 향상 및 차단 방지
    try:
        data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False, group_by='ticker')
    except:
        return pd.DataFrame()

    results = []
    for t in tickers:
        try:
            # 주가 데이터 추출
            df_t = data[t].dropna()
            if df_t.empty: continue
            
            cur = df_t['Close'].iloc[-1]
            high = df_t['High'].max()
            low = df_t['Low'].min()
            
            mdd = ((cur - high) / high) * 100
            rec = ((cur - low) / low) * 100
            # 1. 점수 계산 후 소수점 한자리로 통일
            score = round(abs(mdd) - rec, 1)

            # 섹터 및 시총 정보 (개별 호출 최소화)
            info = yf.Ticker(t).info
            s_raw = info.get('sector', '기타')
            mkt_cap = (info.get('marketCap') or 0) / 1e9

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, "섹터": SECTOR_MAP.get(s_raw, s_raw), "현재가": cur,
                "MDD": mdd, "회복률": rec, "점수": score, "시총($B)": mkt_cap
            })
        except: continue
    return pd.DataFrame(results)

# 4. 메인 화면 UI
st.title("📈 나스닥 100 섹터별 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tabs = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

for i, tab in enumerate(tabs):
    years = i + 1
    with tab:
        with st.spinner(f"{years}년 데이터를 정밀 분석 중입니다..."):
            res_df = fetch_analysis_data(years)
            if not res_df.empty:
                st.dataframe(
                    res_df.sort_values("점수", ascending=False),
                    use_container_width=True, hide_index=True,
                    column_order=["신호", "티커", "섹터", "현재가", "MDD", "회복률", "점수", "시총($B)"],
                    column_config={
                        "현재가": st.column_config.NumberColumn(format="$%.2f"),
                        "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                        "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                        "점수": st.column_config.NumberColumn(format="%.1f"), # 소수점 한자리 통일
                        "시총($B)": st.column_config.NumberColumn(format="$%.1f B")
                    }
                )
            else:
                st.error("데이터 서버 응답이 지연되고 있습니다. 잠시 후 상단 메뉴에서 [Clear Cache]를 눌러주세요.")
