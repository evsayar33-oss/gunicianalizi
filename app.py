import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone, timedelta
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. UI VE TERMINAL YAPILANDIRMASI
# ==========================================
st.set_page_config(page_title="TIER-1 GLOBAL TERMINAL v6.0", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { color: #00E676; font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .session-live { background-color: #1B5E20; color: #00E676; padding: 4px 8px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; }
    .session-off { background-color: #E65100; color: #FFA726; padding: 4px 8px; border-radius: 4px; font-weight: bold; border: 1px solid #FFA726; }
    </style>
    """, unsafe_allow_html=True)

# Otomatik yenileme (2 dakikada bir)
count = st_autorefresh(interval=120000, limit=None, key="macro_60_refresh")

# ==========================================
# 2. KURUMSAL QUANT MOTORU (v6.0 DEFENSIVE)
# ==========================================
class RobustMacroEngine:
    def __init__(self):
        # 100% Kesintisiz Çalışan Likit Varlık Havuzu
        self.tickers = {
            'SPX': 'SPY', 'NQ': 'QQQ', 'XAU': 'GLD', 'XAG': 'SLV',
            'DXY': 'UUP', 'US10Y': '^TNX', 'TIP': 'TIP', 'TLT': 'TLT',
            'HYG': 'HYG', 'LQD': 'LQD', 'VIX': '^VIX', 'XLK': 'XLK',
            'XLF': 'XLF', 'RSP': 'RSP', 'COPPER': 'FCX', 'OIL': 'USO',
            'JPY': 'JPY=X', 'BTC': 'BTC-USD', 'XME': 'XME'
        }
        self.lookback_days = '5d' # 5 günlük hızlı ve kesintisiz çekim
        self.interval = '15m'
        self.z_window = 48        # 48 Bar (~2 Günlük Stabilite)
        self.inertia_span = 6

    def get_current_market_regime(self):
        """TSİ (UTC+3) Seans Tespit Motoru"""
        now_utc = datetime.now(timezone.utc)
        now_trt = now_utc + timedelta(hours=3)
        weekday = now_trt.weekday()
        time_decimal = now_trt.hour + now_trt.minute / 60.0

        if weekday >= 5:
            return "HAFTA SONU (24/7 GLOBAL MAKRO)", False
        
        # 16:30 - 23:00 TSİ Canlı Seans
        if 16.5 <= time_decimal < 23.0:
            return "WALL STREET NAKİT SEANSI (DİNAMİK OLS)", True
        else:
            return "LONDRA/ASYA & PRE-MARKET (KÜRESEL SENTETİK AKIŞ)", False

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
        
        def calc_smooth_velocity(series):
            ret = np.log(series / series.shift(1)).fillna(0)
            vel_4h = ret.ewm(span=12).mean() * 12
            vel_8h = ret.ewm(span=24).mean() * 24
            return (0.7 * vel_4h) + (0.3 * vel_8h)

        # 24/7 Global Akışlar
        features['BTC_Liquidity'] = calc_smooth_velocity(df['BTC']) if 'BTC' in df else 0
        features['Carry_Trade'] = calc_smooth_velocity(df['JPY']) if 'JPY' in df else 0
        features['DXY_Ret'] = calc_smooth_velocity(df['DXY']) if 'DXY' in df else 0
        features['US10Y_Ret'] = calc_smooth_velocity(df['US10Y']) if 'US10Y' in df else 0
        features['VIX_Ret'] = calc_smooth_velocity(df['VIX']) if 'VIX' in df else 0
        
        if 'XAU' in df and 'OIL' in df: features['Gold_Oil'] = calc_smooth_velocity(df['XAU'] / (df['OIL'] + 1e-6))
        if 'COPPER' in df and 'XAU' in df: features['Copper_Gold'] = calc_smooth_velocity(df['COPPER'] / (df['XAU'] + 1e-6))
        if 'XAG' in df and 'XAU' in df: features['SLV_GLD_Beta'] = calc_smooth_velocity(df['XAG'] / (df['XAU'] + 1e-6))
        if 'XME' in df and 'XAU' in df: features['XME_GLD_Ratio'] = calc_smooth_velocity(df['XME'] / (df['XAU'] + 1e-6))
        
        if 'TIP' in df and 'TLT' in df: features['Real_Yield_Proxy'] = calc_smooth_velocity(df['TIP'] / (df['TLT'] + 1e-6))
        if 'HYG' in df and 'LQD' in df: features['HYG_LQD_Spread'] = calc_smooth_velocity(df['HYG'] / (df['LQD'] + 1e-6))
        if 'HYG' in df and 'TLT' in df: features['HYG_TLT_Spread'] = calc_smooth_velocity(df['HYG'] / (df['TLT'] + 1e-6))
        if 'XLK' in df and 'XLF' in df: features['XLK_XLF_Rotation'] = calc_smooth_velocity(df['XLK'] / (df['XLF'] + 1e-6))
        if 'SPX' in df and 'RSP' in df: features['SPY_RSP_Breadth'] = calc_smooth_velocity(df['SPX'] / (df['RSP'] + 1e-6))
        
        if 'TLT' in df:
            tlt_ret = np.log(df['TLT'] / df['TLT'].shift(1)).abs().fillna(0)
            features['Bond_Vol_Shock'] = tlt_ret.ewm(span=12).mean() * 1000

        for col in ['SPX', 'NQ', 'XAU', 'XAG']:
            if col in df: features[f'{col}_Ret'] = calc_smooth_velocity(df[col])

        smoothed_features = features.ewm(span=self.inertia_span).mean()
        return smoothed_features.ffill().bfill()

    def dynamic_z_score_engine(self, df):
        if df.empty:
            return pd.DataFrame()
        mean = df.rolling(window=self.z_window, min_periods=12).mean()
        std = df.rolling(window=self.z_window, min_periods=12).std()
        z_scores = (df - mean) / (std + 1e-6)
        return z_scores.fillna(0)

    def compute_trajectory(self, z_features, target_ret_col, is_live_session, asset_type):
        empty_df = pd.DataFrame(columns=['Katman (Makro Faktör)', '4-Saatlik İvme (Z-Score)', 'Dinamik Ağırlık (%)', 'Net Katkı'])
        
        # Kesin Emniyet Kilidi: Boş veri durumunda çöküşü önle
        if z_features.empty or len(z_features) == 0:
            return 0.0, empty_df

        latest_z = z_features.iloc[-1].clip(-3.0, 3.0)
        breakdown = []

        # CANLI SEANS (WALL STREET AÇIK)
        if is_live_session and len(z_features) >= self.z_window:
            if asset_type == 'SPX':
                feature_matrix = ['VIX_Ret', 'HYG_LQD_Spread', 'HYG_TLT_Spread', 'SPY_RSP_Breadth', 'XLK_XLF_Rotation', 'Real_Yield_Proxy', 'US10Y_Ret', 'Carry_Trade', 'BTC_Liquidity', 'DXY_Ret']
            elif asset_type == 'NQ':
                feature_matrix = ['Real_Yield_Proxy', 'US10Y_Ret', 'XLK_XLF_Rotation', 'VIX_Ret', 'Bond_Vol_Shock', 'Carry_Trade', 'BTC_Liquidity', 'HYG_LQD_Spread', 'DXY_Ret']
            elif asset_type == 'XAU':
                feature_matrix = ['Real_Yield_Proxy', 'US10Y_Ret', 'DXY_Ret', 'Bond_Vol_Shock', 'Gold_Oil', 'Copper_Gold', 'SLV_GLD_Beta', 'Carry_Trade', 'HYG_TLT_Spread', 'BTC_Liquidity']
            else:
                feature_matrix = ['Copper_Gold', 'XME_GLD_Ratio', 'Real_Yield_Proxy', 'DXY_Ret', 'US10Y_Ret', 'SLV_GLD_Beta', 'BTC_Liquidity', 'XLK_XLF_Rotation', 'Gold_Oil', 'HYG_LQD_Spread']

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
            
            for col in feature_matrix:
                z_val = latest_z[col] if col in latest_z else 0.0
                w_val = normalized_weights[col]
                breakdown.append({
                    'Katman (Makro Faktör)': col,
                    '4-Saatlik İvme (Z-Score)': round(z_val, 2),
                    'Dinamik Ağırlık (%)': round(w_val, 1),
                    'Net Katkı': round(z_val * (w_val / 100.0), 3)
                })

            total_score = sum(latest_z[col] * (normalized_weights[col] / 100.0) for col in feature_matrix if col in latest_z)

        # SEANS DIŞI / PRE-MARKET (KÜRESEL MAKRO SENTETİK MODELİ)
        else:
            if asset_type in ['SPX', 'NQ']:
                struct_weights = {
                    'BTC_Liquidity': 30.0,
                    'Carry_Trade': 25.0,
                    'DXY_Ret': -25.0,
                    'US10Y_Ret': -15.0,
                    'Gold_Oil': -5.0
                }
            elif asset_type == 'XAU':
                struct_weights = {
                    'DXY_Ret': -35.0,
                    'US10Y_Ret': -25.0,
                    'Gold_Oil': 20.0,
                    'Carry_Trade': 10.0,
                    'Copper_Gold': -10.0
                }
            else:
                struct_weights = {
                    'Copper_Gold': 35.0,
                    'DXY_Ret': -30.0,
                    'BTC_Liquidity': 20.0,
                    'US10Y_Ret': -15.0
                }

            for col, w_val in struct_weights.items():
                z_val = latest_z[col] if col in latest_z else 0.0
                breakdown.append({
                    'Katman (Makro Faktör)': col,
                    '4-Saatlik İvme (Z-Score)': round(z_val, 2),
                    'Dinamik Ağırlık (%)': round(w_val, 1),
                    'Net Katkı': round(z_val * (w_val / 100.0), 3)
                })

            total_score = sum(latest_z[col] * (w_val / 100.0) for col, w_val in struct_weights.items() if col in latest_z)

        breakdown_df = pd.DataFrame(breakdown).sort_values('Dinamik Ağırlık (%)', ascending=False)
        final_score = np.tanh(total_score / 1.5) * 100
        return final_score, breakdown_df

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = RobustMacroEngine()
session_name, is_us_open = engine.get_current_market_regime()

st.title("🏛️ TIER-1 GLOBAL TERMINAL (v6.0)")

if is_us_open:
    st.markdown(f'<span class="session-live">🟢 {session_name}</span>', unsafe_allow_html=True)
    st.caption("Wall Street Açık: Canlı OLS Hisse/Kredi Modeli Aktif")
else:
    st.markdown(f'<span class="session-off">🟠 {session_name}</span>', unsafe_allow_html=True)
    st.caption("Piyasa Kapalı: 24/7 Global Kripto, FX, Faiz & Emtia Akış Modeli Devrede")

try:
    raw_df = engine.fetch_data()
    features_df = engine.calculate_features(raw_df)
    z_scores = engine.dynamic_z_score_engine(features_df)

    tab_spx, tab_nq, tab_xau, tab_xag = st.tabs(["S&P 500", "NASDAQ", "ALTIN (XAU)", "GÜMÜŞ (XAG)"])

    def render_view(score, table, asset_title):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"### {asset_title} 4H Rotası")
            c = "#00E676" if score > 0 else "#FF1744"
            st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score:.1f}</h1>", unsafe_allow_html=True)
            st.markdown(f"**Makro Yön:** {'🟢 GÜÇLÜ ALICILI' if score > 15 else '🔴 GÜÇLÜ SATICILI' if score < -15 else '⚪ DENGELİ / YATAY'}")
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
        score_spx, table_spx = engine.compute_trajectory(z_scores, 'SPX_Ret', is_us_open, 'SPX')
        render_view(score_spx, table_spx, "S&P 500")

    with tab_nq:
        score_nq, table_nq = engine.compute_trajectory(z_scores, 'NQ_Ret', is_us_open, 'NQ')
        render_view(score_nq, table_nq, "NASDAQ")

    with tab_xau:
        score_xau, table_xau = engine.compute_trajectory(z_scores, 'XAU_Ret', is_us_open, 'XAU')
        render_view(score_xau, table_xau, "ALTIN")

    with tab_xag:
        score_xag, table_xag = engine.compute_trajectory(z_scores, 'XAG_Ret', is_us_open, 'XAG')
        render_view(score_xag, table_xag, "GÜMÜŞ")

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
