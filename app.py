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
    .dataframe { font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# Otomatik yenileme (60 saniyede bir tetiklenir)
count = st_autorefresh(interval=60000, limit=None, key="macro_refresh")

# ==========================================
# 2. KURUMSAL VERİ VE HESAPLAMA MOTORU
# ==========================================
class QuantMacroEngine:
    def __init__(self):
        # YENİ ALTYAPI: Vadeli işlemler(Futures) 5dk verilerde koptuğu için en likit ETF'lere (Proxy) geçildi.
        self.tickers = {
            'XAU': 'GLD',      # Altın ETF
            'XAG': 'SLV',      # Gümüş ETF
            'SPX': 'SPY',      # S&P 500 ETF
            'NQ': 'QQQ',       # Nasdaq ETF
            'DXY': 'UUP',      # Dolar Endeksi ETF
            'US10Y': '^TNX',   # 10 Yıllık Faiz
            'VIX': '^VIX',     # VIX Endeksi
            'HYG': 'HYG',      # High Yield Kredi
            'TLT': 'TLT',      # 20+ Yıl Tahvil
            'COPPER': 'CPER',  # Bakır ETF
            'OIL': 'USO',      # Petrol ETF
            'JPY': 'FXY',      # Japon Yeni ETF
            'RSP': 'RSP'       # Eşit Ağırlıklı SPX
        }
        self.lookback_days = '5d'
        self.interval = '5m'
        self.z_window = 36 # 3 saatlik Z-Skor penceresi
        
    @st.cache_data(ttl=45, show_spinner=False)
    def fetch_market_data(_self):
        symbols = list(_self.tickers.values())
        df = yf.download(symbols, period=_self.lookback_days, interval=_self.interval, progress=False)['Close']
        df = df.ffill().bfill() 
        inv_map = {v: k for k, v in _self.tickers.items()}
        df.rename(columns=inv_map, inplace=True)
        return df

    def calculate_micro_macro_features(self, df):
        features = pd.DataFrame(index=df.index)
        features['HYG_TLT_Spread'] = df['HYG'] / df['TLT']
        
        # MOVE Endeksi (Bond Vol) için min_periods=2 eklendi ki başlarda 0 dönmesin
        features['Bond_Vol_Proxy'] = df['TLT'].pct_change().rolling(12, min_periods=2).std() * np.sqrt(252*78)
        
        features['Copper_Gold'] = df['COPPER'] / df['XAU'] 
        features['Gold_Oil'] = df['XAU'] / df['OIL'] 
        features['SPY_RSP'] = df['SPX'] / df['RSP'] 
        features['Carry_Trade'] = df['JPY']
        
        for col in ['XAU', 'XAG', 'SPX', 'NQ', 'DXY', 'US10Y', 'VIX']:
            ret = np.log(df[col] / df[col].shift(1))
            features[f'{col}_Ret'] = ret.replace([np.inf, -np.inf], np.nan).fillna(0)
            
        return features.ffill().bfill()

    def dynamic_z_score_normalization(self, df):
        mean = df.rolling(window=self.z_window, min_periods=5).mean()
        std = df.rolling(window=self.z_window, min_periods=5).std()
        # Eğer STD 0 ise (veri durağansa) 1e-8 ekleyerek NaN (Tanımsızlık) hatasını önlüyoruz
        z_scores = (df - mean) / (std + 1e-8) 
        return z_scores.fillna(0)

    def calculate_dynamic_weights_and_score(self, z_features, target_ret_col, feature_cols):
        if len(z_features) < self.z_window:
            return 0.0, {col: 0.0 for col in feature_cols}
            
        recent_data = z_features.tail(self.z_window)
        weights = {}
        for col in feature_cols:
            # Varyans 0 ise korelasyon NaN çıkar, bunu 0'a eşitliyoruz
            corr = recent_data[col].corr(recent_data[target_ret_col])
            weights[col] = 0.0 if pd.isna(corr) else corr
            
        total_weight = sum(abs(w) for w in weights.values()) + 1e-8
        normalized_weights = {k: (v / total_weight)*100 for k, v in weights.items()}
        
        latest_row = z_features.iloc[-1]
        score = sum(latest_row[col] * (normalized_weights[col]/100) for col in feature_cols)
        final_score = np.tanh(score) * 100
        return final_score, normalized_weights

# ==========================================
# 3. UYGULAMA VE GÖRSELLEŞTİRME
# ==========================================
engine = QuantMacroEngine()

st.title("🏛️ TIER-1 QUANT MACRO TERMINAL")
st.markdown(f"**Gün İçi Likidite Motoru v2.7** (ETF Altyapısı) | Ping: {count}")

try:
    raw_df = engine.fetch_market_data()
    
    if raw_df.empty:
        st.error("Veri alınamadı. YFinance API'si geçici olarak yanıt vermiyor olabilir.")
    else:
        features_df = engine.calculate_micro_macro_features(raw_df)
        z_scores = engine.dynamic_z_score_normalization(features_df)
        
        tab1, tab2, tab3, tab4 = st.tabs(["S&P 500", "NASDAQ", "ALTIN", "GÜMÜŞ"])
        
        # --- SPX MODELİ ---
        with tab1:
            spx_features = ['VIX_Ret', 'HYG_TLT_Spread', 'SPY_RSP', 'Carry_Trade', 'US10Y_Ret']
            score_spx, weights_spx = engine.calculate_dynamic_weights_and_score(z_scores, 'SPX_Ret', spx_features)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("### Anlık İbre")
                color = "#00FF00" if score_spx > 0 else "#FF0000"
                st.markdown(f"<h1 style='color: {color}; font-size: 55px; text-align: center;'>{score_spx:.1f}</h1>", unsafe_allow_html=True)
            with col2:
                w_df = pd.DataFrame(list(weights_spx.items()), columns=['Faktör', 'Ağırlık (%)']).sort_values('Ağırlık (%)', ascending=True)
                fig = go.Figure(go.Bar(x=w_df['Ağırlık (%)'], y=w_df['Faktör'], orientation='h', marker_color=np.where(w_df['Ağırlık (%)']>0, 'green', 'red')))
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=200, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
                st.plotly_chart(fig, use_container_width=True)

        # --- NQ MODELİ ---
        with tab2:
            nq_features = ['VIX_Ret', 'US10Y_Ret', 'Carry_Trade', 'Bond_Vol_Proxy', 'HYG_TLT_Spread']
            score_nq, weights_nq = engine.calculate_dynamic_weights_and_score(z_scores, 'NQ_Ret', nq_features)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("### Anlık İbre")
                color = "#00FF00" if score_nq > 0 else "#FF0000"
                st.markdown(f"<h1 style='color: {color}; font-size: 55px; text-align: center;'>{score_nq:.1f}</h1>", unsafe_allow_html=True)
            with col2:
                w_df = pd.DataFrame(list(weights_nq.items()), columns=['Faktör', 'Ağırlık (%)']).sort_values('Ağırlık (%)', ascending=True)
                fig = go.Figure(go.Bar(x=w_df['Ağırlık (%)'], y=w_df['Faktör'], orientation='h', marker_color=np.where(w_df['Ağırlık (%)']>0, 'green', 'red')))
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=200, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
                st.plotly_chart(fig, use_container_width=True)

        # --- XAU MODELİ ---
        with tab3:
            xau_features = ['US10Y_Ret', 'DXY_Ret', 'Bond_Vol_Proxy', 'Gold_Oil']
            score_xau, weights_xau = engine.calculate_dynamic_weights_and_score(z_scores, 'XAU_Ret', xau_features)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("### Anlık İbre")
                color = "#00FF00" if score_xau > 0 else "#FF0000"
                st.markdown(f"<h1 style='color: {color}; font-size: 55px; text-align: center;'>{score_xau:.1f}</h1>", unsafe_allow_html=True)
            with col2:
                w_df = pd.DataFrame(list(weights_xau.items()), columns=['Faktör', 'Ağırlık (%)']).sort_values('Ağırlık (%)', ascending=True)
                fig = go.Figure(go.Bar(x=w_df['Ağırlık (%)'], y=w_df['Faktör'], orientation='h', marker_color=np.where(w_df['Ağırlık (%)']>0, 'green', 'red')))
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=200, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
                st.plotly_chart(fig, use_container_width=True)

        # --- XAG MODELİ ---
        with tab4:
            xag_features = ['Copper_Gold', 'DXY_Ret', 'US10Y_Ret', 'XAU_Ret']
            score_xag, weights_xag = engine.calculate_dynamic_weights_and_score(z_scores, 'XAG_Ret', xag_features)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("### Anlık İbre")
                color = "#00FF00" if score_xag > 0 else "#FF0000"
                st.markdown(f"<h1 style='color: {color}; font-size: 55px; text-align: center;'>{score_xag:.1f}</h1>", unsafe_allow_html=True)
            with col2:
                w_df = pd.DataFrame(list(weights_xag.items()), columns=['Faktör', 'Ağırlık (%)']).sort_values('Ağırlık (%)', ascending=True)
                fig = go.Figure(go.Bar(x=w_df['Ağırlık (%)'], y=w_df['Faktör'], orientation='h', marker_color=np.where(w_df['Ağırlık (%)']>0, 'green', 'red')))
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=200, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        
        # TEŞHİS PANELİ (Diagnostic Panel) - Raw Veriler burada gözükecek
        with st.expander("🔍 QUANT TEŞHİS PANELİ (Ham Z-Skor & Piyasa Verileri)"):
            st.markdown("Eğer bir ağırlık **0** ise, ilgili verinin Z-Skoru sabittir (Piyasa o an illikit olabilir veya API veri vermiyordur).")
            diag_cols = ['Bond_Vol_Proxy', 'Copper_Gold', 'HYG_TLT_Spread', 'Carry_Trade']
            st.dataframe(features_df[diag_cols].tail(3), use_container_width=True)

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
