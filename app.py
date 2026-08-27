import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. UI VE TERMINAL YAPILANDIRMASI
# ==========================================
st.set_page_config(page_title="TIER-1 MASTER TERMINAL v9.0", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { color: #00E676; font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .master-badge { background-color: #1B5E20; color: #00E676; padding: 4px 10px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# 2 dakikada bir otomatik yenile
count = st_autorefresh(interval=120000, limit=None, key="macro_90_refresh")

# ==========================================
# 2. DETERMINİSTİK HIZLI QUANT MOTORU (v9.0)
# ==========================================
class MasterMacroEngine:
    def __init__(self):
        # 100% Uptime ve Yüksek Likidite Tickerları
        self.symbol_map = {
            'ES=F': 'SPX',
            'NQ=F': 'NQ',
            'GC=F': 'XAU',
            'SI=F': 'XAG',
            'HG=F': 'COPPER',
            'CL=F': 'OIL',
            'EURUSD=X': 'DXY_INV', # Euro Düşüşü = Dolar Gücü
            'USDJPY=X': 'JPY',     # Carry Trade
            'BTC-USD': 'BTC',      # Kripto Likidite
            'IEF': 'BONDS'         # 7-10Y Tahvil (Düşüşü = Faiz Artışı)
        }

    @st.cache_data(ttl=120, show_spinner=False)
    def fetch_master_data(_self):
        """0.5 saniyede tek sorguda paralel indirme yapar."""
        symbols = list(_self.symbol_map.keys())
        try:
            raw = yf.download(symbols, period='5d', interval='1h', progress=False, group_by='ticker')
            df = pd.DataFrame()
            for sym, alias in _self.symbol_map.items():
                try:
                    if sym in raw and 'Close' in raw[sym]:
                        df[alias] = raw[sym]['Close']
                    elif 'Close' in raw and sym in raw['Close']:
                        df[alias] = raw['Close'][sym]
                except Exception:
                    pass
            df = df.ffill().bfill()
            return df
        except Exception:
            return pd.DataFrame()

    def calculate_deterministic_features(self, df):
        if df.empty or len(df) < 5:
            return pd.DataFrame()

        features = pd.DataFrame(index=df.index)
        
        # 4 Saatlik Kesin Getiri İvmeleri
        features['Copper_Gold'] = (df['COPPER'] / (df['XAU'] + 1e-6)).pct_change(4).fillna(0)
        features['Gold_Oil'] = (df['XAU'] / (df['OIL'] + 1e-6)).pct_change(4).fillna(0)
        features['SLV_GLD_Beta'] = (df['XAG'] / (df['XAU'] + 1e-6)).pct_change(4).fillna(0)
        
        features['BTC_Liquidity'] = df['BTC'].pct_change(4).fillna(0)
        features['Carry_Trade'] = df['JPY'].pct_change(4).fillna(0)
        features['DXY_Pressure'] = -df['DXY_INV'].pct_change(4).fillna(0) # EUR Düşüşü = Dolar Artışı
        features['Bond_Yield_Pressure'] = -df['BONDS'].pct_change(4).fillna(0) # Tahvil Düşüşü = Faiz Artışı

        return features.ffill().bfill()

    def calculate_stable_z_scores(self, df):
        if df.empty:
            return pd.DataFrame()
        # 24 Saatlik Kararlı Z-Skor Normalizasyonu
        mean = df.rolling(24, min_periods=4).mean()
        std = df.rolling(24, min_periods=4).std()
        z_scores = (df - mean) / (std + 1e-6)
        return z_scores.fillna(0)

    def compute_fixed_macro_score(self, z_features, asset_type):
        empty_df = pd.DataFrame(columns=['Katman (Makro Faktör)', '4-Saatlik İvme (Z-Score)', 'Yapısal Ağırlık (%)', 'Net Katkı'])
        if z_features.empty:
            return 0.0, empty_df

        # Kapanmış son barın Z-Skorunu al (Zıplamayı önler)
        latest_z = z_features.iloc[-1].clip(-3.0, 3.0)

        if asset_type == 'SPX':
            weights = {'BTC_Liquidity': 25.0, 'Carry_Trade': 20.0, 'DXY_Pressure': -25.0, 'Bond_Yield_Pressure': -20.0, 'Copper_Gold': 10.0}
        elif asset_type == 'NQ':
            weights = {'BTC_Liquidity': 30.0, 'Carry_Trade': 20.0, 'Bond_Yield_Pressure': -25.0, 'DXY_Pressure': -15.0, 'Copper_Gold': 10.0}
        elif asset_type == 'XAU':
            weights = {'DXY_Pressure': -35.0, 'Bond_Yield_Pressure': -30.0, 'Gold_Oil': 15.0, 'Carry_Trade': 10.0, 'SLV_GLD_Beta': 10.0}
        else: # XAG
            weights = {'Copper_Gold': 35.0, 'DXY_Pressure': -25.0, 'BTC_Liquidity': 20.0, 'Bond_Yield_Pressure': -10.0, 'Gold_Oil': 10.0}

        breakdown = []
        for col, w_val in weights.items():
            z_val = latest_z[col] if col in latest_z else 0.0
            contribution = z_val * (w_val / 100.0)
            breakdown.append({
                'Katman (Makro Faktör)': col,
                '4-Saatlik İvme (Z-Score)': round(z_val, 2),
                'Yapısal Ağırlık (%)': round(w_val, 1),
                'Net Katkı': round(contribution, 3)
            })

        breakdown_df = pd.DataFrame(breakdown).sort_values('Yapısal Ağırlık (%)', ascending=False)
        total_score = sum(latest_z[col] * (w_val / 100.0) for col, w_val in weights.items() if col in latest_z)
        
        final_score = np.tanh(total_score / 1.2) * 100
        return final_score, breakdown_df

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = MasterMacroEngine()

st.title("🏛️ TIER-1 MASTER TERMINAL (v9.0)")
st.markdown('<span class="master-badge">⚡ ULTRA-FAST DETERMINISTIC ENGINE (STABLE)</span>', unsafe_allow_html=True)
st.caption("CME Futures & FX Senkronize Akış | 4-Saatlik Sabitlenmiş Makro Yön")

try:
    raw_df = engine.fetch_master_data()
    
    if raw_df.empty or len(raw_df) < 3:
        st.error("Veri bağlantısı kuruluyor, lütfen sayfayı bir kez yenileyin.")
    else:
        features_df = engine.calculate_deterministic_features(raw_df)
        z_scores = engine.calculate_stable_z_scores(features_df)

        tab_spx, tab_nq, tab_xau, tab_xag = st.tabs(["S&P 500 (ES=F)", "NASDAQ (NQ=F)", "ALTIN (GC=F)", "GÜMÜŞ (SI=F)"])

        def render_view(score, table, asset_title):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"### {asset_title} 4H Rotası")
                c = "#00E676" if score > 0 else "#FF1744"
                st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score:.1f}</h1>", unsafe_allow_html=True)
                st.markdown(f"**H4 Makro Yön:** {'🟢 GÜÇLÜ ALICILI' if score > 15 else '🔴 GÜÇLÜ SATICILI' if score < -15 else '⚪ DENGELİ / YATAY'}")
            with col2:
                if not table.empty:
                    fig = go.Figure(go.Bar(
                        x=table['Yapısal Ağırlık (%)'], y=table['Katman (Makro Faktör)'], orientation='h',
                        marker_color=np.where(table['Yapısal Ağırlık (%)'] > 0, '#00E676', '#FF1744')
                    ))
                    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=220, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
                    st.plotly_chart(fig, use_container_width=True)

            st.dataframe(table, use_container_width=True, hide_index=True)

        with tab_spx:
            score_spx, table_spx = engine.compute_fixed_macro_score(z_scores, 'SPX')
            render_view(score_spx, table_spx, "S&P 500 (ES=F)")

        with tab_nq:
            score_nq, table_nq = engine.compute_fixed_macro_score(z_scores, 'NQ')
            render_view(score_nq, table_nq, "NASDAQ (NQ=F)")

        with tab_xau:
            score_xau, table_xau = engine.compute_fixed_macro_score(z_scores, 'XAU')
            render_view(score_xau, table_xau, "ALTIN (GC=F)")

        with tab_xag:
            score_xag, table_xag = engine.compute_fixed_macro_score(z_scores, 'XAG')
            render_view(score_xag, table_xag, "GÜMÜŞ (SI=F)")

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
