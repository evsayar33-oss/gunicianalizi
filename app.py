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
st.set_page_config(page_title="TIER-1 HARMONIZED TERMINAL (v39.0)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .regime-box { padding: 12px 18px; border-radius: 6px; font-weight: bold; font-size: 13px; margin-bottom: 15px; border-left: 5px solid; }
    .regime-goldilocks { background-color: #00332c; color: #00E676; border-color: #00E676; }
    .regime-reflation { background-color: #332200; color: #FFD600; border-color: #FFD600; }
    .regime-stagflation { background-color: #33001a; color: #FF4081; border-color: #FF4081; }
    .regime-deflation { background-color: #330000; color: #FF1744; border-color: #FF1744; }
    .regime-mixed { background-color: #262000; color: #FFB300; border-color: #FFB300; }
    .div-bull { background-color: #004D40; color: #00E676; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-bear { background-color: #4A148C; color: #FF1744; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #FF1744; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-neutral { background-color: #263238; color: #ECEFF1; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #78909C; font-size: 13px; display: inline-block; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

count = st_autorefresh(interval=60000, limit=None, key="macro_390_refresh")

# ==========================================
# 2. HARMONİZE QUANT MAKRO MOTORU (v39.0)
# ==========================================
class HarmonizedMacroEngine:
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
            'ZN=F': 'BONDS_10Y',    # 10Y Hazine Vadeli
            'ZB=F': 'BONDS_30Y',    # 30Y Uzun Vade Vadeli
            'HYG': 'HYG',           # Junk Kredi
            'LQD': 'LQD',           # IG Kredi
            'XLK': 'XLK',           # Teknoloji
            'XLF': 'XLF',           # Finans
            'RSP': 'RSP',           # Eşit Ağırlıklı S&P 500
            'XME': 'XME'            # Madencilik Endeksi
        }

    def fetch_single_ticker(self, symbol):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=15m"
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

    @st.cache_data(ttl=60, show_spinner=False)
    def fetch_synchronized_grid(_self):
        raw_dict = {}
        def worker(sym, alias):
            s = _self.fetch_single_ticker(sym)
            if not s.empty:
                raw_dict[alias] = s

        with ThreadPoolExecutor(max_workers=16) as executor:
            for sym, alias in _self.symbol_map.items():
                executor.submit(worker, sym, alias)

        df = pd.DataFrame(raw_dict)
        df = df.sort_index()
        df = df.resample('15min').last().ffill().bfill().dropna()
        return df

    def calculate_balanced_momentum(self, s):
        """Kaya gibi sarsılmaz oturaklı momentum formülü (v28 Çekirdeği)."""
        if s is None or len(s) < 32:
            return 0.0
        
        r_daily = (s.iloc[-1] / s.iloc[-32]) - 1.0
        r_4h    = (s.iloc[-1] / s.iloc[-17]) - 1.0
        r_1h    = (s.iloc[-1] / s.iloc[-5])  - 1.0
        
        real_mom = (0.45 * r_daily) + (0.35 * r_4h) + (0.20 * r_1h)
        
        pct = s.pct_change().dropna()
        vol = pct.tail(32).std()
        if pd.isna(vol) or vol < 1e-5:
            vol = 0.0035
            
        sharpe = real_mom / vol
        return float(np.clip(sharpe, -2.5, 2.5))

    def detect_consensus_macro_regime(self, factors):
        spx = factors['SPX_Mom']
        nq = factors['NQ_Mom']
        copper = factors['Copper_Gold']
        sector = factors['Sector_Rotation']
        dxy = factors['DXY_Pressure']
        yields = factors['Bond_Yield_Pressure']
        credit = factors['Credit_Risk_Spread']

        if spx > 0.3 and nq > 0.3 and sector >= -0.5 and copper >= -0.5 and dxy <= 0.5:
            return {'name': "☀️ GENİŞ TABANLI BOĞA RALLİSİ (Goldilocks)", 'css': "regime-goldilocks", 'desc': "Tüm hisse ve riskli varlıklar alıcılarla destekli."}
        elif dxy < -0.5 and (sector < -0.6 or copper < -0.6):
            return {'name': "⚠️ SEÇİCİ DOLAR GEVŞEMESİ & SAVUNMACI ROTASYON", 'css': "regime-mixed", 'desc': "Dolar düşüşü hisseleri tutuyor ancak Teknoloji ve Sanayi zayıf."}
        elif copper > 0.8 and factors['Gold_Oil'] > 0 and spx > 0:
            return {'name': "🚀 REFLASYON (Sanayi & Emtia Liderliği)", 'css': "regime-reflation", 'desc': "Gümüş ve Bakır küresel büyümeyi fiyatlıyor."}
        elif yields > 0.8 and (spx < 0 or nq < 0):
            return {'name': "🌋 STAGFLASYON & LİKİDİTE SIKIŞMASI", 'css': "regime-stagflation", 'desc': "Yükselen faizler değerlemeleri baskılıyor."}
        elif spx < -0.5 and credit < -0.8:
            return {'name': "❄️ DEFLASYONİST ÇÖKÜŞ & KREDİ KRİZİ", 'css': "regime-deflation", 'desc': "Tüm riskli varlıklardan nakde kaçış."}
        else:
            return {'name': "⚪ DENGELİ GEÇİŞ REJİMİ (Konsolidasyon)", 'css': "regime-goldilocks", 'desc': "Piyasa dengeli ve yönsüz konsolide oluyor."}

    def compute_all_asset_scores(self, df):
        scores = {}
        
        # 1. HER VARLIĞIN SAF MOMENTUMU (Yapay karıştırma yok)
        spx_mom = self.calculate_balanced_momentum(df['SPX'])
        nq_mom = self.calculate_balanced_momentum(df['NQ'])
        xau_mom = self.calculate_balanced_momentum(df['XAU'])
        xag_mom = self.calculate_balanced_momentum(df['XAG'])
        
        btc_mom = self.calculate_balanced_momentum(df['BTC'])
        jpy_mom = self.calculate_balanced_momentum(df['JPY'])
        dxy_mom = -self.calculate_balanced_momentum(df['EUR'])
        yield_mom = -self.calculate_balanced_momentum(df['BONDS_10Y'])
        
        copper_gold = self.calculate_balanced_momentum(df['COPPER'] / (df['XAU'] + 1e-6))
        gold_oil = self.calculate_balanced_momentum(df['XAU'] / (df['OIL'] + 1e-6))
        slv_gld = self.calculate_balanced_momentum(df['XAG'] / (df['XAU'] + 1e-6))
        xme_gld = self.calculate_balanced_momentum(df['XME'] / (df['XAU'] + 1e-6))
        
        credit_risk = self.calculate_balanced_momentum(df['HYG'] / (df['LQD'] + 1e-6))
        sector_rot = self.calculate_balanced_momentum(df['XLK'] / (df['XLF'] + 1e-6))
        real_yield_shock = self.calculate_balanced_momentum(df['BONDS_10Y'] / (df['BONDS_30Y'] + 1e-6))

        factors_pool = {
            'SPX_Mom': spx_mom, 'NQ_Mom': nq_mom, 'XAU_Mom': xau_mom, 'XAG_Mom': xag_mom,
            'Copper_Gold': copper_gold, 'Gold_Oil': gold_oil, 'SLV_GLD_Beta': slv_gld,
            'XME_GLD_Ratio': xme_gld, 'Credit_Risk_Spread': credit_risk,
            'Sector_Rotation': sector_rot, 'Real_Yield_Shock': real_yield_shock,
            'DXY_Pressure': dxy_mom, 'Bond_Yield_Pressure': yield_mom, 'BTC_Liquidity': btc_mom, 'Carry_Trade': jpy_mom
        }

        regime_info = self.detect_consensus_macro_regime(factors_pool)

        # 2. OTURAKLI HESAPLAMA MOTORU
        def build_result(base_weights, factors_dict):
            multipliers = {}
            for k, w in base_weights.items():
                val = abs(factors_dict.get(k, 0.0))
                # 0.8 üs ile aşırı zıplamalar tamamen engellendi
                multipliers[k] = abs(w) * (1.0 + (min(val, 2.0) ** 0.8))
            
            total_att = sum(multipliers.values()) + 1e-6
            dyn_weights = {}
            for k, w in base_weights.items():
                sign = 1.0 if w >= 0 else -1.0
                raw_norm = (multipliers[k] / total_att) * 100.0
                dyn_weights[k] = raw_norm * sign

            total_actual = sum(abs(v) for v in dyn_weights.values()) + 1e-6
            for k in dyn_weights:
                dyn_weights[k] = (dyn_weights[k] / total_actual) * 100.0

            breakdown = []
            for k, w in dyn_weights.items():
                val = factors_dict.get(k, 0.0)
                contribution = val * (w / 100.0)
                breakdown.append({
                    'Katman (Öncü Faktör)': k,
                    'Oturaklı İvme': round(val, 2),
                    'Dinamik Ağırlık (%)': round(w, 1),
                    'Net Katkı': round(contribution, 3)
                })

            breakdown_df = pd.DataFrame(breakdown).sort_values('Dinamik Ağırlık (%)', ascending=False)
            total_score = sum(factors_dict.get(k, 0.0) * (dyn_weights[k] / 100.0) for k in dyn_weights)
            
            # 1.5 Böleni ile Sarsılmaz ve Ağırbaşlı Karar
            final_score = np.tanh(total_score / 1.5) * 100

            if final_score > 15:
                msg = "🚀 GÜÇLÜ BOĞA TRENDİ (4H Pozisyon Yönü: ALIM)"
                css = "div-bull"
            elif final_score < -15:
                msg = "🩸 GÜÇLÜ AYI BASKISI (4H Pozisyon Yönü: SATIŞ)"
                css = "div-bear"
            else:
                msg = "⚪ DENGELİ KONSOLİDASYON (Piyasa Yönsüz / Bekle)"
                css = "div-neutral"

            return {'score': final_score, 'table': breakdown_df, 'msg': msg, 'css': css}

        # ==========================================
        # 4 VARLIK İÇİN EŞİTLENMİŞ SARSILMAZ MATRİSLER
        # ==========================================
        # S&P 500 (4 Ana Omurga + Sektör)
        spx_factors = {
            'SPX_Mom': spx_mom, 'Credit_Risk_Spread': credit_risk,
            'Bond_Yield_Pressure': yield_mom, 'DXY_Pressure': dxy_mom, 'Sector_Rotation': sector_rot
        }
        spx_base = {
            'SPX_Mom': 35.0,              # Fiyat Trendi (%35)
            'Credit_Risk_Spread': 25.0,   # Kurumsal Kredi Omurgası (%25)
            'Bond_Yield_Pressure': -20.0, # Faiz Baskısı (%-20)
            'DXY_Pressure': -15.0,        # Dolar Baskısı (%-15)
            'Sector_Rotation': 5.0        # Sektör Rotasyonu (%5)
        }
        scores['SPX'] = build_result(spx_base, spx_factors)

        # NASDAQ (4 Ana Omurga + Sektör)
        nq_factors = {
            'NQ_Mom': nq_mom, 'Bond_Yield_Pressure': yield_mom,
            'Credit_Risk_Spread': credit_risk, 'DXY_Pressure': dxy_mom, 'Sector_Rotation': sector_rot
        }
        nq_base = {
            'NQ_Mom': 35.0,               # Fiyat Trendi (%35)
            'Bond_Yield_Pressure': -25.0, # Teknoloji Faiz İskontosu (%-25)
            'Credit_Risk_Spread': 20.0,   # Kurumsal Kredi Omurgası (%20)
            'DXY_Pressure': -15.0,        # Dolar Baskısı (%-15)
            'Sector_Rotation': 5.0        # Sektör Liderliği (%5)
        }
        scores['NQ'] = build_result(nq_base, nq_factors)

        # ALTIN (DOKUNULMADI - %100 KUSURSUZ)
        xau_factors = {
            'XAU_Mom': xau_mom, 'Real_Yield_Shock': real_yield_shock, 'DXY_Pressure': dxy_mom,
            'Bond_Yield_Pressure': yield_mom, 'Gold_Oil': gold_oil, 'SLV_GLD_Beta': slv_gld
        }
        xau_base = {
            'XAU_Mom': 35.0, 'Real_Yield_Shock': 25.0, 'DXY_Pressure': -20.0,
            'Bond_Yield_Pressure': -15.0, 'Gold_Oil': 10.0, 'SLV_GLD_Beta': 10.0
        }
        scores['XAU'] = build_result(xau_base, xau_factors)

        # GÜMÜŞ (DOKUNULMADI - %100 KUSURSUZ)
        xag_factors = {
            'XAG_Mom': xag_mom, 'Copper_Gold': copper_gold, 'XME_GLD_Ratio': xme_gld,
            'SLV_GLD_Beta': slv_gld, 'Real_Yield_Shock': real_yield_shock, 'DXY_Pressure': dxy_mom
        }
        xag_base = {
            'XAG_Mom': 35.0, 'Copper_Gold': 20.0, 'XME_GLD_Ratio': 20.0,
            'SLV_GLD_Beta': 10.0, 'Real_Yield_Shock': 10.0, 'DXY_Pressure': -10.0
        }
        scores['XAG'] = build_result(xag_base, xag_factors)

        return scores, regime_info

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = HarmonizedMacroEngine()

st.title("🏛️ TIER-1 HARMONIZED TERMINAL (v39.0)")
st.markdown('<span class="status-badge">🛡️ ROCK-SOLID 4-ASSET CORE HARMONY</span>', unsafe_allow_html=True)
st.caption("Altın ve Gümüş'ün Kusursuz Matematiksel Kalıbıyla Birebir Eşitlenmiş S&P 500 ve NASDAQ")

try:
    df_grid = engine.fetch_synchronized_grid()
    
    if df_grid.empty or len(df_grid) < 24:
        st.warning("Veriler senkronize ediliyor, lütfen bekleyin...")
    else:
        results, regime_info = engine.compute_all_asset_scores(df_grid)

        st.markdown(f"""
        <div class="regime-box {regime_info['css']}">
            Mevcut Küresel Makro Rejim: {regime_info['name']}<br>
            <span style="font-size:11px; font-weight:normal; opacity:0.85;">{regime_info['desc']}</span>
        </div>
        """, unsafe_allow_html=True)

        tab_spx, tab_nq, tab_xau, tab_xag = st.tabs(["S&P 500 (ES=F)", "NASDAQ (NQ=F)", "ALTIN (GC=F)", "GÜMÜŞ (SI=F)"])

        def render_view(res, asset_title):
            score = res['score']
            table = res['table']
            div_msg = res['msg']
            div_class = res['css']

            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"### {asset_title} 4H Rotası")
                
                if score > 15:
                    c = "#00E676"  # Yeşil (Boğa)
                elif score < -15:
                    c = "#FF1744"  # Kırmızı (Ayı)
                else:
                    c = "#ECEFF1"  # Beyaz (Nötr)

                st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score:.1f}</h1>", unsafe_allow_html=True)
                st.markdown(f'<div class="{div_class}">{div_msg}</div>', unsafe_allow_html=True)
            with col2:
                if not table.empty:
                    fig = go.Figure(go.Bar(
                        x=table['Dinamik Ağırlık (%)'], y=table['Katman (Öncü Faktör)'], orientation='h',
                        marker_color=np.where(table['Dinamik Ağırlık (%)'] > 0, '#00E676', '#FF1744')
                    ))
                    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
                    st.plotly_chart(fig, use_container_width=True)

            st.dataframe(table, use_container_width=True, hide_index=True)

        with tab_spx:
            render_view(results.get('SPX'), "S&P 500 (ES=F)")

        with tab_nq:
            render_view(results.get('NQ'), "NASDAQ (NQ=F)")

        with tab_xau:
            render_view(results.get('XAU'), "ALTIN (GC=F)")

        with tab_xag:
            render_view(results.get('XAG'), "GÜMÜŞ (SI=F)")

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
