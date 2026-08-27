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
st.set_page_config(page_title="TIER-1 24/7 GLOBAL TERMINAL v7.5", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { color: #00E676; font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .live-badge { background-color: #1B5E20; color: #00E676; padding: 4px 8px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

count = st_autorefresh(interval=120000, limit=None, key="macro_75_refresh")

# ==========================================
# 2. KURUMSAL QUANT MAKRO MOTORU (v7.5)
# ==========================================
class ResilientMacroEngine:
    def __init__(self):
        # 100% Canlı 24/5 ve 24/7 Kesintisiz Akış Tickerları
        self.tickers = {
            'SPX': 'ES=F',       # S&P 500 Vadeli
            'NQ': 'NQ=F',        # Nasdaq Vadeli
            'XAU': 'GC=F',       # Altın Vadeli
            'XAG': 'SI=F',       # Gümüş Vadeli
            'COPPER': 'HG=F',    # Bakır Vadeli
            'OIL': 'CL=F',       # Ham Petrol Vadeli
            'BONDS': 'ZN=F',     # 10Y Tahvil Vadeli
            'EUR': 'EURUSD=X',   # Dolar Gücü (EUR Düşerse Dolar Artar)
            'JPY': 'JPY=X',      # USD/JPY Carry Trade
            'BTC': 'BTC-USD'     # Bitcoin 24/7 Likidite
        }
        self.lookback_days = '5d'
        self.interval = '15m'
        self.z_window = 36        # ~1.5 Günlük Hareketli Pencere
        self.inertia_span = 4

    @st.cache_data(ttl=60, show_spinner=False)
    def fetch_data(_self):
        """Her varlığı bağımsız ve güvenli indirir, çöküşü imkansız kılar."""
        data_dict = {}
        for alias, symbol in _self.tickers.items():
            try:
                t = yf.Ticker(symbol)
                hist = t.history(period=_self.lookback_days, interval=_self.interval)
                if not hist.empty and 'Close' in hist.columns:
                    # Timezone farklarını kaldırıp eşleştir
                    s = hist['Close']
                    s.index = s.index.tz_localize(None) if s.index.tz is not None else s.index
                    data_dict[alias] = s
            except Exception:
                pass
                
        # Eğer Ticker.history boş dönerse yedek batch download
        if len(data_dict) < 4:
            try:
                symbols = list(_self.tickers.values())
                raw = yf.download(symbols, period=_self.lookback_days, interval=_self.interval, progress=False)
                if not raw.empty and 'Close' in raw:
                    for alias, symbol in _self.tickers.items():
                        if symbol in raw['Close']:
                            s = raw['Close'][symbol].dropna()
                            s.index = s.index.tz_localize(None) if s.index.tz is not None else s.index
                            data_dict[alias] = s
            except Exception:
                pass

        df = pd.DataFrame(data_dict).ffill().bfill()
        return df

    def calculate_features(self, df):
        if df.empty or len(df) < 5:
            return pd.DataFrame()
            
        features = pd.DataFrame(index=df.index)
        
        def calc_smooth_velocity(series):
            ret = np.log(series / series.shift(1)).fillna(0)
            vel_4h = ret.ewm(span=12).mean() * 12
            vel_8h = ret.ewm(span=24).mean() * 24
            return (0.7 * vel_4h) + (0.3 * vel_8h)

        # 1. KÜRESEL ÇAPRAZ MAKRO RASYOLAR
        if 'COPPER' in df and 'XAU' in df: features['Copper_Gold'] = calc_smooth_velocity(df['COPPER'] / (df['XAU'] + 1e-6))
        if 'XAU' in df and 'OIL' in df:    features['Gold_Oil'] = calc_smooth_velocity(df['XAU'] / (df['OIL'] + 1e-6))
        if 'XAG' in df and 'XAU' in df:    features['SLV_GLD_Beta'] = calc_smooth_velocity(df['XAG'] / (df['XAU'] + 1e-6))
        
        # 2. LİKİDİTE, FAİZ & DOLAR AKIŞLARI
        if 'BTC' in df:   features['BTC_Liquidity'] = calc_smooth_velocity(df['BTC'])
        if 'JPY' in df:   features['Carry_Trade'] = calc_smooth_velocity(df['JPY'])
        if 'EUR' in df:   features['DXY_Ret'] = -calc_smooth_velocity(df['EUR']) # EUR düşüşü = Dolar artışı
        if 'BONDS' in df: features['Bond_Yield_Shock'] = -calc_smooth_velocity(df['BONDS']) # Tahvil düşüşü = Faiz artışı
        
        # 3. HEDEF GETİRİLER
        for col in ['SPX', 'NQ', 'XAU', 'XAG']:
            if col in df: features[f'{col}_Ret'] = calc_smooth_velocity(df[col])

        smoothed = features.ewm(span=self.inertia_span).mean()
        return smoothed.ffill().bfill()

    def dynamic_z_score_engine(self, df):
        if df.empty:
            return pd.DataFrame()
        mean = df.rolling(window=self.z_window, min_periods=8).mean()
        std = df.rolling(window=self.z_window, min_periods=8).std()
        z_scores = (df - mean) / (std + 1e-6)
        return z_scores.fillna(0)

    def compute_trajectory(self, z_features, target_ret_col, feature_matrix):
        empty_df = pd.DataFrame(columns=['Katman (Makro Faktör)', '4-Saatlik İvme (Z-Score)', 'Dinamik Ağırlık (%)', 'Net Katkı'])
        
        if z_features.empty or len(z_features) == 0:
            return 0.0, empty_df

        # Mevcut sütunları filtrele
        active_features = [f for f in feature_matrix if f in z_features.columns]
        if not active_features:
            return 0.0, empty_df

        recent_data = z_features.tail(self.z_window)
        weights = {}
        for col in active_features:
            if target_ret_col in recent_data.columns:
                corr = recent_data[col].corr(recent_data[target_ret_col])
                weights[col] = 0.0 if pd.isna(corr) else corr
            else:
                weights[col] = 0.1 # Fallback nötr ağırlık

        total_weight = sum(abs(w) for w in weights.values()) + 1e-6
        normalized_weights = {k: (v / total_weight) * 100 for k, v in weights.items()}
        
        latest_z = z_features.iloc[-1].clip(-3.0, 3.0)
        
        breakdown = []
        for col in active_features:
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
        total_score = sum(latest_z[col] * (normalized_weights[col] / 100.0) for col in active_features if col in latest_z)
        
        final_score = np.tanh(total_score / 1.5) * 100
        return final_score, breakdown_df

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = ResilientMacroEngine()

st.title("🏛️ TIER-1 24/7 GLOBAL TERMINAL (v7.5)")
st.markdown('<span class="live-badge">🟢 CME CANLI VADELİ & KÜRESEL FX AKIŞI AKTİF</span>', unsafe_allow_html=True)
st.caption("CME E-mini, Emtia & 24/7 Küresel Likidite Akış Motoru")

try:
    raw_df = engine.fetch_data()
    
    if raw_df.empty or len(raw_df) < 5:
        st.warning("Piyasa verileri sunucudan çekiliyor, lütfen 10 saniye sonra sayfayı yenileyin...")
    else:
        features_df = engine.calculate_features(raw_df)
        z_scores = engine.dynamic_z_score_engine(features_df)

        tab_spx, tab_nq, tab_xau, tab_xag = st.tabs(["S&P 500 (ES=F)", "NASDAQ (NQ=F)", "ALTIN (GC=F)", "GÜMÜŞ (SI=F)"])

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
