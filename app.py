import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. UI VE TERMINAL YAPILANDIRMASI
# ==========================================
st.set_page_config(page_title="TIER-1 SHARPE TERMINAL (v18.0)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .status-badge { background-color: #004D40; color: #00E676; padding: 4px 10px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 12px; }
    .div-bull { background-color: #004D40; color: #00E676; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-bear { background-color: #4A148C; color: #FF1744; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #FF1744; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-neutral { background-color: #263238; color: #ECEFF1; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #78909C; font-size: 13px; display: inline-block; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2 dakikada bir otomatik yenile
count = st_autorefresh(interval=120000, limit=None, key="macro_180_refresh")

# ==========================================
# 2. SHARPE QUANT MAKRO MOTORU (v18.0)
# ==========================================
class SharpeMacroEngine:
    def __init__(self):
        self.symbol_map = {
            'ES=F': 'SPX',          # S&P 500 Vadeli
            'NQ=F': 'NQ',           # Nasdaq 100 Vadeli
            'GC=F': 'XAU',          # Altın Vadeli
            'SI=F': 'XAG',          # Gümüş Vadeli
            'HG=F': 'COPPER',       # Bakır Vadeli
            'CL=F': 'OIL',          # Ham Petrol Vadeli
            'EURUSD=X': 'EUR',      # Dolar Gücü (Ters DXY)
            'USDJPY=X': 'JPY',      # Carry Trade
            'BTC-USD': 'BTC',       # 24/7 Global Likidite
            'IEF': 'BONDS',         # 7-10Y Hazine Tahvili
            'TLT': 'TLT',           # 20+ Yıl Hazine Tahvili
            'TIP': 'TIP',           # TIPS (Reel Faiz)
            'HYG': 'HYG',           # Junk Kredi
            'LQD': 'LQD',           # IG Kredi
            'XLK': 'XLK',           # Teknoloji Sektörü
            'XLF': 'XLF',           # Finans Sektörü
            'RSP': 'RSP',           # Eşit Ağırlıklı S&P 500
            'XME': 'XME'            # Madencilik Endeksi
        }

    def fetch_single_ticker(self, symbol):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1h"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
        try:
            r = requests.get(url, headers=headers, timeout=4)
            if r.status_code == 200:
                data = r.json()
                res = data['chart']['result'][0]
                timestamps = res['timestamp']
                closes = res['indicators']['quote'][0]['close']
                df = pd.DataFrame({'time': pd.to_datetime(timestamps, unit='s'), 'Close': closes}).dropna()
                df.set_index('time', inplace=True)
                return df['Close']
        except Exception:
            pass
        return pd.Series(dtype=float)

    @st.cache_data(ttl=120, show_spinner=False)
    def fetch_all_data(_self):
        results = {}
        def worker(sym, alias):
            s = _self.fetch_single_ticker(sym)
            if not s.empty:
                results[alias] = s

        with ThreadPoolExecutor(max_workers=16) as executor:
            for sym, alias in _self.symbol_map.items():
                executor.submit(worker, sym, alias)

        df = pd.DataFrame(results).ffill().bfill()
        return df

    def calculate_sharpe_features(self, df):
        """Sıfır tabanlı mutlak getiri momentumu hesaplar (Asla yönü ters çevirmez)."""
        if df.empty or len(df) < 5:
            return pd.DataFrame()

        features = pd.DataFrame(index=df.index)
        
        # 1H (%50) + 4H (%50) Gerçek Yön İvmesi
        def calc_real_momentum(series):
            r1h = series.pct_change(1).fillna(0)
            r4h = series.pct_change(4).fillna(0)
            return (0.5 * r1h) + (0.5 * r4h)

        # 1. KENDİ FİYAT MOMENTUMLARI
        for col in ['SPX', 'NQ', 'XAU', 'XAG']:
            if col in df: features[f'{col}_Mom'] = calc_real_momentum(df[col])

        # 2. MAKRO GÖSTERGELER
        if 'TIP' in df and 'TLT' in df: features['Real_Yield_Shock'] = calc_real_momentum(df['TIP'] / (df['TLT'] + 1e-6))
        if 'HYG' in df and 'LQD' in df: features['Credit_Risk_Spread'] = calc_real_momentum(df['HYG'] / (df['LQD'] + 1e-6))
        if 'HYG' in df and 'TLT' in df: features['Credit_Flight_Safety'] = calc_real_momentum(df['HYG'] / (df['TLT'] + 1e-6))
        if 'XLK' in df and 'XLF' in df: features['Sector_Rotation'] = calc_real_momentum(df['XLK'] / (df['XLF'] + 1e-6))
        if 'SPX' in df and 'RSP' in df: features['Market_Breadth'] = calc_real_momentum(df['SPX'] / (df['RSP'] + 1e-6))
        if 'COPPER' in df and 'XAU' in df: features['Copper_Gold'] = calc_real_momentum(df['COPPER'] / (df['XAU'] + 1e-6))
        if 'XAU' in df and 'OIL' in df:    features['Gold_Oil'] = calc_real_momentum(df['XAU'] / (df['OIL'] + 1e-6))
        if 'XAG' in df and 'XAU' in df:    features['SLV_GLD_Beta'] = calc_real_momentum(df['XAG'] / (df['XAU'] + 1e-6))
        if 'XME' in df and 'XAU' in df:    features['XME_GLD_Ratio'] = calc_real_momentum(df['XME'] / (df['XAU'] + 1e-6))

        # Dolar ve Faiz (Dolar Düşüşü = Pozitif Ralli)
        if 'EUR' in df:   features['DXY_Pressure'] = -calc_real_momentum(df['EUR'])
        if 'BONDS' in df: features['Bond_Yield_Pressure'] = -calc_real_momentum(df['BONDS'])
        if 'BTC' in df:   features['BTC_Liquidity'] = calc_real_momentum(df['BTC'])
        if 'JPY' in df:   features['Carry_Trade'] = calc_real_momentum(df['JPY'])

        return features.ffill().bfill()

    def calculate_volatility_normalized_scores(self, df):
        """Ortalamayı ÇIKARMAZ! Sadece volatiliteye böler (Yükselen varlık kesinlikle pozitif kalır)."""
        if df.empty:
            return pd.DataFrame()
        # Son 24 Saatin Volatilitesi
        rolling_vol = df.rolling(24, min_periods=4).std()
        # Sharpe Skoru: Getiri / Volatilite
        sharpe_scores = df / (rolling_vol + 1e-5)
        return sharpe_scores.fillna(0)

    def compute_asset_score(self, sharpe_features, df, asset_type):
        empty_df = pd.DataFrame(columns=['Katman (Öncü Faktör)', 'Sharpe İvmesi', 'Dinamik Dikkat Ağırlığı (%)', 'Net Katkı'])
        if sharpe_features.empty:
            return {'score': 0.0, 'table': empty_df, 'msg': "⚪ DENGELİ KONSOLİDASYON", 'css': "div-neutral"}

        latest_s = sharpe_features.iloc[-1].clip(-3.0, 3.0)

        # YAPISAL BAZ AĞIRLIKLAR
        if asset_type == 'XAG': # GÜMÜŞ
            base_weights = {
                'XAG_Mom': 30.0, 'XME_GLD_Ratio': 25.0, 'Copper_Gold': 20.0,
                'SLV_GLD_Beta': 10.0, 'Real_Yield_Shock': 10.0, 'DXY_Pressure': -15.0,
                'BTC_Liquidity': 5.0, 'Gold_Oil': 5.0, 'Credit_Risk_Spread': 5.0, 'Bond_Yield_Pressure': -5.0
            }
            target_col = 'XAG'
        elif asset_type == 'XAU': # ALTIN
            base_weights = {
                'XAU_Mom': 30.0, 'Real_Yield_Shock': 25.0, 'DXY_Pressure': -20.0,
                'Bond_Yield_Pressure': -15.0, 'Gold_Oil': 15.0, 'SLV_GLD_Beta': 10.0,
                'Credit_Flight_Safety': -5.0, 'Carry_Trade': 5.0, 'Copper_Gold': -3.0, 'BTC_Liquidity': -2.0
            }
            target_col = 'XAU'
        elif asset_type == 'NQ': # NASDAQ
            base_weights = {
                'NQ_Mom': 30.0, 'Credit_Risk_Spread': 15.0, 'Sector_Rotation': 15.0,
                'BTC_Liquidity': 15.0, 'Real_Yield_Shock': -15.0, 'Bond_Yield_Pressure': -15.0,
                'Carry_Trade': 10.0, 'DXY_Pressure': -10.0, 'Market_Breadth': -5.0, 'Copper_Gold': 5.0
            }
            target_col = 'NQ'
        else: # S&P 500
            base_weights = {
                'SPX_Mom': 30.0, 'Credit_Risk_Spread': 20.0, 'Credit_Flight_Safety': 15.0,
                'Sector_Rotation': 15.0, 'BTC_Liquidity': 10.0, 'Real_Yield_Shock': -10.0,
                'Bond_Yield_Pressure': -10.0, 'Carry_Trade': 10.0, 'DXY_Pressure': -10.0, 'Market_Breadth': -5.0
            }
            target_col = 'SPX'

        # DİNAMİK ŞOK DİKKAT AĞIRLIĞI
        attention_multipliers = {}
        for col, base_w in base_weights.items():
            s = abs(latest_s[col]) if col in latest_s else 0.0
            # Güçlü hareket eden faktörün ağırlığını katla
            attention_multipliers[col] = abs(base_w) * (1.0 + (s ** 1.2))

        total_attention = sum(attention_multipliers.values()) + 1e-6

        dynamic_weights = {}
        for col, base_w in base_weights.items():
            sign = 1.0 if base_w >= 0 else -1.0
            norm_w = (attention_multipliers[col] / total_attention) * 100.0 * sign
            dynamic_weights[col] = norm_w

        breakdown = []
        for col, w_val in dynamic_weights.items():
            s_val = latest_s[col] if col in latest_s else 0.0
            contribution = s_val * (w_val / 100.0)
            breakdown.append({
                'Katman (Öncü Faktör)': col,
                'Sharpe İvmesi': round(s_val, 2),
                'Dinamik Dikkat Ağırlığı (%)': round(w_val, 1),
                'Net Katkı': round(contribution, 3)
            })

        breakdown_df = pd.DataFrame(breakdown).sort_values('Dinamik Dikkat Ağırlığı (%)', ascending=False)
        total_score = sum(latest_s[col] * (dynamic_weights[col] / 100.0) for col in dynamic_weights if col in latest_s)
        
        # -100 ile +100 Arası Kesin Yön Skoru
        final_score = np.tanh(total_score / 0.7) * 100

        # GERÇEK TREND KARARI
        if final_score > 15:
            divergence_msg = "🚀 GÜÇLÜ BOĞA TRENDİ (Alıcılar ve Likidite Piyasayı Sürüklüyor)"
            div_class = "div-bull"
        elif final_score < -15:
            divergence_msg = "🩸 GÜÇLÜ AYI BASKISI (Satıcılar ve Makro Fren Üstün)"
            div_class = "div-bear"
        else:
            divergence_msg = "⚪ DENGELİ KONSOLİDASYON (Piyasa Yönsüz)"
            div_class = "div-neutral"

        return {
            'score': final_score,
            'table': breakdown_df,
            'msg': divergence_msg,
            'css': div_class
        }

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = SharpeMacroEngine()

st.title("🏛️ TIER-1 SHARPE TERMINAL (v18.0)")
st.markdown('<span class="status-badge">⚡ SHARPE VOLATILITY-ADJUSTED MOMENTUM ENGINE</span>', unsafe_allow_html=True)
st.caption("Sıfır Tabanlı Mutlak İvme + Şok Ağırlıklandırması (Asla Ralliyi Ters Okumaz)")

try:
    raw_df = engine.fetch_all_data()
    
    if raw_df.empty or len(raw_df) < 3:
        st.warning("Veriler güncelleniyor, lütfen bekleyin...")
    else:
        features_df = engine.calculate_sharpe_features(raw_df)
        sharpe_scores = engine.calculate_volatility_normalized_scores(features_df)

        tab_spx, tab_nq, tab_xau, tab_xag = st.tabs(["S&P 500 (ES=F)", "NASDAQ (NQ=F)", "ALTIN (GC=F)", "GÜMÜŞ (SI=F)"])

        def render_view(res, asset_title):
            score = res['score']
            table = res['table']
            div_msg = res['msg']
            div_class = res['css']

            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"### {asset_title} 4H Rotası")
                
                if score > 15:
                    c = "#00E676"  # Yeşil (Boğa)
                elif score < -15:
                    c = "#FF1744"  # Kırmızı (Ayı)
                else:
                    c = "#ECEFF1"  # Beyaz (Nötr)

                st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score:.1f}</h1>", unsafe_allow_html=True)
                st.markdown(f'<div class="{div_class}">{div_msg}</div>', unsafe_allow_html=True)
            with col2:
                if not table.empty:
                    fig = go.Figure(go.Bar(
                        x=table['Dinamik Dikkat Ağırlığı (%)'], y=table['Katman (Öncü Faktör)'], orientation='h',
                        marker_color=np.where(table['Dinamik Dikkat Ağırlığı (%)'] > 0, '#00E676', '#FF1744')
                    ))
                    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
                    st.plotly_chart(fig, use_container_width=True)

            st.dataframe(table, use_container_width=True, hide_index=True)

        with tab_spx:
            render_view(engine.compute_asset_score(sharpe_scores, raw_df, 'SPX'), "S&P 500 (ES=F)")

        with tab_nq:
            render_view(engine.compute_asset_score(sharpe_scores, raw_df, 'NQ'), "NASDAQ (NQ=F)")

        with tab_xau:
            render_view(engine.compute_asset_score(sharpe_scores, raw_df, 'XAU'), "ALTIN (GC=F)")

        with tab_xag:
            render_view(engine.compute_asset_score(sharpe_scores, raw_df, 'XAG'), "GÜMÜŞ (SI=F)")

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
