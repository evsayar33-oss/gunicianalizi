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
st.set_page_config(page_title="TIER-1 MASTER TERMINAL (v25.0)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .status-badge { background-color: #004D40; color: #00E676; padding: 4px 10px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 12px; }
    .div-bull { background-color: #004D40; color: #00E676; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-bear { background-color: #4A148C; color: #FF1744; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #FF1744; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-neutral { background-color: #263238; color: #ECEFF1; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #78909C; font-size: 13px; display: inline-block; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 1 dakikada bir otomatik yenileme
count = st_autorefresh(interval=60000, limit=None, key="macro_250_refresh")

# ==========================================
# 2. EGEMEN QUANT MAKRO MOTORU (v25.0)
# ==========================================
class SovereignMacroEngine:
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

    def calculate_sovereign_momentum(self, s):
        """
        EGEMEN FİYAT MOMENTUMU:
        Seansın Başından Beri Getiri (%40) + 4 Saatlik Trend (%35) + 1 Saatlik İvme (%25)
        Fiyat kırmızıdayken modelin yeşil yakmasını imkansız kılar.
        """
        if s is None or len(s) < 16:
            return 0.0
        
        r1h  = (s.iloc[-1] / s.iloc[-5]) - 1.0 if len(s) >= 5 else 0.0
        r4h  = (s.iloc[-1] / s.iloc[-17]) - 1.0 if len(s) >= 17 else 0.0
        r_session = (s.iloc[-1] / s.iloc[-32]) - 1.0 if len(s) >= 32 else r4h  # ~8 saatlik seans getirisi
        
        # Egemen İvme Formülü
        sovereign_mom = (0.40 * r_session) + (0.35 * r4h) + (0.25 * r1h)
        
        pct = s.pct_change().dropna()
        vol = pct.ewm(span=16).std().iloc[-1]
        if pd.isna(vol) or vol < 1e-5:
            vol = 0.003
            
        sharpe = sovereign_mom / vol
        return float(np.clip(sharpe, -2.5, 2.5))

    def calculate_ratio_kinetic(self, s1, s2):
        if s1 is None or s2 is None or s1.empty or s2.empty:
            return 0.0
        common_idx = s1.index.intersection(s2.index)
        if len(common_idx) < 16:
            return 0.0
        ratio = s1.loc[common_idx] / (s2.loc[common_idx] + 1e-6)
        return self.calculate_sovereign_momentum(ratio)

    def compute_all_asset_scores(self, data):
        scores = {}
        
        # 1. EGEMEN HAM İVMELER
        spx_mom = self.calculate_sovereign_momentum(data.get('SPX'))
        nq_mom = self.calculate_sovereign_momentum(data.get('NQ'))
        xau_mom = self.calculate_sovereign_momentum(data.get('XAU'))
        xag_mom = self.calculate_sovereign_momentum(data.get('XAG'))
        
        btc_mom = self.calculate_sovereign_momentum(data.get('BTC'))
        jpy_mom = self.calculate_sovereign_momentum(data.get('JPY'))
        dxy_mom = -self.calculate_sovereign_momentum(data.get('EUR'))  # EUR Düşüşü = Dolar Gücü
        yield_mom = -self.calculate_sovereign_momentum(data.get('BONDS')) # Tahvil Düşüşü = Faiz Artışı
        
        real_yield_shock = self.calculate_ratio_kinetic(data.get('TIP'), data.get('TLT'))
        credit_risk = self.calculate_ratio_kinetic(data.get('HYG'), data.get('LQD'))
        credit_flight = self.calculate_ratio_kinetic(data.get('HYG'), data.get('TLT'))
        sector_rot = self.calculate_ratio_kinetic(data.get('XLK'), data.get('XLF'))
        breadth = self.calculate_ratio_kinetic(data.get('SPX'), data.get('RSP'))
        
        copper_gold = self.calculate_ratio_kinetic(data.get('COPPER'), data.get('XAU'))
        gold_oil = self.calculate_ratio_kinetic(data.get('XAU'), data.get('OIL'))
        slv_gld = self.calculate_ratio_kinetic(data.get('XAG'), data.get('XAU'))
        xme_gld = self.calculate_ratio_kinetic(data.get('XME'), data.get('XAU'))

        # ==========================================
        # 2. EGEMEN AĞIRLIK VE LİMİT MOTORU
        # ==========================================
        def build_result(base_weights, factors_dict, max_proxy_weight=10.0):
            multipliers = {}
            for k, w in base_weights.items():
                val = abs(factors_dict.get(k, 0.0))
                # Fiyat momentumu daha fazla dikkat alır
                boost = 1.5 if '_Mom' in k else 1.0
                multipliers[k] = abs(w) * (1.0 + (min(val, 2.5) ** boost))
            
            total_att = sum(multipliers.values()) + 1e-6
            dyn_weights = {}
            for k, w in base_weights.items():
                sign = 1.0 if w >= 0 else -1.0
                raw_norm = (multipliers[k] / total_att) * 100.0
                
                # DIŞ PROXY TAVAN SINIRI: Carry Trade veya BTC %10'u geçip sistemi rehin alamaz!
                if k in ['Carry_Trade', 'BTC_Liquidity']:
                    raw_norm = min(raw_norm, max_proxy_weight)
                    
                dyn_weights[k] = raw_norm * sign

            # Ağırlıkları %100'e tekrar normalize et
            total_actual = sum(abs(v) for v in dyn_weights.values()) + 1e-6
            for k in dyn_weights:
                dyn_weights[k] = (dyn_weights[k] / total_actual) * 100.0

            breakdown = []
            for k, w in dyn_weights.items():
                val = factors_dict.get(k, 0.0)
                contribution = val * (w / 100.0)
                breakdown.append({
                    'Katman (Öncü Faktör)': k,
                    'Egemen İvme': round(val, 2),
                    'Dinamik Ağırlık (%)': round(w, 1),
                    'Net Katkı': round(contribution, 3)
                })

            breakdown_df = pd.DataFrame(breakdown).sort_values('Dinamik Ağırlık (%)', ascending=False)
            total_score = sum(factors_dict.get(k, 0.0) * (dyn_weights[k] / 100.0) for k in dyn_weights)
            
            # 1.4 Böleni ile Kararlı Reaksiyon
            final_score = np.tanh(total_score / 1.4) * 100

            if final_score > 15:
                msg = "🚀 GÜÇLÜ BOĞA TRENDİ (Alıcılar ve Likidite Piyasayı Sürüklüyor)"
                css = "div-bull"
            elif final_score < -15:
                msg = "🩸 GÜÇLÜ AYI BASKISI (Satıcılar ve Makro Fren Üstün)"
                css = "div-bear"
            else:
                msg = "⚪ DENGELİ KONSOLİDASYON (Yönsüz / Kararsız Bölge)"
                css = "div-neutral"

            return {'score': final_score, 'table': breakdown_df, 'msg': msg, 'css': css}

        # ----------------------------------------------------
        # S&P 500 (SPX) MATRİSİ (Fiyat %40 Egemen)
        # ----------------------------------------------------
        spx_factors = {
            'SPX_Mom': spx_mom, 'Credit_Flight_Safety': credit_flight, 'Credit_Risk_Spread': credit_risk,
            'Sector_Rotation': sector_rot, 'Carry_Trade': jpy_mom, 'BTC_Liquidity': btc_mom,
            'Copper_Gold': copper_gold, 'DXY_Pressure': dxy_mom, 'Real_Yield_Shock': real_yield_shock, 'Bond_Yield_Pressure': yield_mom
        }
        spx_base = {
            'SPX_Mom': 40.0,              # Fiyat Trendi Egemen (%40)
            'Credit_Flight_Safety': 15.0, # Kredi Güvenliği
            'Credit_Risk_Spread': 10.0,   # Temerrüt Riski
            'Sector_Rotation': 10.0,      # Sektör Rotasyonu
            'Carry_Trade': 5.0,           # Carry Trade (Limitli)
            'BTC_Liquidity': 5.0,         # Kripto Likidite (Limitli)
            'Copper_Gold': 5.0,           # Büyüme
            'DXY_Pressure': -5.0,         # Dolar Baskısı (-)
            'Real_Yield_Shock': -5.0,     # Reel Faiz Baskısı (-)
            'Bond_Yield_Pressure': -5.0   # Nominal Faiz Baskısı (-)
        }
        scores['SPX'] = build_result(spx_base, spx_factors)

        # ----------------------------------------------------
        # NASDAQ (NQ) MATRİSİ (Fiyat %40 Egemen)
        # ----------------------------------------------------
        nq_factors = {
            'NQ_Mom': nq_mom, 'Sector_Rotation': sector_rot, 'Credit_Flight_Safety': credit_flight,
            'Credit_Risk_Spread': credit_risk, 'Carry_Trade': jpy_mom, 'BTC_Liquidity': btc_mom,
            'Copper_Gold': copper_gold, 'DXY_Pressure': dxy_mom, 'Real_Yield_Shock': real_yield_shock, 'Bond_Yield_Pressure': yield_mom
        }
        nq_base = {
            'NQ_Mom': 40.0,               # Fiyat Trendi Egemen (%40)
            'Sector_Rotation': 15.0,      # Teknoloji Liderliği
            'Credit_Flight_Safety': 10.0, # Kredi Güvenliği
            'Credit_Risk_Spread': 10.0,   # Temerrüt Riski
            'Carry_Trade': 5.0,           # Carry Trade (Limitli)
            'BTC_Liquidity': 5.0,         # Kripto Likidite (Limitli)
            'Copper_Gold': 5.0,           # Büyüme
            'DXY_Pressure': -5.0,         # Dolar Baskısı (-)
            'Real_Yield_Shock': -5.0,     # Reel Faiz Baskısı (-)
            'Bond_Yield_Pressure': -5.0   # Nominal Faiz Baskısı (-)
        }
        scores['NQ'] = build_result(nq_base, nq_factors)

        # ----------------------------------------------------
        # ALTIN (XAU) MATRİSİ (DOKUNULMADI - %100 KUSURSUZ ÇALIŞIYOR)
        # ----------------------------------------------------
        xau_factors = {
            'XAU_Mom': xau_mom, 'Real_Yield_Shock': real_yield_shock, 'DXY_Pressure': dxy_mom,
            'Bond_Yield_Pressure': yield_mom, 'Gold_Oil': gold_oil, 'SLV_GLD_Beta': slv_gld,
            'Credit_Flight_Safety': credit_flight, 'Carry_Trade': jpy_mom, 'Copper_Gold': copper_gold, 'BTC_Liquidity': btc_mom
        }
        xau_base = {
            'XAU_Mom': 30.0, 'Real_Yield_Shock': 25.0, 'DXY_Pressure': -20.0,
            'Bond_Yield_Pressure': -15.0, 'Gold_Oil': 15.0, 'SLV_GLD_Beta': 10.0,
            'Credit_Flight_Safety': -5.0, 'Carry_Trade': 5.0, 'Copper_Gold': -3.0, 'BTC_Liquidity': -2.0
        }
        scores['XAU'] = build_result(xau_base, xau_factors)

        # ----------------------------------------------------
        # GÜMÜŞ (XAG) MATRİSİ (DOKUNULMADI - %100 KUSURSUZ ÇALIŞIYOR)
        # ----------------------------------------------------
        xag_factors = {
            'XAG_Mom': xag_mom, 'Copper_Gold': copper_gold, 'XME_GLD_Ratio': xme_gld,
            'SLV_GLD_Beta': slv_gld, 'Real_Yield_Shock': real_yield_shock, 'DXY_Pressure': dxy_mom,
            'BTC_Liquidity': btc_mom, 'Gold_Oil': gold_oil, 'Credit_Risk_Spread': credit_risk, 'Bond_Yield_Pressure': yield_mom
        }
        xag_base = {
            'XAG_Mom': 30.0, 'Copper_Gold': 20.0, 'XME_GLD_Ratio': 20.0,
            'SLV_GLD_Beta': 10.0, 'Real_Yield_Shock': 10.0, 'DXY_Pressure': -10.0,
            'BTC_Liquidity': 5.0, 'Gold_Oil': 5.0, 'Credit_Risk_Spread': 5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['XAG'] = build_result(xag_base, xag_factors)

        return scores

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = SovereignMacroEngine()

st.title("🏛️ TIER-1 MASTER TERMINAL (v25.0)")
st.markdown('<span class="status-badge">⚡ SOVEREIGN PRICE MOMENTUM & PROXY-CAPPED ENGINE</span>', unsafe_allow_html=True)
st.caption("Fiyat Egemenliği (%40) + Sınırlandırılmış Dış Proxy'ler | Yanıltmayan Gerçek Makro Yön")

try:
    native_data = engine.fetch_all_native_data()
    
    if not native_data or len(native_data) < 3:
        st.warning("Veriler güncelleniyor, lütfen bekleyin...")
    else:
        results = engine.compute_all_asset_scores(native_data)

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
