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
st.set_page_config(page_title="TIER-1 QUANT TERMINAL v4.0 (4H)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { color: #00E676; font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .horizon-badge { background-color: #1E2638; padding: 5px 10px; border-radius: 4px; font-size: 13px; border: 1px solid #00E676; color: #00E676; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Otomatik yenileme (2 dakikada bir tetiklenir)
count = st_autorefresh(interval=120000, limit=None, key="macro_4h_refresh")

# ==========================================
# 2. KURUMSAL QUANT MAKRO MOTORU (4-HOUR HORIZON)
# ==========================================
class MacroHorizon4HEngine:
    def __init__(self):
        self.tickers = {
            'SPX': 'SPY',         # S&P 500
            'NQ': 'QQQ',          # Nasdaq 100
            'XAU': 'GLD',         # Spot Altın
            'XAG': 'SLV',         # Spot Gümüş
            'DXY': 'UUP',         # Dolar Endeksi
            'US10Y': '^TNX',      # 10Y Nominal Faiz
            'TIP': 'TIP',         # TIPS (Reel Faiz)
            'TLT': 'TLT',         # 20+ Yıl Hazine Tahvili
            'HYG': 'HYG',         # Junk Kredi
            'LQD': 'LQD',         # IG Kredi
            'VIX': '^VIX',        # Volatilite Endeksi
            'VIX3M': '^VIX3M',    # 3 Aylık Volatilite
            'XLK': 'XLK',         # Teknoloji
            'XLF': 'XLF',         # Finans
            'RSP': 'RSP',         # Eşit Ağırlıklı S&P
            'COPPER': 'FCX',      # Bakır Proxy
            'OIL': 'USO',         # Petrol
            'JPY': 'FXY',         # Carry Trade
            'BTC': 'BTC-USD',     # Global Likidite
            'XME': 'XME'          # Madencilik / Sanayi
        }
        self.lookback_days = '1mo'  # 1 Aylık Veri Geçmişi
        self.interval = '15m'       # 15 Dakikalık Barlar
        self.z_window = 96          # ~3-4 Günlük (96 Bar) Rejim Hafızası
        self.smoothing_span = 4     # 1 Saatlik (4 bar) Üstel Düzeltme

    @st.cache_data(ttl=90, show_spinner=False)
    def fetch_data(_self):
        symbols = list(_self.tickers.values())
        df = yf.download(symbols, period=_self.lookback_days, interval=_self.interval, progress=False)['Close']
        df = df.ffill().bfill()
        inv_map = {v: k for k, v in _self.tickers.items()}
        df.rename(columns=inv_map, inplace=True)
        return df

    def calculate_4h_features(self, df):
        features = pd.DataFrame(index=df.index)
        
        # 1. RASYOLAR
        real_yield = df['TIP'] / df['TLT']
        hyg_lqd = df['HYG'] / df['LQD']
        hyg_tlt = df['HYG'] / df['TLT']
        xlk_xlf = df['XLK'] / df['XLF']
        spy_rsp = df['SPX'] / df['RSP']
        copper_gold = df['COPPER'] / df['XAU']
        gold_oil = df['XAU'] / df['OIL']
        slv_gld = df['XAG'] / df['XAU']
        xme_gld = df['XME'] / df['XAU']
        
        # 4 SAATLİK VE 8 SAATLİK İVME FORMÜLÜ (15m Bar Bazında)
        # shift(16) = 16 * 15dk = 4 Saat
        # shift(32) = 32 * 15dk = 8 Saat
        def calc_4h_momentum(series):
            m4h = (series / series.shift(16) - 1).fillna(0)
            m8h = (series / series.shift(32) - 1).fillna(0)
            return (0.7 * m4h) + (0.3 * m8h)

        features['Real_Yield_Proxy'] = calc_4h_momentum(real_yield)
        features['HYG_LQD_Spread'] = calc_4h_momentum(hyg_lqd)
        features['HYG_TLT_Spread'] = calc_4h_momentum(hyg_tlt)
        features['XLK_XLF_Rotation'] = calc_4h_momentum(xlk_xlf)
        features['SPY_RSP_Breadth'] = calc_4h_momentum(spy_rsp)
        features['Copper_Gold'] = calc_4h_momentum(copper_gold)
        features['Gold_Oil'] = calc_4h_momentum(gold_oil)
        features['SLV_GLD_Beta'] = calc_4h_momentum(slv_gld)
        features['XME_GLD_Ratio'] = calc_4h_momentum(xme_gld)

        # Volatilite ve Makro Şoklar (4 Saatlik Ortalama)
        features['Bond_Vol_Shock'] = df['TLT'].pct_change().abs().rolling(16, min_periods=1).mean() * 1000
        if 'VIX3M' in df.columns:
            features['VIX_Term_Structure'] = calc_4h_momentum(df['VIX'] / (df['VIX3M'] + 1e-6))
        else:
            features['VIX_Term_Structure'] = calc_4h_momentum(df['VIX'])

        features['Carry_Trade'] = calc_4h_momentum(df['JPY'])
        features['BTC_Liquidity'] = calc_4h_momentum(df['BTC'])

        # Hedef Varlıkların 4 Saatlik Momentumları
        for col in ['SPX', 'NQ', 'XAU', 'XAG', 'DXY', 'US10Y', 'VIX']:
            features[f'{col}_Ret'] = calc_4h_momentum(df[col])

        # 1 Saatlik (4 barlık) EMA Yumuşatma Filtresi
        smoothed_features = features.ewm(span=self.smoothing_span).mean()
        return smoothed_features.ffill().bfill()

    def dynamic_z_score_engine(self, df):
        mean = df.rolling(window=self.z_window, min_periods=16).mean()
        std = df.rolling(window=self.z_window, min_periods=16).std()
        z_scores = (df - mean) / (std + 1e-6)
        return z_scores.fillna(0)

    def compute_4h_trajectory(self, z_features, target_ret_col, feature_matrix):
        if len(z_features) < self.z_window:
            return 0.0, pd.DataFrame()

        recent_data = z_features.tail(self.z_window)
        weights = {}
        for col in feature_matrix:
            corr = recent_data[col].corr(recent_data[target_ret_col])
            weights[col] = 0.0 if pd.isna(corr) else corr

        total_weight = sum(abs(w) for w in weights.values()) + 1e-6
        normalized_weights = {k: (v / total_weight) * 100 for k, v in weights.items()}
        
        # Son Bar Z-Skoru (Kırpma sadece burada uygulanır)
        latest_z = z_features.iloc[-1].clip(-3.0, 3.0)
        
        breakdown = []
        for col in feature_matrix:
            z_val = latest_z[col]
            w_val = normalized_weights[col]
            contribution = z_val * (w_val / 100.0)
            breakdown.append({
                'Katman (Makro Faktör)': col,
                '4-Saatlik İvme (Z-Score)': round(z_val, 2),
                'Seans Ağırlığı (%)': round(w_val, 1),
                'Net Katkı': round(contribution, 3)
            })

        breakdown_df = pd.DataFrame(breakdown).sort_values('Seans Ağırlığı (%)', ascending=False)
        
        total_score = sum(latest_z[col] * (normalized_weights[col] / 100.0) for col in feature_matrix)
        final_score = np.tanh(total_score / 2.0) * 100
        return final_score, breakdown_df

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = MacroHorizon4HEngine()

st.title("🏛️ TIER-1 QUANT MACRO TERMINAL (v4.0)")
st.markdown('<span class="horizon-badge">⏱️ ANALİZ UFKU: ÖNÜMÜZDEKİ 4 SAAT (H4 ENGINE)</span>', unsafe_allow_html=True)
st.caption(f"15m Barlar | 4-Günlük Rejim Hafızası | Canlı Veri Akışı: Aktif ({count})")

try:
    raw_df = engine.fetch_data()
    features_df = engine.calculate_4h_features(raw_df)
    z_scores = engine.dynamic_z_score_engine(features_df)

    tab_spx, tab_nq, tab_xau, tab_xag = st.tabs(["S&P 500", "NASDAQ", "ALTIN (XAU)", "GÜMÜŞ (XAG)"])

    # --- SPX ---
    with tab_spx:
        spx_matrix = [
            'VIX_Ret', 'VIX_Term_Structure', 'HYG_LQD_Spread', 'HYG_TLT_Spread',
            'SPY_RSP_Breadth', 'XLK_XLF_Rotation', 'Real_Yield_Proxy', 'US10Y_Ret',
            'Carry_Trade', 'BTC_Liquidity', 'DXY_Ret'
        ]
        score_spx, table_spx = engine.compute_4h_trajectory(z_scores, 'SPX_Ret', spx_matrix)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### 4 Saatlik Rota Tahmini")
            c = "#00E676" if score_spx > 0 else "#FF1744"
            st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score_spx:.1f}</h1>", unsafe_allow_html=True)
            st.markdown(f"**H4 Makro Yön:** {'🟢 GÜÇLÜ ALICILI TREND' if score_spx > 20 else '🔴 GÜÇLÜ SATICILI TREND' if score_spx < -20 else '⚪ DENGELİ / YATAY'}")
        with col2:
            fig = go.Figure(go.Bar(
                x=table_spx['Seans Ağırlığı (%)'], y=table_spx['Katman (Makro Faktör)'], orientation='h',
                marker_color=np.where(table_spx['Seans Ağırlığı (%)'] > 0, '#00E676', '#FF1744')
            ))
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(table_spx, use_container_width=True, hide_index=True)

    # --- NQ ---
    with tab_nq:
        nq_matrix = [
            'Real_Yield_Proxy', 'US10Y_Ret', 'XLK_XLF_Rotation', 'VIX_Ret',
            'Bond_Vol_Shock', 'Carry_Trade', 'BTC_Liquidity', 'HYG_LQD_Spread',
            'DXY_Ret', 'VIX_Term_Structure'
        ]
        score_nq, table_nq = engine.compute_4h_trajectory(z_scores, 'NQ_Ret', nq_matrix)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### 4 Saatlik Rota Tahmini")
            c = "#00E676" if score_nq > 0 else "#FF1744"
            st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score_nq:.1f}</h1>", unsafe_allow_html=True)
            st.markdown(f"**H4 Makro Yön:** {'🟢 GÜÇLÜ ALICILI TREND' if score_nq > 20 else '🔴 GÜÇLÜ SATICILI TREND' if score_nq < -20 else '⚪ DENGELİ / YATAY'}")
        with col2:
            fig = go.Figure(go.Bar(
                x=table_nq['Seans Ağırlığı (%)'], y=table_nq['Katman (Makro Faktör)'], orientation='h',
                marker_color=np.where(table_nq['Seans Ağırlığı (%)'] > 0, '#00E676', '#FF1744')
            ))
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(table_nq, use_container_width=True, hide_index=True)

    # --- XAU ---
    with tab_xau:
        xau_matrix = [
            'Real_Yield_Proxy', 'US10Y_Ret', 'DXY_Ret', 'Bond_Vol_Shock',
            'Gold_Oil', 'Copper_Gold', 'SLV_GLD_Beta', 'Carry_Trade',
            'HYG_TLT_Spread', 'BTC_Liquidity'
        ]
        score_xau, table_xau = engine.compute_4h_trajectory(z_scores, 'XAU_Ret', xau_matrix)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### 4 Saatlik Rota Tahmini")
            c = "#00E676" if score_xau > 0 else "#FF1744"
            st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score_xau:.1f}</h1>", unsafe_allow_html=True)
            st.markdown(f"**H4 Makro Yön:** {'🟢 GÜÇLÜ ALICILI TREND' if score_xau > 20 else '🔴 GÜÇLÜ SATICILI TREND' if score_xau < -20 else '⚪ DENGELİ / YATAY'}")
        with col2:
            fig = go.Figure(go.Bar(
                x=table_xau['Seans Ağırlığı (%)'], y=table_xau['Katman (Makro Faktör)'], orientation='h',
                marker_color=np.where(table_xau['Seans Ağırlığı (%)'] > 0, '#00E676', '#FF1744')
            ))
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(table_xau, use_container_width=True, hide_index=True)

    # --- XAG ---
    with tab_xag:
        xag_matrix = [
            'Copper_Gold', 'XME_GLD_Ratio', 'Real_Yield_Proxy', 'DXY_Ret',
            'US10Y_Ret', 'SLV_GLD_Beta', 'BTC_Liquidity', 'XLK_XLF_Rotation',
            'Gold_Oil', 'HYG_LQD_Spread'
        ]
        score_xag, table_xag = engine.compute_4h_trajectory(z_scores, 'XAG_Ret', xag_matrix)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### 4 Saatlik Rota Tahmini")
            c = "#00E676" if score_xag > 0 else "#FF1744"
            st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score_xag:.1f}</h1>", unsafe_allow_html=True)
            st.markdown(f"**H4 Makro Yön:** {'🟢 GÜÇLÜ ALICILI TREND' if score_xag > 20 else '🔴 GÜÇLÜ SATICILI TREND' if score_xag < -20 else '⚪ DENGELİ / YATAY'}")
        with col2:
            fig = go.Figure(go.Bar(
                x=table_xag['Seans Ağırlığı (%)'], y=table_xag['Katman (Makro Faktör)'], orientation='h',
                marker_color=np.where(table_xag['Seans Ağırlığı (%)'] > 0, '#00E676', '#FF1744')
            ))
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(table_xag, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"4H Horizon Motoru Hatası: {str(e)}")
