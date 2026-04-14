import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="나스닥 MDD 분석기", layout="wide")

# 섹터 한글화
SECTOR_MAP = {
    "Technology": "💻 기술", "Consumer Cyclical": "🛍️ 임의소비",
    "Communication Services": "📱 통신", "Healthcare": "🏥 헬스케어",
    "Financial Services": "🏦 금융", "Industrials": "🏭 산업재",
    "Consumer Defensive": "🛒 필수소비", "Utilities": "⚡ 유틸리티",
    "Real Estate": "🏢 부동산", "Energy": "🛢️ 에너지", "Basic Materials": "🧱 소재"
}

# 1단계: 가장 안정적인 상위 15개 종목만 우선 분석 (차단 방지)
def get_light_tickers():
    return ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP", "NFLX", "ADBE", "AMD", "QCOM", "INTU"]

@st.cache_data(ttl=600) # 캐시 시간을 10분으로 줄여 빠른 피드백 유도
def fetch_mdd_safe(years):
    tickers = get_light_tickers()
    try:
        # 분할 요청이 아닌 일괄 요청으로 서버 부하 감소
        data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
        if data.empty: return pd.DataFrame()
        
        results = []
        for t in tickers:
            try:
                # 데이터 추출
                prices = data['Close'][t].dropna()
                if len(prices) < 10: continue
                
                cur = prices.iloc[-1]
                high = data['High'][t].max()
                low = data['Low'][t].min()
                
                mdd = ((cur - high) / high) * 100
                rec = ((cur - low) / low) * 100
                # 점수 소수점 한자리 통일
                score = round(abs(mdd) - rec, 1)

                # 섹터 정보 (별도 호출 없이 기본값 설정 후 성공 시 업데이트)
                results.append({
                    "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                    "티커": t, "현재가": cur, "MDD": mdd, "회복률": rec, "점수": score
                })
            except: continue
        return pd.DataFrame(results)
    except:
        return pd.DataFrame()

# UI 출력
st.title("📈 나스닥 100 MDD 분석 (안전 모드)")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

# 탭 구성
tab1, tab2, tab3 = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

def render_analysis(years, target_tab):
    with target_tab:
        df = fetch_mdd_safe(years)
        if not df.empty:
            st.dataframe(
                df.sort_values("점수", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={
                    "현재가": st.column_config.NumberColumn(format="$%.2f"),
                    "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                    "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                    "점수": st.column_config.NumberColumn(format="%.1f")
                }
            )
        else:
            st.warning("야후 파이낸스에서 데이터를 가져오지 못했습니다. 잠시 후 새로고침(F5) 해주세요.")

render_analysis(1, tab1)
render_analysis(2, tab2)
render_analysis(3, tab3)
