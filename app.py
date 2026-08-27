import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. UI VE TERMINAL YAPILANDIRMASI
# ==========================================
st.set_page_config(page_title="TIER-1 ULTIMATE MACRO TERMINAL (v11.0)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { color: #00E676; font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .status-badge { background-color: #1B5E20; color: #00E676; padding: 4px 10px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# 2 dakikada bir otomatik yenile
count = st_autorefresh(interval=120000, limit=None, key="macro_110_refresh")

# ==========================================
# 2. TAM TEŞEKKÜLLÜ QUANT MAKRO MOTORU (v11.0)
# ==========================================
class UltimateMacroEngine:
    def __init__(self):
        # 16 Bağımsız Ultra-Likit Global Varlık Havuzu
        self.symbol_map = {
            'ES=F': 'SPX',          # S&P 500 Vadeli
            'NQ=F': 'NQ',           # Nasdaq 100 Vadeli
            'GC=F': 'XAU',          # Altın Vadeli
            'SI=F': 'XAG',          # Gümüş Vadeli
            'HG=F': 'COPPER',       # Bakır Vadeli
            'CL=F': 'OIL',          # Ham Petrol Vadeli
            'EURUSD=X': 'EUR',      # Dolar Karşıtı FX (Ters DXY)
            'USDJPY=X': 'JPY',      # Carry Trade (USD/JPY)
            'BTC-USD': 'BTC',       # 24/7 Global Likidite Kanaryası
            'IEF': 'BONDS',         # 7-10Y Hazine Tahvili
            'TLT': 'TLT',           # 20+ Yıl Uzun Vade Tahvil
            'TIP': 'TIP',           # TIPS (Reel Faiz)
            'HYG': 'HYG',           # Yüksek Getirili (Junk) Kredi
            'LQD': 'LQD',           # Yatırım Seviyesi (IG) Kredi
            'XLK': 'XLK',           # Teknoloji Sektörü
            'XLF': 'XLF',           # Finans Sektörü
            'RSP': 'RSP',           # Eşit Ağırlıklı S&P 500 (Breadth)
            'XME': 'XME'            # Sanayi Metalleri Madencilik
        }

    def fetch_single_ticker(self, symbol):
        """Doğrudan REST JSON motoru (0.2 saniyede çeker)."""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1h"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        try:
            r = requests.get(url, headers=headers, timeout=4)
            if r.status_code == 200:
                data = r.json()
                res = data['chart']['result'][0]
                timestamps = res['timestamp']
                closes = res['indicators']['quote'][0]['close']
                df = pd.DataFrame({'time': pd.to_datetime(timestamps, unit='s'), 'Close': closes}).dropna()
                df.set_index('time', inplace=True)
                return df['Close']
        except Exception:
            pass
        return pd.Series(dtype=float)

    @st.cache_data(ttl=120, show_spinner=False)
    def fetch_all_data(_self):
        """16 varlığı paralel 16 thread ile 0.4 saniyede indirir."""
        results = {}
        def worker(sym, alias):
            s = _self.fetch_single_ticker(sym)
            if not s.empty:
                results[alias] = s

        with ThreadPoolExecutor(max_workers=16) as executor:
            for sym, alias in _self.symbol_map.items():
                executor.submit(worker, sym, alias)

        df = pd.DataFrame(results).ffill().bfill()
        return df

    def calculate_deep_features(self, df):
        if df.empty or len(df) < 5:
            return pd.DataFrame()

        features = pd.DataFrame(index=df.index)
        
        # 4 Saatlik İvme Fonksiyonu
        def calc_vel(series):
            return series.pct_change(4).fillna(0)

        # 1. REEL FAİZ & GETİRİ EĞRİSİ
        if 'TIP' in df and 'TLT' in df:
            features['Real_Yield_Shock'] = calc_vel(df['TIP'] / (df['TLT'] + 1e-6))
        if 'TLT' in df:
            features['Bond_Vol_Shock'] = df['TLT'].pct_change().abs().rolling(4, min_periods=1).mean() * 1000

        # 2. KURUMSAL KREDİ MAKASLARI
        if 'HYG' in df and 'LQD' in df:
            features['Credit_Risk_Spread'] = calc_vel(df['HYG'] / (df['LQD'] + 1e-6))
        if 'HYG' in df and 'TLT' in df:
            features['Credit_Flight_Safety'] = calc_vel(df['HYG'] / (df['TLT'] + 1e-6))

        # 3. SEKTÖREL ROTASYON & PİYASA GENİŞLİĞİ
        if 'XLK' in df and 'XLF' in df:
            features['Sector_Rotation'] = calc_vel(df['XLK'] / (df['XLF'] + 1e-6))
        if 'SPX' in df and 'RSP' in df:
            features['Market_Breadth'] = calc_vel(df['SPX'] / (df['RSP'] + 1e-6))

        # 4. KÜRESEL EMTİA VE SANAYİ RASYOLARI
        if 'COPPER' in df and 'XAU' in df:
            features['Copper_Gold'] = calc_vel(df['COPPER'] / (df['XAU'] + 1e-6))
        if 'XAU' in df and 'OIL' in df:
            features['Gold_Oil'] = calc_vel(df['XAU'] / (df['OIL'] + 1e-6))
        if 'XAG' in df and 'XAU' in df:
            features['SLV_GLD_Beta'] = calc_vel(df['XAG'] / (df['XAU'] + 1e-6))
        if 'XME' in df and 'XAU' in df:
            features['XME_GLD_Ratio'] = calc_vel(df['XME'] / (df['XAU'] + 1e-6))

        # 5. DÖVİZ, FAİZ VE 24/7 LİKİDİTE AKIŞLARI
        if 'BTC' in df:   features['BTC_Liquidity'] = calc_vel(df['BTC'])
        if 'JPY' in df:   features['Carry_Trade'] = calc_vel(df['JPY'])
        if 'EUR' in df:   features['DXY_Pressure'] = -calc_vel(df['EUR'])
        if 'BONDS' in df: features['Bond_Yield_Pressure'] = -calc_vel(df['BONDS'])

        return features.ffill().bfill()

    def calculate_stable_z_scores(self, df):
        if df.empty:
            return pd.DataFrame()
        mean = df.rolling(24, min_periods=4).mean()
        std = df.rolling(24, min_periods=4).std()
        z_scores = (df - mean) / (std + 1e-6)
        return z_scores.fillna(0)

    def compute_asset_score(self, z_features, asset_type):
        empty_df = pd.DataFrame(columns=['Katman (Makro Faktör)', '4-Saatlik İvme (Z-Score)', 'Yapısal Ağırlık (%)', 'Net Katkı'])
        if z_features.empty:
            return 0.0, empty_df

        latest_z = z_features.iloc[-1].clip(-3.0, 3.0)

        # 10 KATMANLI KURUMSAL HEDGE FUND MAKRO MATRİSLERİ
        if asset_type == 'SPX':
            weights = {
                'Credit_Risk_Spread': 15.0,    # Saf Temerrüt Riski (+)
                'Credit_Flight_Safety': 15.0,  # Güvenli Limana Kaçış (+)
                'Sector_Rotation': 15.0,       # Büyüme vs Değer Liderliği (+)
                'Market_Breadth': -10.0,       # Genişlik Daralması / Megacap Çarpıklığı (-)
                'Real_Yield_Shock': -10.0,     # Reel Faiz Baskısı (-)
                'Bond_Yield_Pressure': -10.0,  # Nominal Faiz Baskısı (-)
                'DXY_Pressure': -10.0,         # Dolar Baskısı (-)
                'Carry_Trade': 10.0,           # Dolar/Yen Likidite Fonlaması (+)
                'BTC_Liquidity': 10.0,         # 24/7 Global Risk İştahı (+)
                'Copper_Gold': 5.0             # Küresel Büyüme İvmesi (+)
            }
        elif asset_type == 'NQ':
            weights = {
                'Real_Yield_Shock': -20.0,     # Teknoloji İskonto Oranı (#1 Düşman) (-)
                'Sector_Rotation': 20.0,       # Teknoloji Sektör Liderliği (+)
                'Bond_Yield_Pressure': -15.0,  # Nominal Faiz Baskısı (-)
                'Credit_Risk_Spread': 10.0,    # Şirket Borçlanma Sağlığı (+)
                'BTC_Liquidity': 10.0,         # Yüksek Beta Spekülatif Likidite (+)
                'Carry_Trade': 10.0,           # Tech Hedge Fonlama (+)
                'DXY_Pressure': -10.0,         # Çokuluslu Şirket Gelir Baskısı (-)
                'Market_Breadth': -5.0,        # Piyasa Genişliği Baskısı (-)
                'Bond_Vol_Shock': -5.0,        # Tahvil Volatilite Şoku (-)
                'Copper_Gold': 5.0             # Büyüme İvmesi (+)
            }
        elif asset_type == 'XAU':
            weights = {
                'Real_Yield_Shock': -25.0,     # TIPS / Reel Faiz (Altının #1 Anahtarı) (-)
                'DXY_Pressure': -20.0,         # Dolar Değerleme Tabanı (-)
                'Bond_Yield_Pressure': -15.0,  # Fırsat Maliyeti (-)
                'Gold_Oil': 10.0,              # Stagflasyon & Enerji Riski (+)
                'SLV_GLD_Beta': 10.0,          # Kıymetli Madenler Risk İştahı (+)
                'Credit_Flight_Safety': 5.0,   # Kredi Krizinde Güvenli Liman (+)
                'Carry_Trade': 5.0,            # FX Güvenli Liman Uyumu (+)
                'Copper_Gold': -5.0,           # Sanayi vs Korunma Ayrışması (-)
                'Bond_Vol_Shock': 5.0,         # Tahvil Paniğinde Altına Kaçış (+)
                'BTC_Liquidity': -5.0          # Alternatif Varlık Rekabeti (-)
            }
        else: # XAG (GÜMÜŞ)
            weights = {
                'Copper_Gold': 25.0,           # Sanayi Talebi (#1 Gümüş Motoru) (+)
                'XME_GLD_Ratio': 15.0,         # Madencilik & Sanayi Aktivitesi (+)
                'SLV_GLD_Beta': 15.0,          # Gümüş Momentum Liderliği (+)
                'Real_Yield_Shock': -10.0,     # Reel Faiz Baskısı (-)
                'DXY_Pressure': -10.0,         # Dolar Baskısı (-)
                'BTC_Liquidity': 10.0,         # Yüksek Beta Likidite Talebi (+)
                'Sector_Rotation': 5.0,        # Döngüsel Sanayi Sektör Rotasyonu (+)
                'Gold_Oil': 5.0,               # Hammadde Enflasyon Koruması (+)
                'Credit_Risk_Spread': 5.0,     # Ekonomik Büyüme ve Borçlanma (+)
                'Bond_Yield_Pressure': -5.0    # Faiz Maliyeti (-)
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
engine = UltimateMacroEngine()

st.title("🏛️ TIER-1 ULTIMATE MACRO TERMINAL (v11.0)")
st.markdown('<span class="status-badge">⚡ 16-VARLIK / 10-KATMANLI REST MAKRO MOTORU</span>', unsafe_allow_html=True)
st.caption("Reel Faiz, Kredi Spreadleri, Sektör Rotasyonu, Piyasa Genişliği & 24/7 Global Likidite")

try:
    raw_df = engine.fetch_all_data()
    
    if raw_df.empty or len(raw_df) < 3:
        st.warning("Veriler güncelleniyor, lütfen bekleyin...")
    else:
        features_df = engine.calculate_deep_features(raw_df)
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
                    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
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
