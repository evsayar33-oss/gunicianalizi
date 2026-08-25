import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. AYARLAR VE UI KONFİGÜRASYONU
# ==========================================
st.set_page_config(page_title="QUANT MACRO TERMINAL", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { color: #00FF00; font-family: 'Courier New', monospace; }
    .metric-container { border: 1px solid #333; padding: 10px; border-radius: 5px; background-color: #1A1C23; }
    </style>
    """, unsafe_allow_html=True)

# Otomatik yenileme (60 saniyede bir)
count = st_autorefresh(interval=60000, limit=None, key="macro_refresh")

# ==========================================
# 2. KURUMSAL VERİ VE HESAPLAMA MOTORU (CLASS)
# ==========================================
class QuantMacroEngine:
    def __init__(self):
        # yfinance ticker eşleştirmeleri
        self.tickers = {
            'XAU': 'GC=F', 'XAG': 'SI=F', 'SPX': '^GSPC', 'NQ': 'NQ=F',
            'DXY': 'DX-Y.NYB', 'US10Y': '^TNX', 'US2Y': '^IRX', # IRX (13W) proxy for short end intraday
            'VIX': '^VIX', 'VIX3M': '^VIX3M', 
            'HYG': 'HYG', 'TLT': 'TLT', 
            'COPPER': 'HG=F', 'OIL': 'CL=F', 'JPY': 'JPY=X',
            'RSP': 'RSP', 'SPY': 'SPY'
        }
        self.lookback_days = '5d'
        self.interval = '5m'
        self.z_window = 36 # 3 saatlik (36 bar) hareketli Z-Skor penceresi
        
    @st.cache_data(ttl=30, show_spinner=False)
    def fetch_market_data(_self):
        """Tüm piyasa verisini asenkron ve güvenli çeker, multi-index'i temizler."""
        symbols = list(_self.tickers.values())
        df = yf.download(symbols, period=_self.lookback_days, interval=_self.interval, progress=False)['Close']
        df = df.ffill().dropna()
        # Sütun isimlerini okunabilir ticker'lara çevir
        inv_map = {v: k for k, v in _self.tickers.items()}
        df.rename(columns=inv_map, inplace=True)
        return df

    def calculate_micro_macro_features(self, df):
        """Düz fiyatları alıp, kurumsal spread ve oranlara çevirir."""
        features = pd.DataFrame(index=df.index)
        
        # 1. LİKİDİTE & FAİZ (Plumbing)
        features['Yield_Curve'] = df['US10Y'] - df['US2Y']
        features['HYG_TLT_Spread'] = df['HYG'] / df['TLT'] # Kredi Stresi Proxy
        
        # 2. VOLATİLİTE YÜZEYİ (Term Structure)
        features['VIX_Term_Structure'] = df['VIX'] / df['VIX3M'] # > 1 ise panik/backwardation
        features['Bond_Vol_Proxy'] = df['TLT'].pct_change().rolling(12).std() * np.sqrt(252*78) # Sentetik MOVE
        
        # 3. ÇAPRAZ VARLIK (Cross-Asset Ratios)
        features['Copper_Gold'] = df['COPPER'] / df['XAU'] # Büyüme/Enflasyon
        features['Gold_Oil'] = df['XAU'] / df['OIL'] # Stagflasyon
        features['SPY_RSP'] = df['SPY'] / df['RSP'] # Piyasa Genişliği Daralması
        features['Carry_Trade'] = df['JPY'] # USDJPY
        
        # Fiyat momentumları (Log Returns)
        for col in ['XAU', 'XAG', 'SPX', 'NQ', 'DXY', 'US10Y']:
            features[f'{col}_Ret'] = np.log(df[col] / df[col].shift(1))
            
        return features.dropna()

    def dynamic_z_score_normalization(self, df):
        """Gelecek veriyi kullanmadan (Look-ahead bias olmadan) 3 saatlik Z-Skor hesaplar."""
        mean = df.rolling(window=self.z_window).mean()
        std = df.rolling(window=self.z_window).std()
        z_scores = (df - mean) / (std + 1e-8) # Sıfıra bölme hatasını önle
        return z_scores.dropna()

    def calculate_dynamic_weights_and_score(self, z_features, target_ret_col, feature_cols):
        """Sabit ağırlık hatasını çözen Dinamik OLS Korelasyon Motoru."""
        recent_data = z_features.tail(self.z_window) # Son 3 saat
        
        weights = {}
        for col in feature_cols:
            # Hedef varlık getirisi ile özelliğin korelasyonunu hesapla
            corr = recent_data[col].corr(recent_data[target_ret_col])
            # NaN koruması
            weights[col] = 0 if np.isnan(corr) else corr
            
        # Ağırlıkları mutlak değer toplamına göre normalize et (Toplamları 1 olsun)
        total_weight = sum(abs(w) for w in weights.values()) + 1e-8
        normalized_weights = {k: v / total_weight for k, v in weights.items()}
        
        # Anlık Mikro Skor Hesaplama (Son dakika verisi * Ağırlık)
        latest_row = z_features.iloc[-1]
        score = sum(latest_row[col] * normalized_weights[col] for col in feature_cols)
        
        # Skoru -100 ile +100 arasına sıkıştır (Tanh fonksiyonu ile)
        final_score = np.tanh(score) * 100
        return final_score, normalized_weights

# ==========================================
# 3. UYGULAMA VE GÖRSELLEŞTİRME (DASHBOARD)
# ==========================================
engine = QuantMacroEngine()

st.title("🏛️ TIER-1 QUANT MACRO TERMINAL")
st.markdown(f"**Gün İçi Likidite ve Çapraz Varlık Akış Motoru v2.5** | Canlı Yenileme: Aktif ({count})")

with st.spinner("Piyasa Verileri ve Volatilite Yüzeyleri Hesaplanıyor..."):
    try:
        raw_df = engine.fetch_market_data()
        features_df = engine.calculate_micro_macro_features(raw_df)
        z_scores = engine.dynamic_z_score_normalization(features_df)
        
        # UI Sekmeleri (Mobil için ideal)
        tab1, tab2, tab3, tab4 = st.tabs(["S&P 500 (SPX)", "NASDAQ (NQ)", "ALTIN (XAU)", "GÜMÜŞ (XAG)"])
        
        # --- SPX MODELİ ---
        with tab1:
            spx_features = ['VIX_Term_Structure', 'HYG_TLT_Spread', 'SPY_RSP', 'Yield_Curve', 'Carry_Trade', 'US10Y_Ret']
            score_spx, weights_spx = engine.calculate_dynamic_weights_and_score(z_scores, 'SPX_Ret', spx_features)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("### Anlık Yön İbresi")
                color = "#00FF00" if score_spx > 0 else "#FF0000"
                st.markdown(f"<h1 style='color: {color}; font-size: 60px; text-align: center;'>{score_spx:.1f}</h1>", unsafe_allow_html=True)
                st.markdown(f"**Hedef Rota:** {'YUKARI / Likidite Destekli' if score_spx > 15 else 'AŞAĞI / Risk-Off Akışı' if score_spx < -15 else 'NÖTR / Konsolidasyon'}")
            
            with col2:
                st.markdown("**Dinamik OLS Ağırlıkları (Son 3 Saat)**")
                w_df = pd.DataFrame(list(weights_spx.items()), columns=['Faktör', 'Etki']).sort_values('Etki', ascending=True)
                fig = go.Figure(go.Bar(x=w_df['Etki'], y=w_df['Faktör'], orientation='h', marker_color=np.where(w_df['Etki']>0, 'green', 'red')))
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
                st.plotly_chart(fig, use_container_width=True)

        # --- NQ MODELİ ---
        with tab2:
            nq_features = ['VIX_Term_Structure', 'US10Y_Ret', 'Carry_Trade', 'Bond_Vol_Proxy', 'HYG_TLT_Spread']
            score_nq, weights_nq = engine.calculate_dynamic_weights_and_score(z_scores, 'NQ_Ret', nq_features)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("### Anlık Yön İbresi")
                color = "#00FF00" if score_nq > 0 else "#FF0000"
                st.markdown(f"<h1 style='color: {color}; font-size: 60px; text-align: center;'>{score_nq:.1f}</h1>", unsafe_allow_html=True)
            with col2:
                w_df = pd.DataFrame(list(weights_nq.items()), columns=['Faktör', 'Etki']).sort_values('Etki', ascending=True)
                fig = go.Figure(go.Bar(x=w_df['Etki'], y=w_df['Faktör'], orientation='h', marker_color=np.where(w_df['Etki']>0, 'green', 'red')))
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
                st.plotly_chart(fig, use_container_width=True)

        # --- XAU MODELİ ---
        with tab3:
            xau_features = ['US10Y_Ret', 'DXY_Ret', 'Bond_Vol_Proxy', 'Gold_Oil', 'Yield_Curve']
            score_xau, weights_xau = engine.calculate_dynamic_weights_and_score(z_scores, 'XAU_Ret', xau_features)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("### Anlık Yön İbresi")
                color = "#00FF00" if score_xau > 0 else "#FF0000"
                st.markdown(f"<h1 style='color: {color}; font-size: 60px; text-align: center;'>{score_xau:.1f}</h1>", unsafe_allow_html=True)
            with col2:
                w_df = pd.DataFrame(list(weights_xau.items()), columns=['Faktör', 'Etki']).sort_values('Etki', ascending=True)
                fig = go.Figure(go.Bar(x=w_df['Etki'], y=w_df['Faktör'], orientation='h', marker_color=np.where(w_df['Etki']>0, 'green', 'red')))
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
                st.plotly_chart(fig, use_container_width=True)

        # --- XAG MODELİ ---
        with tab4:
            xag_features = ['Copper_Gold', 'DXY_Ret', 'US10Y_Ret', 'XAU_Ret']
            score_xag, weights_xag = engine.calculate_dynamic_weights_and_score(z_scores, 'XAG_Ret', xag_features)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("### Anlık Yön İbresi")
                color = "#00FF00" if score_xag > 0 else "#FF0000"
                st.markdown(f"<h1 style='color: {color}; font-size: 60px; text-align: center;'>{score_xag:.1f}</h1>", unsafe_allow_html=True)
            with col2:
                w_df = pd.DataFrame(list(weights_xag.items()), columns=['Faktör', 'Etki']).sort_values('Etki', ascending=True)
                fig = go.Figure(go.Bar(x=w_df['Etki'], y=w_df['Faktör'], orientation='h', marker_color=np.where(w_df['Etki']>0, 'green', 'red')))
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("*Modül, verileri yfinance üzerinden asenkron çeker. Ağırlıklar piyasa rejimine göre her 5 dakikada bir otomatik güncellenir.*")

    except Exception as e:
        st.error(f"Veri akışında hata oluştu. Lütfen tekrar deneyin. Detay: {e}")
