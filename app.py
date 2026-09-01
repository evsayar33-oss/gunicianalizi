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
st.set_page_config(page_title="TIER-1 ALL-WEATHER TERMINAL (v30.0)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .regime-box { padding: 10px 16px; border-radius: 6px; font-weight: bold; font-size: 13px; margin-bottom: 15px; border-left: 5px solid; }
    .regime-goldilocks { background-color: #00332c; color: #00E676; border-color: #00E676; }
    .regime-reflation { background-color: #332200; color: #FFD600; border-color: #FFD600; }
    .regime-stagflation { background-color: #33001a; color: #FF4081; border-color: #FF4081; }
    .regime-deflation { background-color: #001a33; color: #40C4FF; border-color: #40C4FF; }
    .div-bull { background-color: #004D40; color: #00E676; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-bear { background-color: #4A148C; color: #FF1744; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #FF1744; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-neutral { background-color: #263238; color: #ECEFF1; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #78909C; font-size: 13px; display: inline-block; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 1 dakikada bir otomatik yenileme
count = st_autorefresh(interval=60000, limit=None, key="macro_300_refresh")

# ==========================================
# 2. OTONOM ALL-WEATHER QUANT MAKRO MOTORU
# ==========================================
class AllWeatherMacroEngine:
    def __init__(self):
        self.symbol_map = {
            'ES=F': 'SPX',          # S&P 500 Vadeli
            'NQ=F': 'NQ',           # Nasdaq 100 Vadeli
            'GC=F': 'XAU',          # Altın Vadeli
            'SI=F': 'XAG',          # Gümüş Vadeli
            'HG=F': 'COPPER',       # Bakır Vadeli (Büyüme Öncüsü)
            'CL=F': 'OIL',          # Ham Petrol (Enflasyon Öncüsü)
            'EURUSD=X': 'EUR',      # Dolar Gücü (Ters DXY)
            'USDJPY=X': 'JPY',      # Carry Trade Fonlaması
            'BTC-USD': 'BTC',       # 24/7 Global Likidite
            'IEF': 'BONDS',         # 7-10Y Hazine Tahvili
            'TLT': 'TLT',           # 20+ Yıl Hazine Tahvili
            'TIP': 'TIP',           # TIPS (Reel Faiz / Enflasyon)
            'HYG': 'HYG',           # Junk Kredi (Risk İştahı)
            'LQD': 'LQD',           # IG Kredi (Kalite)
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
    def fetch_all_native_data(_self):
        series_dict = {}
        def worker(sym, alias):
            s = _self.fetch_single_ticker(sym)
            if not s.empty:
                series_dict[alias] = s

        with ThreadPoolExecutor(max_workers=16) as executor:
            for sym, alias in _self.symbol_map.items():
                executor.submit(worker, sym, alias)

        return series_dict

    def calculate_kinetic_momentum(self, s):
        """15m (%50) + 1H (%30) + 4H (%20) Kinetik İvme (4H Yarılanma Hafızalı)."""
        if s is None or len(s) < 16:
            return 0.0
        
        r15m = (s.iloc[-1] / s.iloc[-2]) - 1.0 if len(s) >= 2 else 0.0
        r1h  = (s.iloc[-1] / s.iloc[-5]) - 1.0 if len(s) >= 5 else 0.0
        r4h  = (s.iloc[-1] / s.iloc[-17]) - 1.0 if len(s) >= 17 else 0.0
        
        kinetic_mom = (0.50 * r15m) + (0.30 * r1h) + (0.20 * r4h)
        
        pct = s.pct_change().dropna()
        vol = pct.ewm(span=16).std().iloc[-1]
        if pd.isna(vol) or vol < 1e-5:
            vol = 0.003
            
        sharpe = kinetic_mom / vol
        return float(np.clip(sharpe, -2.5, 2.5))

    def calculate_ratio_kinetic(self, s1, s2):
        if s1 is None or s2 is None or s1.empty or s2.empty:
            return 0.0
        common_idx = s1.index.intersection(s2.index)
        if len(common_idx) < 16:
            return 0.0
        ratio = s1.loc[common_idx] / (s2.loc[common_idx] + 1e-6)
        return self.calculate_kinetic_momentum(ratio)

    def detect_global_macro_regime(self, factors):
        """
        Ray Dalio 4-Evreli Makro Matrisi:
        Büyüme (Growth) vs Enflasyon (Inflation) dinamik tespit motoru.
        """
        growth_vector = (0.6 * factors['Copper_Gold']) + (0.4 * factors['Breadth'])
        inflation_vector = (0.6 * factors['Real_Yield_Shock']) + (0.4 * factors['Gold_Oil'])

        if growth_vector > 0 and inflation_vector <= 0:
            return {
                'name': "☀️ GOLDILOCKS (Güçlü Büyüme / Düşük Enflasyon)",
                'css': "regime-goldilocks",
                'desc': "Hisse senetleri ve teknoloji için en ideal zemin. Büyüme hisseleri lider, emtialar dengeli.",
                'regime_id': 'GOLDILOCKS'
            }
        elif growth_vector > 0 and inflation_vector > 0:
            return {
                'name': "🚀 REFLASYON (Güçlü Büyüme / Yükselen Enflasyon)",
                'css': "regime-reflation",
                'desc': "Sanayi metalleri, Gümüş ve Bakır patlaması. Değer/Bankacılık hisseleri güçlü, faizler baskılı.",
                'regime_id': 'REFLATION'
            }
        elif growth_vector <= 0 and inflation_vector > 0:
            return {
                'name': "🌋 STAGFLASYON (Düşük Büyüme / Yüksek Enflasyon)",
                'css': "regime-stagflation",
                'desc': "Altın ve Enerjinin mutlak krallığı. Hisse senetleri iskonto baskısı altında, riskli krediler zayıf.",
                'regime_id': 'STAGFLATION'
            }
        else:
            return {
                'name': "❄️ DEFLASYON / KRİZ (Düşük Büyüme / Düşük Enflasyon)",
                'css': "regime-deflation",
                'desc': "Devlet tahvilleri ve nakit güvenli liman. Hisse ve sanayi emtiaları genel satış baskısında.",
                'regime_id': 'DEFLATION'
            }

    def compute_all_asset_scores(self, data):
        scores = {}
        
        # 1. 15-DAKİKALIK TÜM HAM İVMELER
        spx_mom = self.calculate_kinetic_momentum(data.get('SPX'))
        nq_mom = self.calculate_kinetic_momentum(data.get('NQ'))
        xau_mom = self.calculate_kinetic_momentum(data.get('XAU'))
        xag_mom = self.calculate_kinetic_momentum(data.get('XAG'))
        
        btc_mom = self.calculate_kinetic_momentum(data.get('BTC'))
        jpy_mom = self.calculate_kinetic_momentum(data.get('JPY'))
        dxy_mom = -self.calculate_kinetic_momentum(data.get('EUR'))  # EUR Düşüşü = Dolar Gücü
        yield_mom = -self.calculate_kinetic_momentum(data.get('BONDS')) # Tahvil Düşüşü = Faiz Artışı
        
        real_yield_shock = self.calculate_ratio_kinetic(data.get('TIP'), data.get('TLT'))
        credit_risk = self.calculate_ratio_kinetic(data.get('HYG'), data.get('LQD'))
        credit_flight = self.calculate_ratio_kinetic(data.get('HYG'), data.get('TLT'))
        sector_rot = self.calculate_ratio_kinetic(data.get('XLK'), data.get('XLF'))
        breadth = self.calculate_ratio_kinetic(data.get('SPX'), data.get('RSP'))
        
        copper_gold = self.calculate_ratio_kinetic(data.get('COPPER'), data.get('XAU'))
        gold_oil = self.calculate_ratio_kinetic(data.get('XAU'), data.get('OIL'))
        slv_gld = self.calculate_ratio_kinetic(data.get('XAG'), data.get('XAU'))
        xme_gld = self.calculate_ratio_kinetic(data.get('XME'), data.get('XAU'))

        factors_pool = {
            'Copper_Gold': copper_gold, 'Gold_Oil': gold_oil, 'SLV_GLD_Beta': slv_gld,
            'XME_GLD_Ratio': xme_gld, 'Real_Yield_Shock': real_yield_shock, 'Credit_Risk_Spread': credit_risk,
            'Credit_Flight_Safety': credit_flight, 'Sector_Rotation': sector_rot, 'Breadth': breadth,
            'DXY_Pressure': dxy_mom, 'Bond_Yield_Pressure': yield_mom, 'BTC_Liquidity': btc_mom,
            'Carry_Trade': jpy_mom, 'SPX_Mom': spx_mom, 'NQ_Mom': nq_mom, 'XAU_Mom': xau_mom, 'XAG_Mom': xag_mom
        }

        # 2. OTONOM MAKRO REJİM TESPİTİ
        regime_info = self.detect_global_macro_regime(factors_pool)
        regime = regime_info['regime_id']

        # ==========================================
        # 3. REJİME GÖRE OTONOM KALİBRE OLAN AĞIRLIKLAR
        # ==========================================
        def build_result(base_weights, target_mom_val):
            # Şok Dikkat Mekanizması
            multipliers = {}
            for k, w in base_weights.items():
                val = abs(factors_pool.get(k, 0.0))
                boost = 1.5 if '_Mom' in k else 0.8
                multipliers[k] = abs(w) * (1.0 + (min(val, 2.5) ** boost))
            
            total_att = sum(multipliers.values()) + 1e-6
            dyn_weights = {}
            for k, w in base_weights.items():
                sign = 1.0 if w >= 0 else -1.0
                raw_norm = (multipliers[k] / total_att) * 100.0
                
                if '_Mom' in k:
                    raw_norm = max(raw_norm, 40.0) # Fiyat Egemenliği %40
                elif k in ['Carry_Trade', 'BTC_Liquidity']:
                    raw_norm = min(raw_norm, 10.0) # Dış Proxy Tavanı
                    
                dyn_weights[k] = raw_norm * sign

            total_actual = sum(abs(v) for v in dyn_weights.values()) + 1e-6
            for k in dyn_weights:
                dyn_weights[k] = (dyn_weights[k] / total_actual) * 100.0

            breakdown = []
            for k, w in dyn_weights.items():
                val = factors_pool.get(k, 0.0)
                contribution = val * (w / 100.0)
                breakdown.append({
                    'Katman (Öncü Faktör)': k,
                    'Kinetik İvme': round(val, 2),
                    'Dinamik Ağırlık (%)': round(w, 1),
                    'Net Katkı': round(contribution, 3)
                })

            breakdown_df = pd.DataFrame(breakdown).sort_values('Dinamik Ağırlık (%)', ascending=False)
            total_score = sum(factors_pool.get(k, 0.0) * (dyn_weights[k] / 100.0) for k in dyn_weights)
            final_score = np.tanh(total_score / 1.3) * 100

            # Uyumsuzluk Fren Kilidi
            if target_mom_val < -0.3 and final_score > 0:
                final_score = min(final_score, 8.0)
                msg = "🟢 BOĞA UYUMSUZLUĞU (Fiyat Düşüyor ama Makro Zemin Güçlü - Dip Arayışı)"
                css = "div-bull"
            elif target_mom_val > 0.3 and final_score < 0:
                final_score = max(final_score, -8.0)
                msg = "🚨 AYI UYUMSUZLUĞU (Fiyat Yükseliyor ama Makro Zemin Zayıf - Tepe Tuzağı)"
                css = "div-bear"
            elif final_score > 15:
                msg = "🚀 GÜÇLÜ BOĞA TRENDİ (Alıcılar ve Makro Rejim Destekliyor)"
                css = "div-bull"
            elif final_score < -15:
                msg = "🩸 GÜÇLÜ AYI BASKISI (Satıcılar ve Makro Rejim Baskıda)"
                css = "div-bear"
            else:
                msg = "⚪ DENGELİ KONSOLİDASYON (Piyasa Yönsüz / İşlem Açma)"
                css = "div-neutral"

            return {'score': final_score, 'table': breakdown_df, 'msg': msg, 'css': css}

        # REJİME GÖRE OTONOM AĞIRLIK AYARLAMASI:
        # 1. GÜMÜŞ
        xag_base = {
            'XAG_Mom': 40.0, 
            'Copper_Gold': 25.0 if regime == 'REFLATION' else 20.0,
            'XME_GLD_Ratio': 20.0 if regime in ['REFLATION', 'GOLDILOCKS'] else 15.0,
            'SLV_GLD_Beta': 10.0, 'Real_Yield_Shock': 10.0, 'DXY_Pressure': -10.0,
            'BTC_Liquidity': 5.0, 'Gold_Oil': 5.0, 'Credit_Risk_Spread': 5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['XAG'] = build_result(xag_base, xag_mom)

        # 2. ALTIN
        xau_base = {
            'XAU_Mom': 40.0, 
            'Real_Yield_Shock': 30.0 if regime == 'STAGFLATION' else 25.0,
            'DXY_Pressure': -20.0, 'Bond_Yield_Pressure': -15.0,
            'Gold_Oil': 20.0 if regime == 'STAGFLATION' else 10.0,
            'SLV_GLD_Beta': 10.0, 'Credit_Flight_Safety': -5.0, 'Carry_Trade': 5.0,
            'Copper_Gold': -3.0, 'BTC_Liquidity': -2.0
        }
        scores['XAU'] = build_result(xau_base, xau_mom)

        # 3. S&P 500
        spx_base = {
            'SPX_Mom': 45.0,
            'Credit_Flight_Safety': 20.0 if regime == 'GOLDILOCKS' else 15.0,
            'Credit_Risk_Spread': 15.0, 'Sector_Rotation': 10.0,
            'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0, 'Copper_Gold': 5.0,
            'DXY_Pressure': -5.0, 'Real_Yield_Shock': -5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['SPX'] = build_result(spx_base, spx_mom)

        # 4. NASDAQ
        nq_base = {
            'NQ_Mom': 45.0,
            'Sector_Rotation': 20.0 if regime == 'GOLDILOCKS' else 15.0,
            'Credit_Flight_Safety': 10.0, 'Credit_Risk_Spread': 10.0,
            'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0, 'Copper_Gold': 5.0,
            'DXY_Pressure': -5.0, 'Real_Yield_Shock': -5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['NQ'] = build_result(nq_base, nq_mom)

        return scores, regime_info

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = AllWeatherMacroEngine()

st.title("🏛️ TIER-1 ALL-WEATHER TERMINAL (v30.0)")
st.markdown('<span class="status-badge">🌐 AUTONOMOUS 4-QUADRANT MACRO ENGINE</span>', unsafe_allow_html=True)
st.caption("Ray Dalio All-Weather Rejim Matrisi + Kinetik İvme & Otonom Kalibrasyon")

try:
    native_data = engine.fetch_all_native_data()
    
    if not native_data or len(native_data) < 3:
        st.warning("Veriler güncelleniyor, lütfen bekleyin...")
    else:
        results, regime_info = engine.compute_all_asset_scores(native_data)

        # ÜST MAKRO REJİM BANDI (HER ZAMAN CANLI VE AÇIKLAYICI)
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
                
                # Nötr bölge [-15, +15] BEYAZ!
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
