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
st.set_page_config(page_title="TIER-1 24/7 FUTURES TERMINAL (v7.0)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { color: #00E676; font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .live-badge { background-color: #1B5E20; color: #00E676; padding: 4px 8px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# Otomatik yenileme (2 dakikada bir)
count = st_autorefresh(interval=120000, limit=None, key="macro_70_refresh")

# ==========================================
# 2. 24/7 CANLI VADELİ (FUTURES) MAKRO MOTORU
# ==========================================
class Global247MacroEngine:
    def __init__(self):
        # Günde 23-24 saat kesintisiz akan CME Vadeli, FX ve Kripto Sepeti
        self.tickers = {
            'SPX': 'ES=F',       # S&P 500 E-mini Vadeli (23/5 Canlı)
            'NQ': 'NQ=F',        # Nasdaq 100 E-mini Vadeli (23/5 Canlı)
            'XAU': 'GC=F',       # Spot Altın Vadeli (23/5 Canlı)
            'XAG': 'SI=F',       # Spot Gümüş Vadeli (23/5 Canlı)
            'COPPER': 'HG=F',    # Bakır Vadeli (23/5 Canlı)
            'OIL': 'CL=F',       # Ham Petrol Vadeli (23/5 Canlı)
            'BONDS': 'ZN=F',     # 10Y Hazine Tahvili Vadeli (23/5 Canlı)
            'DXY': 'DX-Y.NYB',   # Dolar Endeksi (24/5 Canlı)
            'JPY': 'JPY=X',      # USD/JPY Carry Trade (24/5 Canlı)
            'BTC': 'BTC-USD'     # Bitcoin Likidite (24/7 Canlı)
        }
        self.lookback_days = '5d'
        self.interval = '15m'
        self.z_window = 48        # 48 Bar (12 Saatlik Rejim Penceresi)
        self.inertia_span = 6     # 1.5 Saatlik Eylemsizlik Filtresi

    @st.cache_data(ttl=60, show_spinner=False)
    def fetch_data(_self):
        symbols = list(_self.tickers.values())
        try:
            df = yf.download(symbols, period=_self.lookback_days, interval=_self.interval, progress=False)['Close']
            df = df.ffill().bfill()
            inv_map = {v: k for k, v in _self.tickers.items()}
            df.rename(columns=inv_map, inplace=True)
            return df
        except Exception:
            return pd.DataFrame()

    def calculate_features(self, df):
        if df.empty:
            return pd.DataFrame()
            
        features = pd.DataFrame(index=df.index)
        
        # Sürekli EWMA Getiri Hızı (Continuous Velocity)
        def calc_smooth_velocity(series):
            ret = np.log(series / series.shift(1)).fillna(0)
            vel_4h = ret.ewm(span=16).mean() * 16
            vel_8h = ret.ewm(span=32).mean() * 32
            return (0.7 * vel_4h) + (0.3 * vel_8h)

        # 1. KÜRESEL ÇAPRAZ MAKRO RASYOLAR
        features['Copper_Gold'] = calc_smooth_velocity(df['COPPER'] / (df['XAU'] + 1e-6)) # Küresel Büyüme
        features['Gold_Oil'] = calc_smooth_velocity(df['XAU'] / (df['OIL'] + 1e-6))       # Stagflasyon
        features['SLV_GLD_Beta'] = calc_smooth_velocity(df['XAG'] / (df['XAU'] + 1e-6))   # Emtia Risk İştahı
        
        # 2. LİKİDİTE, FAİZ & DOLAR AKIŞLARI
        features['BTC_Liquidity'] = calc_smooth_velocity(df['BTC'])     # 24/7 Risk Kanaryası
        features['Carry_Trade'] = calc_smooth_velocity(df['JPY'])       # Dolar/Yen Akışı
        features['DXY_Ret'] = calc_smooth_velocity(df['DXY'])           # Dolar Gücü
        features['Bond_Yield_Shock'] = -calc_smooth_velocity(df['BONDS']) # Tahvil Fiyatı Ters = Faiz İvmesi
        
        # 3. HEDEF VARLIK GETİRİLERİ
        for col in ['SPX', 'NQ', 'XAU', 'XAG']:
            features[f'{col}_Ret'] = calc_smooth_velocity(df[col])

        # Sinyal Eylemsizliği (Inertia Filtresi)
        smoothed = features.ewm(span=self.inertia_span).mean()
        return smoothed.ffill().bfill()

    def dynamic_z_score_engine(self, df):
        if df.empty:
            return pd.DataFrame()
        mean = df.rolling(window=self.z_window, min_periods=12).mean()
        std = df.rolling(window=self.z_window, min_periods=12).std()
        z_scores = (df - mean) / (std + 1e-6)
        return z_scores.fillna(0)

    def compute_trajectory(self, z_features, target_ret_col, feature_matrix):
        empty_df = pd.DataFrame(columns=['Katman (Makro Faktör)', '4-Saatlik İvme (Z-Score)', 'Dinamik Ağırlık (%)', 'Net Katkı'])
        
        if z_features.empty or len(z_features) < 12:
            return 0.0, empty_df

        recent_data = z_features.tail(self.z_window)
        weights = {}
        for col in feature_matrix:
            if col in recent_data and target_ret_col in recent_data:
                corr = recent_data[col].corr(recent_data[target_ret_col])
                weights[col] = 0.0 if pd.isna(corr) else corr
            else:
                weights[col] = 0.0

        total_weight = sum(abs(w) for w in weights.values()) + 1e-6
        normalized_weights = {k: (v / total_weight) * 100 for k, v in weights.items()}
        
        # Uç Değer Kırpma (Sadece Son Bar)
        latest_z = z_features.iloc[-1].clip(-3.0, 3.0)
        
        breakdown = []
        for col in feature_matrix:
            z_val = latest_z[col] if col in latest_z else 0.0
            w_val = normalized_weights[col]
            contribution = z_val * (w_val / 100.0)
            breakdown.append({
                'Katman (Makro Faktör)': col,
                '4-Saatlik İvme (Z-Score)': round(z_val, 2),
                'Dinamik Ağırlık (%)': round(w_val, 1),
                'Net Katkı': round(contribution, 3)
            })

        breakdown_df = pd.DataFrame(breakdown).sort_values('Dinamik Ağırlık (%)', ascending=False)
        total_score = sum(latest_z[col] * (normalized_weights[col] / 100.0) for col in feature_matrix if col in latest_z)
        
        # -100 / +100 Tanh Sıkıştırması
        final_score = np.tanh(total_score / 1.5) * 100
        return final_score, breakdown_df

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = Global247MacroEngine()

st.title("🏛️ TIER-1 24/7 GLOBAL TERMINAL (v7.0)")
st.markdown('<span class="live-badge">🟢 CME CANLI VADELİ (FUTURES) & FX AKIŞI AKTİF</span>', unsafe_allow_html=True)
st.caption("ES=F, NQ=F, GC=F, SI=F ve 24/7 Küresel Likidite Verileriyle Canlı Hesaplanıyor")

try:
    raw_df = engine.fetch_data()
    features_df = engine.calculate_features(raw_df)
    z_scores = engine.dynamic_z_score_engine(features_df)

    tab_spx, tab_nq, tab_xau, tab_xag = st.tabs(["S&P 500 (ES=F)", "NASDAQ (NQ=F)", "ALTIN (GC=F)", "GÜMÜŞ (SI=F)"])

    # 24/7 CANLI MAKRO MATRİSLERİ
    spx_matrix = ['BTC_Liquidity', 'Carry_Trade', 'DXY_Ret', 'Bond_Yield_Shock', 'Copper_Gold', 'Gold_Oil']
    nq_matrix = ['BTC_Liquidity', 'Carry_Trade', 'Bond_Yield_Shock', 'DXY_Ret', 'Copper_Gold']
    xau_matrix = ['DXY_Ret', 'Bond_Yield_Shock', 'Gold_Oil', 'Copper_Gold', 'SLV_GLD_Beta', 'Carry_Trade', 'BTC_Liquidity']
    xag_matrix = ['Copper_Gold', 'SLV_GLD_Beta', 'DXY_Ret', 'Bond_Yield_Shock', 'BTC_Liquidity', 'Gold_Oil']

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
                    x=table['Dinamik Ağırlık (%)'], y=table['Katman (Makro Faktör)'], orientation='h',
                    marker_color=np.where(table['Dinamik Ağırlık (%)'] > 0, '#00E676', '#FF1744')
                ))
                fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=220, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
                st.plotly_chart(fig, use_container_width=True)

        if not table.empty:
            st.dataframe(table, use_container_width=True, hide_index=True)

    with tab_spx:
        score_spx, table_spx = engine.compute_trajectory(z_scores, 'SPX_Ret', spx_matrix)
        render_view(score_spx, table_spx, "S&P 500 (ES=F)")

    with tab_nq:
        score_nq, table_nq = engine.compute_trajectory(z_scores, 'NQ_Ret', nq_matrix)
        render_view(score_nq, table_nq, "NASDAQ (NQ=F)")

    with tab_xau:
        score_xau, table_xau = engine.compute_trajectory(z_scores, 'XAU_Ret', xau_matrix)
        render_view(score_xau, table_xau, "ALTIN (GC=F)")

    with tab_xag:
        score_xag, table_xag = engine.compute_trajectory(z_scores, 'XAG_Ret', xag_matrix)
        render_view(score_xag, table_xag, "GÜMÜŞ (SI=F)")

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
