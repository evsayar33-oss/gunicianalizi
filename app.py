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
st.set_page_config(page_title="TIER-1 MASTER TERMINAL (v15.0)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .status-badge { background-color: #1A237E; color: #8C9EFF; padding: 4px 10px; border-radius: 4px; font-weight: bold; border: 1px solid #536DFE; font-size: 12px; }
    .div-bull { background-color: #004D40; color: #00E676; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-bear { background-color: #4A148C; color: #FF1744; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #FF1744; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-neutral { background-color: #263238; color: #ECEFF1; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #78909C; font-size: 13px; display: inline-block; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2 dakikada bir otomatik yenile
count = st_autorefresh(interval=120000, limit=None, key="macro_150_refresh")

# ==========================================
# 2. TAM TEŞEKKÜLLÜ 10-KATMANLI QUANT MOTORU (v15.0)
# ==========================================
class FullScaleMacroEngine:
    def __init__(self):
        self.symbol_map = {
            'ES=F': 'SPX',          # S&P 500 Vadeli
            'NQ=F': 'NQ',           # Nasdaq 100 Vadeli
            'GC=F': 'XAU',          # Altın Vadeli
            'SI=F': 'XAG',          # Gümüş Vadeli
            'HG=F': 'COPPER',       # Bakır Vadeli
            'CL=F': 'OIL',          # Ham Petrol Vadeli
            'EURUSD=X': 'EUR',      # Dolar Gücü (Ters DXY)
            'USDJPY=X': 'JPY',      # Carry Trade
            'BTC-USD': 'BTC',       # 24/7 Global Likidite
            'IEF': 'BONDS',         # 7-10Y Hazine Tahvili
            'TLT': 'TLT',           # 20+ Yıl Hazine Tahvili
            'TIP': 'TIP',           # TIPS (Reel Faiz)
            'HYG': 'HYG',           # Junk Kredi
            'LQD': 'LQD',           # IG Kredi
            'XLK': 'XLK',           # Teknoloji
            'XLF': 'XLF',           # Finans
            'RSP': 'RSP',           # Eşit Ağırlıklı S&P 500
            'XME': 'XME'            # Madencilik Endeksi
        }

    def fetch_single_ticker(self, symbol):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1h"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
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
        def calc_vel(series):
            return series.pct_change(4).fillna(0)

        # 1. KENDİ FİYAT MOMENTUMLARI
        for col in ['SPX', 'NQ', 'XAU', 'XAG']:
            if col in df: features[f'{col}_Mom'] = calc_vel(df[col])

        # 2. REEL FAİZ & KREDİ MAKASLARI
        if 'TIP' in df and 'TLT' in df: features['Real_Yield_Shock'] = calc_vel(df['TIP'] / (df['TLT'] + 1e-6))
        if 'HYG' in df and 'LQD' in df: features['Credit_Risk_Spread'] = calc_vel(df['HYG'] / (df['LQD'] + 1e-6))
        if 'HYG' in df and 'TLT' in df: features['Credit_Flight_Safety'] = calc_vel(df['HYG'] / (df['TLT'] + 1e-6))

        # 3. SEKTÖR, GENİŞLİK VE EMTİA
        if 'XLK' in df and 'XLF' in df: features['Sector_Rotation'] = calc_vel(df['XLK'] / (df['XLF'] + 1e-6))
        if 'SPX' in df and 'RSP' in df: features['Market_Breadth'] = calc_vel(df['SPX'] / (df['RSP'] + 1e-6))
        if 'COPPER' in df and 'XAU' in df: features['Copper_Gold'] = calc_vel(df['COPPER'] / (df['XAU'] + 1e-6))
        if 'XAU' in df and 'OIL' in df:    features['Gold_Oil'] = calc_vel(df['XAU'] / (df['OIL'] + 1e-6))
        if 'XAG' in df and 'XAU' in df:    features['SLV_GLD_Beta'] = calc_vel(df['XAG'] / (df['XAU'] + 1e-6))
        if 'XME' in df and 'XAU' in df:    features['XME_GLD_Ratio'] = calc_vel(df['XME'] / (df['XAU'] + 1e-6))

        # 4. DOLAR, FAİZ & 24/7 LİKİDİTE
        if 'EUR' in df:   features['DXY_Pressure'] = -calc_vel(df['EUR'])
        if 'BONDS' in df: features['Bond_Yield_Pressure'] = -calc_vel(df['BONDS'])
        if 'BTC' in df:   features['BTC_Liquidity'] = calc_vel(df['BTC'])
        if 'JPY' in df:   features['Carry_Trade'] = calc_vel(df['JPY'])

        return features.ffill().bfill()

    def calculate_stable_z_scores(self, df):
        if df.empty:
            return pd.DataFrame()
        mean = df.rolling(24, min_periods=4).mean()
        std = df.rolling(24, min_periods=4).std()
        z_scores = (df - mean) / (std + 1e-6)
        return z_scores.fillna(0)

    def compute_asset_score(self, z_features, df, asset_type):
        empty_df = pd.DataFrame(columns=['Katman (Makro Faktör)', '4-Saatlik İvme (Z-Score)', 'Yapısal Ağırlık (%)', 'Net Katkı'])
        if z_features.empty:
            return 0.0, empty_df, "⚪ DENGELİ KONSOLİDASYON (Piyasa Yönsüz / İşlem Açma)", "div-neutral"

        latest_z = z_features.iloc[-1].clip(-3.0, 3.0)

        # ==========================================
        # 10 KATMANLI EKSİKSİZ KURUMSAL AĞIRLIK MATRİSİ (TOPLAM %100)
        # ==========================================
        if asset_type == 'SPX':
            weights = {
                'SPX_Mom': 20.0,              # Kendi 4H Fiyat İvmesi (+)
                'Credit_Risk_Spread': 15.0,   # Saf Temerrüt Sağlığı (+)
                'Credit_Flight_Safety': 15.0, # Güvenli Limana Kaçış Yok (+)
                'Sector_Rotation': 10.0,      # Büyüme vs Değer (+)
                'BTC_Liquidity': 10.0,        # 24/7 Risk İştahı (+)
                'Carry_Trade': 10.0,          # Dolar/Yen Fonlama Akışı (+)
                'Real_Yield_Shock': -5.0,     # Reel Faiz / Enflasyon Baskısı (-)
                'Bond_Yield_Pressure': -5.0,  # Nominal Faiz Baskısı (-)
                'DXY_Pressure': -5.0,         # Dolar Baskısı (-)
                'Market_Breadth': -5.0        # Megacap Çarpıklığı (-)
            }
            target_col = 'SPX'

        elif asset_type == 'NQ':
            weights = {
                'NQ_Mom': 20.0,               # Kendi 4H Fiyat İvmesi (+)
                'Sector_Rotation': 15.0,      # Teknoloji Liderliği (+)
                'Real_Yield_Shock': -15.0,    # İskonto Oranı / Reel Faiz Baskısı (-)
                'Bond_Yield_Pressure': -15.0, # Nominal Faiz Baskısı (-)
                'Credit_Risk_Spread': 10.0,   # Şirket Borçlanma Sağlığı (+)
                'BTC_Liquidity': 10.0,        # Yüksek Beta Likidite (+)
                'Carry_Trade': 5.0,           # Tech Hedge Fonlama (+)
                'DXY_Pressure': -5.0,         # Çokuluslu Gelir Baskısı (-)
                'Market_Breadth': -3.0,       # Piyasa Genişliği Baskısı (-)
                'Copper_Gold': 2.0            # Büyüme İvmesi (+)
            }
            target_col = 'NQ'

        elif asset_type == 'XAU':
            weights = {
                'XAU_Mom': 20.0,              # Kendi 4H Fiyat İvmesi (+)
                'Real_Yield_Shock': 20.0,     # TIPS Reel Faiz Koruması (+)
                'DXY_Pressure': -15.0,        # Dolar Baskısı (-)
                'Bond_Yield_Pressure': -15.0, # Nominal Faiz Maliyeti (-)
                'Gold_Oil': 10.0,             # Stagflasyon & Enerji Riski (+)
                'SLV_GLD_Beta': 5.0,          # Değerli Maden İştahı (+)
                'Credit_Flight_Safety': -5.0, # Krizde Güvenli Limana Kaçış (-)
                'Carry_Trade': 5.0,           # FX Güvenli Liman Uyumu (+)
                'Copper_Gold': -3.0,          # Sanayi vs Korunma Ayrışması (-)
                'BTC_Liquidity': -2.0         # Alternatif Likidite Rekabeti (-)
            }
            target_col = 'XAU'

        else: # XAG (GÜMÜŞ)
            weights = {
                'XAG_Mom': 20.0,              # Kendi 4H Fiyat İvmesi (+)
                'Copper_Gold': 20.0,          # Sanayi Talebi (#1 Gümüş Motoru) (+)
                'XME_GLD_Ratio': 15.0,        # Madencilik & Malzeme Talebi (+)
                'SLV_GLD_Beta': 10.0,         # Gümüş Liderlik İvmesi (+)
                'Real_Yield_Shock': 10.0,     # Parasal Metal Enflasyon Koruması (+)
                'DXY_Pressure': -10.0,        # Dolar Baskısı (-)
                'Bond_Yield_Pressure': -5.0,  # Faiz Maliyeti (-)
                'BTC_Liquidity': 5.0,         # Yüksek Beta Emtia Talebi (+)
                'Gold_Oil': 3.0,              # Hammadde Enflasyon Koruması (+)
                'Credit_Risk_Spread': 2.0     # Ekonomik Büyüme Desteği (+)
            }
            target_col = 'XAG'

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
        final_score = np.tanh(total_score / 1.0) * 100

        # AYRIŞMA DEDEKTÖRÜ
        price_mom = df[target_col].pct_change(4).iloc[-1] if target_col in df else 0.0
        
        if price_mom > 0.002 and final_score < -15:
            divergence_msg = "🚨 AYI UYUMSUZLUĞU (Fiyat Yükseliyor ama Makro Zemin Satıcılı - Tepe Tuzağı Riski)"
            div_class = "div-bear"
        elif price_mom < -0.002 and final_score > 15:
            divergence_msg = "🟢 BOĞA UYUMSUZLUĞU (Fiyat Düşüyor ama Makro Zemin Güçlü - Dip Alım Fırsatı)"
            div_class = "div-bull"
        elif price_mom > 0.002 and final_score > 15:
            divergence_msg = "🚀 BOĞA TRENDİ (Fiyat ve Makro Tam Uyumlu)"
            div_class = "div-bull"
        elif price_mom < -0.002 and final_score < -15:
            divergence_msg = "🩸 AYI TRENDİ (Düşüş Makro Tarafından Destekleniyor)"
            div_class = "div-bear"
        else:
            divergence_msg = "⚪ DENGELİ KONSOLİDASYON (Piyasa Yönsüz / İşlem Açma)"
            div_class = "div-neutral"

        return final_score, breakdown_df, divergence_msg, div_class

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = FullScaleMacroEngine()

st.title("🏛️ TIER-1 MASTER TERMINAL (v15.0)")
st.markdown('<span class="status-badge">⚡ 10-KATMANLI TAM TEŞEKKÜLLÜ MAKRO MOTORU</span>', unsafe_allow_html=True)
st.caption("Fiyat Trendi (%20) + 9 Makro Çapa (%80) | Toplam %100 Kilitli Ağırlık Matrisi")

try:
    raw_df = engine.fetch_all_data()
    
    if raw_df.empty or len(raw_df) < 3:
        st.warning("Veriler güncelleniyor, lütfen bekleyin...")
    else:
        features_df = engine.calculate_deep_features(raw_df)
        z_scores = engine.calculate_stable_z_scores(features_df)

        tab_spx, tab_nq, tab_xau, tab_xag = st.tabs(["S&P 500 (ES=F)", "NASDAQ (NQ=F)", "ALTIN (GC=F)", "GÜMÜŞ (SI=F)"])

        def render_view(score, table, div_msg, div_class, asset_title):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"### {asset_title} 4H Rotası")
                
                # Nötr bölge [-15, +15] BEYAZ
                if score > 15:
                    c = "#00E676"  # Gerçek Boğa (Yeşil)
                elif score < -15:
                    c = "#FF1744"  # Gerçek Ayı (Kırmızı)
                else:
                    c = "#ECEFF1"  # Nötr / Dengeli (Beyaz)

                st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score:.1f}</h1>", unsafe_allow_html=True)
                st.markdown(f'<div class="{div_class}">{div_msg}</div>', unsafe_allow_html=True)
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
            score_spx, table_spx, div_spx, class_spx = engine.compute_asset_score(z_scores, raw_df, 'SPX')
            render_view(score_spx, table_spx, div_spx, class_spx, "S&P 500 (ES=F)")

        with tab_nq:
            score_nq, table_nq, div_nq, class_nq = engine.compute_asset_score(z_scores, raw_df, 'NQ')
            render_view(score_nq, table_nq, div_nq, class_nq, "NASDAQ (NQ=F)")

        with tab_xau:
            score_xau, table_xau, div_xau, class_xau = engine.compute_asset_score(z_scores, raw_df, 'XAU')
            render_view(score_xau, table_xau, div_xau, class_xau, "ALTIN (GC=F)")

        with tab_xag:
            score_xag, table_xag, div_xag, class_xag = engine.compute_asset_score(z_scores, raw_df, 'XAG')
            render_view(score_xag, table_xag, div_xag, class_xag, "GÜMÜŞ (SI=F)")

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
