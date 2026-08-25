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
st.set_page_config(page_title="TIER-1 QUANT TERMINAL v3.0", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { color: #00E676; font-family: 'Courier New', monospace; font-size: 24px; }
    h2, h3 { color: #ECEFF1; font-size: 16px; }
    .dataframe { font-size: 11px !important; }
    </style>
    """, unsafe_allow_html=True)

count = st_autorefresh(interval=60000, limit=None, key="macro_matrix_refresh")

# ==========================================
# 2. KURUMSAL QUANT MAKRO MOTORU v3.0
# ==========================================
class HeavyweightMacroEngine:
    def __init__(self):
        # 16 Bağımsız Ultra-Likit Gösterge Sepeti
        self.tickers = {
            'SPX': 'SPY',         # S&P 500
            'NQ': 'QQQ',          # Nasdaq 100
            'XAU': 'GLD',         # Spot Altın
            'XAG': 'SLV',         # Spot Gümüş
            'DXY': 'UUP',         # Dolar Endeksi
            'US10Y': '^TNX',      # 10Y Nominal Faiz
            'TIP': 'TIP',         # TIPS (Enflasyon Korumalı Reel Faiz)
            'TLT': 'TLT',         # 20+ Yıl Hazine Tahvili
            'HYG': 'HYG',         # Yüksek Getirili (Junk) Kredi
            'LQD': 'LQD',         # Yatırım Seviyesi (IG) Kredi
            'VIX': '^VIX',        # CBOE Volatilite Endeksi
            'VIX3M': '^VIX3M',    # 3 Aylık Volatilite (Vade Yapısı)
            'XLK': 'XLK',         # Teknoloji Sektörü
            'XLF': 'XLF',         # Finans Sektörü
            'RSP': 'RSP',         # Eşit Ağırlıklı S&P (Breadth)
            'COPPER': 'FCX',      # Bakır Proxy (Freeport)
            'OIL': 'USO',         # Ham Petrol
            'JPY': 'FXY',         # Carry Trade / Fonlama
            'BTC': 'BTC-USD',     # 7/24 Global Likidite Kanaryası
            'XME': 'XME'          # Sanayi Metalleri Madencilik
        }
        self.lookback_days = '5d'
        self.interval = '5m'
        self.z_window = 36 # 3 saatlik hareketli normalize penceresi

    @st.cache_data(ttl=45, show_spinner=False)
    def fetch_matrix_data(_self):
        symbols = list(_self.tickers.values())
        df = yf.download(symbols, period=_self.lookback_days, interval=_self.interval, progress=False)['Close']
        df = df.ffill().bfill()
        inv_map = {v: k for k, v in _self.tickers.items()}
        df.rename(columns=inv_map, inplace=True)
        return df

    def calculate_deep_features(self, df):
        features = pd.DataFrame(index=df.index)
        
        # 1. REEL FAİZ VE GETİRİ EĞRİSİ (Real Rates & Curve)
        features['Real_Yield_Proxy'] = df['TIP'] / df['TLT']
        features['Bond_Vol_Shock'] = df['TLT'].pct_change().abs().rolling(6, min_periods=1).mean() * 1000
        
        # 2. KURUMSAL KREDİ MAKASLARI (Credit Risk & Liquidity)
        features['HYG_LQD_Spread'] = df['HYG'] / df['LQD']  # Saf Kredi Temerrüt Riski
        features['HYG_TLT_Spread'] = df['HYG'] / df['TLT']  # Güvenli Limana Kaçış Riski
        
        # 3. SEKTÖREL ROTASYON VE PİYASA GENİŞLİĞİ (Breadth & Internals)
        features['XLK_XLF_Rotation'] = df['XLK'] / df['XLF'] # Büyüme vs Değer Sektör Rotasyonu
        features['SPY_RSP_Breadth'] = df['SPX'] / df['RSP']   # Megacap Çarpıklık Endeksi
        
        # 4. VOLATİLİTE YÜZEYİ (Term Structure)
        # VIX3M eksik gelirse koruma mekanizması
        if 'VIX3M' in df.columns:
            features['VIX_Term_Structure'] = df['VIX'] / (df['VIX3M'] + 1e-6)
        else:
            features['VIX_Term_Structure'] = df['VIX'].pct_change().fillna(0)

        # 5. KÜRESEL EMTİA & SANAYİ RASYOLARI
        features['Copper_Gold'] = df['COPPER'] / df['XAU']
        features['Gold_Oil'] = df['XAU'] / df['OIL']
        features['SLV_GLD_Beta'] = df['XAG'] / df['XAU']
        features['XME_GLD_Ratio'] = df['XME'] / df['XAU']

        # 6. DÖVİZ, LİKİDİTE & KRİPTO KANARYASI
        features['Carry_Trade'] = df['JPY']
        features['BTC_Liquidity'] = np.log(df['BTC'] / df['BTC'].shift(1)).fillna(0)
        
        # Fiyat Momentumu Log-Getirileri
        for col in ['SPX', 'NQ', 'XAU', 'XAG', 'DXY', 'US10Y', 'VIX']:
            ret = np.log(df[col] / df[col].shift(1))
            features[f'{col}_Ret'] = ret.replace([np.inf, -np.inf], np.nan).fillna(0)

        return features.ffill().bfill()

    def dynamic_z_score_engine(self, df):
        mean = df.rolling(window=self.z_window, min_periods=5).mean()
        std = df.rolling(window=self.z_window, min_periods=5).std()
        z_scores = (df - mean) / (std + 1e-6)
        return z_scores.fillna(0)

    def compute_matrix_vector(self, z_features, target_ret_col, feature_matrix):
        if len(z_features) < self.z_window:
            return 0.0, pd.DataFrame()

        recent_data = z_features.tail(self.z_window)
        weights = {}
        for col in feature_matrix:
            corr = recent_data[col].corr(recent_data[target_ret_col])
            weights[col] = 0.0 if pd.isna(corr) else corr

        total_weight = sum(abs(w) for w in weights.values()) + 1e-6
        normalized_weights = {k: (v / total_weight) * 100 for k, v in weights.items()}
        
        latest_z = z_features.iloc[-1]
        
        # Detaylı Analiz Tablosu Oluşturma
        breakdown = []
        for col in feature_matrix:
            z_val = latest_z[col]
            w_val = normalized_weights[col]
            contribution = z_val * (w_val / 100.0)
            breakdown.append({
                'Katman (Feature)': col,
                'Z-Skor (İvme)': round(z_val, 2),
                'Dinamik Ağırlık (%)': round(w_val, 1),
                'Net Katkı': round(contribution, 3)
            })

        breakdown_df = pd.DataFrame(breakdown).sort_values('Dinamik Ağırlık (%)', ascending=False)
        
        # Nihai Sıkıştırılmış Skor
        total_score = sum(latest_z[col] * (normalized_weights[col] / 100.0) for col in feature_matrix)
        final_score = np.tanh(total_score) * 100
        return final_score, breakdown_df

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = HeavyweightMacroEngine()

st.title("🏛️ TIER-1 GLOBAL MACRO TERMINAL (v3.0)")
st.caption(f"16-Varlık Çapraz Matris & Dinamik OLS Motoru | Canlı Veri Akışı: Aktif ({count})")

try:
    raw_df = engine.fetch_matrix_data()
    features_df = engine.calculate_deep_features(raw_df)
    z_scores = engine.dynamic_z_score_engine(features_df)

    tab_spx, tab_nq, tab_xau, tab_xag = st.tabs(["S&P 500 (SPX)", "NASDAQ (NQ)", "ALTIN (XAU)", "GÜMÜŞ (XAG)"])

    # ------------------ S&P 500 MODELİ (11 KATMAN) ------------------
    with tab_spx:
        spx_matrix = [
            'VIX_Ret', 'VIX_Term_Structure', 'HYG_LQD_Spread', 'HYG_TLT_Spread',
            'SPY_RSP_Breadth', 'XLK_XLF_Rotation', 'Real_Yield_Proxy', 'US10Y_Ret',
            'Carry_Trade', 'BTC_Liquidity', 'DXY_Ret'
        ]
        score_spx, table_spx = engine.compute_matrix_vector(z_scores, 'SPX_Ret', spx_matrix)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### SPX Bileşik Makro Baskı")
            c = "#00E676" if score_spx > 0 else "#FF1744"
            st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score_spx:.1f}</h1>", unsafe_allow_html=True)
            st.markdown(f"**Likidite Durumu:** {'POZİTİF / Risk-On Destekli' if score_spx > 15 else 'NEGATİF / Likidite Çekilmesi' if score_spx < -15 else 'NÖTR / Ayrışma'}")
        
        with col2:
            fig = go.Figure(go.Bar(
                x=table_spx['Dinamik Ağırlık (%)'], 
                y=table_spx['Katman (Feature)'], 
                orientation='h',
                marker_color=np.where(table_spx['Dinamik Ağırlık (%)'] > 0, '#00E676', '#FF1744')
            ))
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=260, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Katman Bazlı Ayrıştırma ve Z-Skor Matrisi**")
        st.dataframe(table_spx, use_container_width=True, hide_index=True)

    # ------------------ NASDAQ MODELİ (10 KATMAN) ------------------
    with tab_nq:
        nq_matrix = [
            'Real_Yield_Proxy', 'US10Y_Ret', 'XLK_XLF_Rotation', 'VIX_Ret',
            'Bond_Vol_Shock', 'Carry_Trade', 'BTC_Liquidity', 'HYG_LQD_Spread',
            'DXY_Ret', 'VIX_Term_Structure'
        ]
        score_nq, table_nq = engine.compute_matrix_vector(z_scores, 'NQ_Ret', nq_matrix)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### NQ Bileşik Makro Baskı")
            c = "#00E676" if score_nq > 0 else "#FF1744"
            st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score_nq:.1f}</h1>", unsafe_allow_html=True)
            st.markdown(f"**Teknoloji Rotasyonu:** {'GÜÇLÜ BOĞA' if score_nq > 15 else 'AYI BASKISI' if score_nq < -15 else 'KONSOLİDASYON'}")
        
        with col2:
            fig = go.Figure(go.Bar(
                x=table_nq['Dinamik Ağırlık (%)'], 
                y=table_nq['Katman (Feature)'], 
                orientation='h',
                marker_color=np.where(table_nq['Dinamik Ağırlık (%)'] > 0, '#00E676', '#FF1744')
            ))
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=260, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Katman Bazlı Ayrıştırma ve Z-Skor Matrisi**")
        st.dataframe(table_nq, use_container_width=True, hide_index=True)

    # ------------------ ALTIN MODELİ (10 KATMAN) ------------------
    with tab_xau:
        xau_matrix = [
            'Real_Yield_Proxy', 'US10Y_Ret', 'DXY_Ret', 'Bond_Vol_Shock',
            'Gold_Oil', 'Copper_Gold', 'SLV_GLD_Beta', 'Carry_Trade',
            'HYG_TLT_Spread', 'BTC_Liquidity'
        ]
        score_xau, table_xau = engine.compute_matrix_vector(z_scores, 'XAU_Ret', xau_matrix)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### Altın Parasal Basınç")
            c = "#00E676" if score_xau > 0 else "#FF1744"
            st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score_xau:.1f}</h1>", unsafe_allow_html=True)
            st.markdown(f"**Güvenli Liman İştahı:** {'ALIM YÖNLÜ' if score_xau > 15 else 'SATIŞ YÖNLÜ' if score_xau < -15 else 'DENGEDE'}")
        
        with col2:
            fig = go.Figure(go.Bar(
                x=table_xau['Dinamik Ağırlık (%)'], 
                y=table_xau['Katman (Feature)'], 
                orientation='h',
                marker_color=np.where(table_xau['Dinamik Ağırlık (%)'] > 0, '#00E676', '#FF1744')
            ))
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=260, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Katman Bazlı Ayrıştırma ve Z-Skor Matrisi**")
        st.dataframe(table_xau, use_container_width=True, hide_index=True)

    # ------------------ GÜMÜŞ MODELİ (10 KATMAN) ------------------
    with tab_xag:
        xag_matrix = [
            'Copper_Gold', 'XME_GLD_Ratio', 'Real_Yield_Proxy', 'DXY_Ret',
            'US10Y_Ret', 'SLV_GLD_Beta', 'BTC_Liquidity', 'XLK_XLF_Rotation',
            'Gold_Oil', 'HYG_LQD_Spread'
        ]
        score_xag, table_xag = engine.compute_matrix_vector(z_scores, 'XAG_Ret', xag_matrix)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### Gümüş Sanayi & Beta Baskısı")
            c = "#00E676" if score_xag > 0 else "#FF1744"
            st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score_xag:.1f}</h1>", unsafe_allow_html=True)
            st.markdown(f"**Emtia Beta Yönü:** {'GÜÇLÜ BOĞA' if score_xag > 15 else 'AYI BASKISI' if score_xag < -15 else 'NÖTR'}")
        
        with col2:
            fig = go.Figure(go.Bar(
                x=table_xag['Dinamik Ağırlık (%)'], 
                y=table_xag['Katman (Feature)'], 
                orientation='h',
                marker_color=np.where(table_xag['Dinamik Ağırlık (%)'] > 0, '#00E676', '#FF1744')
            ))
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=260, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Katman Bazlı Ayrıştırma ve Z-Skor Matrisi**")
        st.dataframe(table_xag, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Matris Hesaplama Hatası: {str(e)}")
