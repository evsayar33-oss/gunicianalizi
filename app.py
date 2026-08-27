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
st.set_page_config(page_title="TIER-1 GLOBAL TERMINAL (v8.5)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { color: #00E676; font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .ironclad-badge { background-color: #1A237E; color: #8C9EFF; padding: 4px 10px; border-radius: 4px; font-weight: bold; border: 1px solid #536DFE; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# Otomatik yenileme (2 dakikada bir)
count = st_autorefresh(interval=120000, limit=None, key="macro_85_refresh")

# ==========================================
# 2. KURŞUN GEÇİRMEZ QUANT MAKRO MOTORU (v8.5)
# ==========================================
class BulletproofMacroEngine:
    def __init__(self):
        # Ana ve Yedek (Fallback) Varlık Havuzu
        self.primary_tickers = {
            'SPX': 'ES=F',       # S&P 500 Vadeli
            'NQ': 'NQ=F',        # Nasdaq Vadeli
            'XAU': 'GC=F',       # Altın Vadeli
            'XAG': 'SI=F',       # Gümüş Vadeli
            'COPPER': 'HG=F',    # Bakır Vadeli
            'OIL': 'CL=F',       # Ham Petrol Vadeli
            'BONDS': 'ZN=F',     # 10Y Tahvil Vadeli
            'EUR': 'EURUSD=X',   # Dolar Gücü
            'JPY': 'JPY=X',      # Carry Trade
            'BTC': 'BTC-USD'     # Kripto Likidite
        }
        self.fallback_tickers = {
            'SPX': 'SPY', 'NQ': 'QQQ', 'XAU': 'GLD', 'XAG': 'SLV',
            'COPPER': 'FCX', 'OIL': 'USO', 'BONDS': 'TLT',
            'EUR': 'UUP', 'JPY': 'FXY', 'BTC': 'BTC-USD'
        }
        self.lookback_days = '5d'
        self.interval = '1h'
        self.z_window = 24

    @st.cache_data(ttl=90, show_spinner=False)
    def fetch_data(_self):
        """AWS IP engeline takılmayan Direct-History & Fallback Çekim Motoru."""
        data_dict = {}
        for alias, symbol in _self.primary_tickers.items():
            s = None
            # 1. Öncelikli Varlığı Çek
            try:
                t = yf.Ticker(symbol)
                h = t.history(period=_self.lookback_days, interval=_self.interval)
                if not h.empty and 'Close' in h.columns and len(h) >= 3:
                    s = h['Close']
            except Exception:
                s = None

            # 2. Eğer takılırsa Otomatik Yedeği (Fallback ETF) Çek
            if s is None or len(s) < 3:
                try:
                    fb_sym = _self.fallback_tickers[alias]
                    t_fb = yf.Ticker(fb_sym)
                    h_fb = t_fb.history(period=_self.lookback_days, interval=_self.interval)
                    if not h_fb.empty and 'Close' in h_fb.columns:
                        s = h_fb['Close']
                except Exception:
                    s = None

            # 3. Saat Damgalarını Eşitle ve Kaydet
            if s is not None and not s.empty:
                if s.index.tz is not None:
                    s.index = s.index.tz_convert('UTC').tz_localize(None)
                data_dict[alias] = s

        df = pd.DataFrame(data_dict).ffill().bfill()
        return df

    def calculate_macro_features(self, df):
        if df.empty or len(df) < 4:
            return pd.DataFrame()
            
        features = pd.DataFrame(index=df.index)
        
        def calc_velocity(series):
            ret = np.log(series / series.shift(1)).fillna(0)
            vel_4h = ret.rolling(4, min_periods=1).sum()
            vel_8h = ret.rolling(8, min_periods=1).sum()
            return (0.7 * vel_4h) + (0.3 * vel_8h)

        if 'COPPER' in df and 'XAU' in df: features['Copper_Gold'] = calc_velocity(df['COPPER'] / (df['XAU'] + 1e-6))
        if 'XAU' in df and 'OIL' in df:    features['Gold_Oil'] = calc_velocity(df['XAU'] / (df['OIL'] + 1e-6))
        if 'XAG' in df and 'XAU' in df:    features['SLV_GLD_Beta'] = calc_velocity(df['XAG'] / (df['XAU'] + 1e-6))
        
        if 'BTC' in df:   features['BTC_Liquidity'] = calc_velocity(df['BTC'])
        if 'JPY' in df:   features['Carry_Trade'] = calc_velocity(df['JPY'])
        if 'EUR' in df:   features['DXY_Pressure'] = -calc_velocity(df['EUR'])
        if 'BONDS' in df: features['Bond_Yield_Pressure'] = -calc_velocity(df['BONDS'])
        
        return features.ffill().bfill()

    def dynamic_z_score_engine(self, df):
        if df.empty:
            return pd.DataFrame()
        mean = df.rolling(window=self.z_window, min_periods=3).mean()
        std = df.rolling(window=self.z_window, min_periods=3).std()
        z_scores = (df - mean) / (std + 1e-6)
        return z_scores.fillna(0)

    def compute_asset_score(self, z_features, asset_type):
        empty_df = pd.DataFrame(columns=['Katman (Makro Faktör)', '4-Saatlik İvme (Z-Score)', 'Yapısal Ağırlık (%)', 'Net Katkı'])
        if z_features.empty or len(z_features) == 0:
            return 0.0, empty_df

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
engine = BulletproofMacroEngine()

st.title("🏛️ TIER-1 GLOBAL TERMINAL (v8.5)")
st.markdown('<span class="ironclad-badge">🛡️ BULLETPROOF 24/7 DUAL-CHANNEL ENGINE</span>', unsafe_allow_html=True)
st.caption("Kesintisiz Global Futures & Direct Chart Feed | 4-Saatlik Kesin Makro Yön")

try:
    raw_df = engine.fetch_data()
    
    if raw_df.empty or len(raw_df) < 3:
        st.warning("Veriler API sunucularından güncelleniyor, lütfen 5 saniye sonra sayfayı yenileyin...")
    else:
        features_df = engine.calculate_macro_features(raw_df)
        z_scores = engine.dynamic_z_score_engine(features_df)

        tab_spx, tab_nq, tab_xau, tab_xag = st.tabs(["S&P 500", "NASDAQ", "ALTIN (XAU)", "GÜMÜŞ (XAG)"])

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
            score_spx, table_spx = engine.compute_asset_score(z_scores, 'SPX')
            render_view(score_spx, table_spx, "S&P 500")

        with tab_nq:
            score_nq, table_nq = engine.compute_asset_score(z_scores, 'NQ')
            render_view(score_nq, table_nq, "NASDAQ")

        with tab_xau:
            score_xau, table_xau = engine.compute_asset_score(z_scores, 'XAU')
            render_view(score_xau, table_xau, "ALTIN")

        with tab_xag:
            score_xag, table_xag = engine.compute_asset_score(z_scores, 'XAG')
            render_view(score_xag, table_xag, "GÜMÜŞ")

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
