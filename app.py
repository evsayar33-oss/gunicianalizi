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
st.set_page_config(page_title="TIER-1 QUANT MACRO TERMINAL (v8.0)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { color: #00E676; font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .ironclad-badge { background-color: #1A237E; color: #8C9EFF; padding: 4px 10px; border-radius: 4px; font-weight: bold; border: 1px solid #536DFE; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# Otomatik yenileme (2 dakikada bir)
count = st_autorefresh(interval=120000, limit=None, key="macro_80_refresh")

# ==========================================
# 2. KURUMSAL IRONCLAD MAKRO MOTORU (v8.0)
# ==========================================
class IroncladMacroEngine:
    def __init__(self):
        # 100% Senkronize 1 Saatlik Global Varlık Havuzu
        self.tickers = {
            'SPX': 'ES=F',       # S&P 500 Vadeli
            'NQ': 'NQ=F',        # Nasdaq Vadeli
            'XAU': 'GC=F',       # Altın Vadeli
            'XAG': 'SI=F',       # Gümüş Vadeli
            'COPPER': 'HG=F',    # Bakır Vadeli
            'OIL': 'CL=F',       # Ham Petrol Vadeli
            'BONDS': 'ZN=F',     # 10Y Hazine Tahvili Vadeli
            'EUR': 'EURUSD=X',   # Ters Dolar Endeksi Proxy
            'JPY': 'JPY=X',      # Carry Trade (USD/JPY)
            'BTC': 'BTC-USD'     # 24/7 Global Likidite
        }
        self.lookback_days = '1mo' # 1 Aylık Kesintisiz 1H Veri
        self.interval = '1h'       # 1 Saatlik Senkronize Barlar
        self.z_window = 24         # 24 Saatlik (1 Günlük) Z-Skor Penceresi

    @st.cache_data(ttl=60, show_spinner=False)
    def fetch_data(_self):
        """Verileri 1H senkronize olarak tek seferde çeker."""
        symbols = list(_self.tickers.values())
        try:
            df = yf.download(symbols, period=_self.lookback_days, interval=_self.interval, progress=False)['Close']
            df = df.ffill().bfill()
            inv_map = {v: k for k, v in _self.tickers.items()}
            df.rename(columns=inv_map, inplace=True)
            return df
        except Exception:
            return pd.DataFrame()

    def calculate_macro_features(self, df):
        if df.empty or len(df) < 5:
            return pd.DataFrame()
            
        features = pd.DataFrame(index=df.index)
        
        # 4 Saatlik ve 8 Saatlik Bileşik Getiri İvmesi
        def calc_velocity(series):
            ret = np.log(series / series.shift(1)).fillna(0)
            vel_4h = ret.rolling(4, min_periods=1).sum()  # Son 4 Saat
            vel_8h = ret.rolling(8, min_periods=1).sum()  # Son 8 Saat
            return (0.7 * vel_4h) + (0.3 * vel_8h)

        # 1. KÜRESEL ÇAPRAZ MAKRO RASYOLAR
        features['Copper_Gold'] = calc_velocity(df['COPPER'] / (df['XAU'] + 1e-6))
        features['Gold_Oil'] = calc_velocity(df['XAU'] / (df['OIL'] + 1e-6))
        features['SLV_GLD_Beta'] = calc_velocity(df['XAG'] / (df['XAU'] + 1e-6))
        
        # 2. LİKİDİTE, FAİZ & FX AKIŞLARI
        features['BTC_Liquidity'] = calc_velocity(df['BTC'])
        features['Carry_Trade'] = calc_velocity(df['JPY'])
        features['DXY_Pressure'] = -calc_velocity(df['EUR'])      # EUR Düşüşü = Dolar Artışı
        features['Bond_Yield_Pressure'] = -calc_velocity(df['BONDS']) # Tahvil Düşüşü = Faiz Artışı
        
        return features.ffill().bfill()

    def dynamic_z_score_engine(self, df):
        if df.empty:
            return pd.DataFrame()
        mean = df.rolling(window=self.z_window, min_periods=4).mean()
        std = df.rolling(window=self.z_window, min_periods=4).std()
        z_scores = (df - mean) / (std + 1e-6)
        return z_scores.fillna(0)

    def compute_asset_score(self, z_features, asset_type):
        """Bayesian Yapısal Makro Modeli (Asla 0'a Çökmez)."""
        latest_z = z_features.iloc[-1].clip(-3.0, 3.0)
        
        # HEDGE FUND YAPISAL MAKRO KATSAYILARI
        if asset_type == 'SPX':
            weights = {
                'BTC_Liquidity': 25.0,        # Global Risk İştahı (+)
                'Carry_Trade': 20.0,          # Dolar/Yen Fonlama Akışı (+)
                'DXY_Pressure': -25.0,        # Dolar Güçlenmesi (-)
                'Bond_Yield_Pressure': -20.0, # Faiz Baskısı (-)
                'Copper_Gold': 10.0           # Küresel Büyüme İvmesi (+)
            }
        elif asset_type == 'NQ':
            weights = {
                'BTC_Liquidity': 30.0,        # Yüksek Beta Likidite (+)
                'Carry_Trade': 20.0,          # Tech Hedge Fonlama (+)
                'Bond_Yield_Pressure': -25.0, # İskonto Oranı / Faiz Baskısı (-)
                'DXY_Pressure': -15.0,        # Çokuluslu Gelir Baskısı (-)
                'Copper_Gold': 10.0           # Büyüme Desteği (+)
            }
        elif asset_type == 'XAU':
            weights = {
                'DXY_Pressure': -35.0,        # Dolar Fiyatlama Tabanı (-)
                'Bond_Yield_Pressure': -30.0, # Fırsat Maliyeti / Faiz (-)
                'Gold_Oil': 15.0,             # Stagflasyon Korunması (+)
                'Carry_Trade': 10.0,          # Güvenli Liman Uyumu (+)
                'SLV_GLD_Beta': 10.0          # Değerli Maden İştahı (+)
            }
        else: # XAG
            weights = {
                'Copper_Gold': 35.0,          # Sanayi Talebi İvmesi (+)
                'DXY_Pressure': -25.0,        # Dolar Baskısı (-)
                'BTC_Liquidity': 20.0,        # Yüksek Beta Emtia Talebi (+)
                'Bond_Yield_Pressure': -10.0, # Faiz Baskısı (-)
                'Gold_Oil': 10.0              # Hammadde Enflasyon Baskısı (+)
            }

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
engine = IroncladMacroEngine()

st.title("🏛️ TIER-1 GLOBAL TERMINAL (v8.0)")
st.markdown('<span class="ironclad-badge">🛡️ IRONCLAD BAYESIAN MACRO ENGINE (24/7 ACTIVE)</span>', unsafe_allow_html=True)
st.caption("1H Senkronize CME Vadeli & FX Akışları | 4-Saatlik Kesintisiz Makro Yön")

try:
    raw_df = engine.fetch_data()
    
    if raw_df.empty or len(raw_df) < 5:
        st.error("Piyasa verileri indirilemedi. Lütfen bağlantınızı kontrol edin.")
    else:
        features_df = engine.calculate_macro_features(raw_df)
        z_scores = engine.dynamic_z_score_engine(features_df)

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
            score_spx, table_spx = engine.compute_asset_score(z_scores, 'SPX')
            render_view(score_spx, table_spx, "S&P 500 (ES=F)")

        with tab_nq:
            score_nq, table_nq = engine.compute_asset_score(z_scores, 'NQ')
            render_view(score_nq, table_nq, "NASDAQ (NQ=F)")

        with tab_xau:
            score_xau, table_xau = engine.compute_asset_score(z_scores, 'XAU')
            render_view(score_xau, table_xau, "ALTIN (GC=F)")

        with tab_xag:
            score_xag, table_xag = engine.compute_asset_score(z_scores, 'XAG')
            render_view(score_xag, table_xag, "GÜMÜŞ (SI=F)")

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
