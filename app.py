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
st.set_page_config(page_title="TIER-1 COHESIVE TERMINAL (v34.0)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .regime-box { padding: 10px 16px; border-radius: 6px; font-weight: bold; font-size: 13px; margin-bottom: 15px; border-left: 5px solid; }
    .regime-goldilocks { background-color: #00332c; color: #00E676; border-color: #00E676; }
    .regime-reflation { background-color: #332200; color: #FFD600; border-color: #FFD600; }
    .regime-stagflation { background-color: #33001a; color: #FF4081; border-color: #FF4081; }
    .regime-deflation { background-color: #330000; color: #FF1744; border-color: #FF1744; }
    .div-bull { background-color: #004D40; color: #00E676; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-bear { background-color: #4A148C; color: #FF1744; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #FF1744; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-neutral { background-color: #263238; color: #ECEFF1; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #78909C; font-size: 13px; display: inline-block; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 1 dakikada bir otomatik yenile
count = st_autorefresh(interval=60000, limit=None, key="macro_340_refresh")

# ==========================================
# 2. BÜTÜNLEŞİK QUANT MAKRO MOTORU (v34.0)
# ==========================================
class CohesiveMacroEngine:
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

    def calculate_absolute_real_momentum(self, s):
        """
        GÜNLÜK GERÇEKLİK ÇAPASI:
        Günün Başından Beri Net Değişim (%50) + 4 Saatlik Trend (%30) + 1 Saatlik İvme (%20).
        Bugün %-2 düşmüş bir varlığın pozitif çıkması imkansızdır!
        """
        if s is None or len(s) < 32:
            return 0.0
        
        # Günlük seans değişimi (~32 bar / 8 saat)
        r_daily = (s.iloc[-1] / s.iloc[-32]) - 1.0
        r_4h    = (s.iloc[-1] / s.iloc[-17]) - 1.0
        r_1h    = (s.iloc[-1] / s.iloc[-5])  - 1.0
        
        # Günün genel gerçeğine kilitli momentum
        real_mom = (0.50 * r_daily) + (0.30 * r_4h) + (0.20 * r_1h)
        
        pct = s.pct_change().dropna()
        vol = pct.tail(32).std()
        if pd.isna(vol) or vol < 1e-5:
            vol = 0.003
            
        sharpe = real_mom / vol
        return float(np.clip(sharpe, -2.5, 2.5))

    def compute_all_asset_scores(self, df):
        scores = {}
        
        # 1. HİZALANMIŞ MAKRO RASYOLAR
        copper_gold = self.calculate_absolute_real_momentum(df['COPPER'] / (df['XAU'] + 1e-6))
        gold_oil = self.calculate_absolute_real_momentum(df['XAU'] / (df['OIL'] + 1e-6))
        slv_gld = self.calculate_absolute_real_momentum(df['XAG'] / (df['XAU'] + 1e-6))
        xme_gld = self.calculate_absolute_real_momentum(df['XME'] / (df['XAU'] + 1e-6))
        
        real_yield_shock = self.calculate_absolute_real_momentum(df['TIP'] / (df['TLT'] + 1e-6))
        credit_risk = self.calculate_absolute_real_momentum(df['HYG'] / (df['LQD'] + 1e-6))
        credit_flight = self.calculate_absolute_real_momentum(df['HYG'] / (df['TLT'] + 1e-6))
        sector_rot = self.calculate_absolute_real_momentum(df['XLK'] / (df['XLF'] + 1e-6))
        breadth = self.calculate_absolute_real_momentum(df['SPX'] / (df['RSP'] + 1e-6))
        
        spx_mom = self.calculate_absolute_real_momentum(df['SPX'])
        nq_mom = self.calculate_absolute_real_momentum(df['NQ'])
        xau_mom = self.calculate_absolute_real_momentum(df['XAU'])
        xag_mom = self.calculate_absolute_real_momentum(df['XAG'])
        
        btc_mom = self.calculate_absolute_real_momentum(df['BTC'])
        jpy_mom = self.calculate_absolute_real_momentum(df['JPY'])
        dxy_mom = -self.calculate_absolute_real_momentum(df['EUR'])
        yield_mom = -self.calculate_absolute_real_momentum(df['BONDS'])

        # 2. HAKİKİ MAKRO REJİM TESPİTİ
        growth_v = (0.4 * credit_risk) + (0.3 * credit_flight) + (0.3 * copper_gold)
        tightness_v = (0.5 * yield_mom) + (0.3 * dxy_mom) + (0.2 * real_yield_shock)

        is_systemic_crash = False
        if growth_v < -0.2 and tightness_v > 0.2:
            is_systemic_crash = True
            regime_info = {
                'name': "⚡ KÜRESEL LİKİDİTE ÇÖKÜŞÜ / TOPLU SATIŞ (Systemic Liquidity Shock)",
                'css': "regime-deflation",
                'desc': "Tüm varlıklardan eşzamanlı nakde kaçış. Faiz ve Dolar baskısı tüm piyasayı aşağı çekiyor."
            }
        elif growth_v > 0 and tightness_v <= 0:
            regime_info = {
                'name': "☀️ GOLDILOCKS (Güçlü Büyüme / Düşük Enflasyon)",
                'css': "regime-goldilocks",
                'desc': "Kredi piyasası sağlıklı, hisseler güçlü."
            }
        elif growth_v > 0 and tightness_v > 0:
            regime_info = {
                'name': "🚀 REFLASYON (Güçlü Büyüme / Yükselen Enflasyon)",
                'css': "regime-reflation",
                'desc': "Emtialar ve değer hisseleri lider."
            }
        else:
            regime_info = {
                'name': "🌋 STAGFLASYON & SIKIŞMA (Kredi Stresi / Faiz Baskısı)",
                'css': "regime-stagflation",
                'desc': "Kredi piyasası ve büyüme baskı altında, faizler yüksek."
            }

        # 3. TOP-DOWN HESAPLAMA MOTORU
        def build_result(base_weights, factors_dict, target_mom):
            multipliers = {}
            for k, w in base_weights.items():
                val = abs(factors_dict.get(k, 0.0))
                multipliers[k] = abs(w) * (1.0 + (min(val, 2.0) ** 0.8))
            
            total_att = sum(multipliers.values()) + 1e-6
            dyn_weights = {}
            for k, w in base_weights.items():
                sign = 1.0 if w >= 0 else -1.0
                raw_norm = (multipliers[k] / total_att) * 100.0
                if k in ['Carry_Trade', 'BTC_Liquidity', 'DXY_Pressure']:
                    raw_norm = min(raw_norm, 12.0)
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
                    'Günlük Gerçek İvme': round(val, 2),
                    'Dinamik Ağırlık (%)': round(w, 1),
                    'Net Katkı': round(contribution, 3)
                })

            breakdown_df = pd.DataFrame(breakdown).sort_values('Dinamik Ağırlık (%)', ascending=False)
            total_score = sum(factors_dict.get(k, 0.0) * (dyn_weights[k] / 100.0) for k in dyn_weights)
            
            # Sistemik çöküşte makro baskıyı doğrudan yansıt
            if is_systemic_crash and target_mom < 0:
                total_score = min(total_score, -0.6) # Zorunlu Ayı Baskısı

            final_score = np.tanh(total_score / 1.0) * 100

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

        # S&P 500
        spx_factors = {
            'SPX_Mom': spx_mom, 'Credit_Flight_Safety': credit_flight, 'Credit_Risk_Spread': credit_risk,
            'Sector_Rotation': sector_rot, 'Carry_Trade': jpy_mom, 'BTC_Liquidity': btc_mom,
            'Copper_Gold': copper_gold, 'DXY_Pressure': dxy_mom, 'Real_Yield_Shock': real_yield_shock, 'Bond_Yield_Pressure': yield_mom
        }
        spx_base = {
            'SPX_Mom': 45.0, 'Credit_Flight_Safety': 15.0, 'Credit_Risk_Spread': 10.0,
            'Sector_Rotation': 10.0, 'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0,
            'Copper_Gold': 5.0, 'DXY_Pressure': -5.0, 'Real_Yield_Shock': -5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['SPX'] = build_result(spx_base, spx_factors, spx_mom)

        # NASDAQ
        nq_factors = {
            'NQ_Mom': nq_mom, 'Sector_Rotation': sector_rot, 'Credit_Flight_Safety': credit_flight,
            'Credit_Risk_Spread': credit_risk, 'Carry_Trade': jpy_mom, 'BTC_Liquidity': btc_mom,
            'Copper_Gold': copper_gold, 'DXY_Pressure': dxy_mom, 'Real_Yield_Shock': real_yield_shock, 'Bond_Yield_Pressure': yield_mom
        }
        nq_base = {
            'NQ_Mom': 45.0, 'Sector_Rotation': 15.0, 'Credit_Flight_Safety': 10.0,
            'Credit_Risk_Spread': 10.0, 'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0,
            'Copper_Gold': 5.0, 'DXY_Pressure': -5.0, 'Real_Yield_Shock': -5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['NQ'] = build_result(nq_base, nq_factors, nq_mom)

        # ALTIN
        xau_factors = {
            'XAU_Mom': xau_mom, 'Real_Yield_Shock': real_yield_shock, 'DXY_Pressure': dxy_mom,
            'Bond_Yield_Pressure': yield_mom, 'Gold_Oil': gold_oil, 'SLV_GLD_Beta': slv_gld,
            'Credit_Flight_Safety': credit_flight, 'Carry_Trade': jpy_mom, 'Copper_Gold': copper_gold, 'BTC_Liquidity': btc_mom
        }
        xau_base = {
            'XAU_Mom': 40.0, 'Real_Yield_Shock': 20.0, 'DXY_Pressure': -20.0,
            'Bond_Yield_Pressure': -15.0, 'Gold_Oil': 10.0, 'SLV_GLD_Beta': 10.0,
            'Credit_Flight_Safety': -5.0, 'Carry_Trade': 5.0, 'Copper_Gold': -3.0, 'BTC_Liquidity': -2.0
        }
        scores['XAU'] = build_result(xau_base, xau_factors, xau_mom)

        # GÜMÜŞ
        xag_factors = {
            'XAG_Mom': xag_mom, 'Copper_Gold': copper_gold, 'XME_GLD_Ratio': xme_gld,
            'SLV_GLD_Beta': slv_gld, 'Real_Yield_Shock': real_yield_shock, 'DXY_Pressure': dxy_mom,
            'BTC_Liquidity': btc_mom, 'Gold_Oil': gold_oil, 'Credit_Risk_Spread': credit_risk, 'Bond_Yield_Pressure': yield_mom
        }
        xag_base = {
            'XAG_Mom': 40.0, 'Copper_Gold': 20.0, 'XME_GLD_Ratio': 20.0,
            'SLV_GLD_Beta': 10.0, 'Real_Yield_Shock': 10.0, 'DXY_Pressure': -10.0,
            'BTC_Liquidity': 5.0, 'Gold_Oil': 5.0, 'Credit_Risk_Spread': 5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['XAG'] = build_result(xag_base, xag_factors, xag_mom)

        return scores, regime_info

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = CohesiveMacroEngine()

st.title("🏛️ TIER-1 COHESIVE TERMINAL (v34.0)")
st.markdown('<span class="status-badge">⚡ TOP-DOWN MACRO GOVERNANCE & DAILY REALITY</span>', unsafe_allow_html=True)
st.caption("Rejim ve Varlıkların %100 Senkronize Çalıştığı Bütünleşik Model")

try:
    df_grid = engine.fetch_synchronized_grid()
    
    if df_grid.empty or len(df_grid) < 24:
        st.warning("Veriler 15m ızgarasında senkronize ediliyor, lütfen bekleyin...")
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
