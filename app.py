import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
import io
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="나스닥 100 실시간 MDD 분석", page_icon="📈", layout="wide")

# 영문 섹터를 한글로 변환하기 위한 딕셔너리
SECTOR_MAP = {
    "Technology": "💻 기술",
    "Consumer Cyclical": "🛍️ 임의소비재",
    "Communication Services": "📱 커뮤니케이션",
    "Healthcare": "🏥 헬스케어",
    "Financial Services": "🏦 금융",
    "Industrials": "🏭 산업재",
    "Consumer Defensive": "🛒 필수소비재",
    "Utilities": "⚡ 유틸리티",
    "Real Estate": "🏢 부동산",
    "Energy": "🛢️ 에너지",
    "Basic Materials": "🧱 소재"
}

# 2. 실시간 나스닥 100 티커 리스트 가져오기
@st.cache_data(ttl=86400)
def get_ndx_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        html_data = io.StringIO(response.text)
        tables = pd.read_html(html_data)
        
        df = next((table for table in tables if 'Ticker' in table.columns or 'Symbol' in table.columns), None)
        
        if df is not None:
            col_name = 'Ticker' if 'Ticker' in df.columns else 'Symbol'
            return sorted(df[col_name].str.replace('.', '-', regex=False).tolist())
        else:
            raise ValueError("Table not found")
    except Exception as e:
        st.error(f"리스트 갱신 실패: {e}")
        return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "PEP", "COST"]

# 3. 데이터 및 섹터 분석 함수
@st.cache_data(ttl=3600)
def fetch_analysis(years):
    tickers = get_ndx_tickers()
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    
    results = []
    tickers_obj = yf.Tickers(' '.join(tickers))
    
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
            
            # 정보 추출 (시총 및 섹터)
            t_info = tickers_obj.tickers[t].info
            
            # 섹터 정보 한글 변환 (없으면 '기타' 처리)
            raw_sector = t_info.get('sector', '기타')
            sector_kr = SECTOR_MAP.get(raw_sector, raw_sector)
            
            mkt_cap = t_info.get('marketCap') or t_info.get('totalAssets') or 0
            if not mkt_cap:
                try:
                    mkt_cap = tickers_obj.tickers[t].fast_info.get('market_cap', 0)
                except:
                    mkt_cap = 0

            mkt_cap_bn = round(mkt_cap / 1e9, 1) if mkt_cap else 0

            # 딕셔너리 순서에 '섹터' 추가
            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, 
                "섹터": sector_kr,  # <--- 티커와 현재가 사이에 추가!
                "현재가": current_val, 
                "MDD": mdd, 
                "회복률": rec, 
                "수익률": chg, 
                "점수": score, 
                "시총($B)": mkt_cap_bn
            })
        except: continue
    return pd.DataFrame(results)

# 4. 메인 UI
st.title("📈 실시간 나스닥 100 (NDX) 우량주 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')} | Wikipedia 실시간 종목 반영")

tab1, tab2, tab3 = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

def render_tab(years):
    with st.spinner(f"{years}년치 주가, 시총, 섹터 데이터를 분석 중입니다..."):
        df = fetch_analysis(years)
        if not df.empty:
            st.dataframe(
                df.sort_values("점수", ascending=False),
                use_container_width=True, hide_index=True,
                # 컬럼 순서를 강제로 지정하여 '티커' 다음에 '섹터'가 오도록 확정
                column_order=["신호", "티커", "섹터", "현재가", "MDD", "회복률", "수익률", "점수", "시총($B)"],
                column_config={
                    "섹터": st.column_config.TextColumn(width="medium"),
                    "현재가": st.column_config.NumberColumn(format="$%.2f"),
                    "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                    "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                    "수익률": st.column_config.NumberColumn(format="%.1f%%"),
                    "점수": st.column_config.NumberColumn(format="%.1f"),
                    "시총($B)": st.column_config.NumberColumn(format="$%.1f B")
                }
            )

with tab1: render_tab(1)
with tab2: render_tab(2)
with tab3: render_tab(3)
