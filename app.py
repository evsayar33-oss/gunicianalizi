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
st.set_page_config(page_title="TIER-1 MASTER TERMINAL (v32.0)", layout="wide", initial_sidebar_state="collapsed")
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
    .div-exhaust { background-color: #E65100; color: #FFA726; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #FFA726; font-size: 13px; display: inline-block; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 1 dakikada bir otomatik yenile
count = st_autorefresh(interval=60000, limit=None, key="macro_320_refresh")

# ==========================================
# 2. HAKİKİ KREDİ AĞIRLIKLI QUANT MOTORU (v32.0)
# ==========================================
class CreditDrivenMacroEngine:
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

    def calculate_v28_locked_momentum(self, s):
        if s is None or len(s) < 16:
            return 0.0, 0.0
        
        r1h  = (s.iloc[-1] / s.iloc[-5]) - 1.0 if len(s) >= 5 else 0.0
        r4h  = (s.iloc[-1] / s.iloc[-17]) - 1.0 if len(s) >= 17 else 0.0
        
        locked_trend = (0.70 * r4h) + (0.30 * r1h)
        
        pct = s.pct_change().dropna()
        vol = pct.ewm(span=32).std().iloc[-1]
        if pd.isna(vol) or vol < 1e-5:
            vol = 0.003
            
        sharpe_macro = locked_trend / vol
        
        r15m = (s.iloc[-1] / s.iloc[-2]) - 1.0 if len(s) >= 2 else 0.0
        micro_exhaustion = r15m / vol
        
        return float(np.clip(sharpe_macro, -2.5, 2.5)), float(np.clip(micro_exhaustion, -2.5, 2.5))

    def calculate_ratio_locked(self, s1, s2):
        if s1 is None or s2 is None or s1.empty or s2.empty:
            return 0.0
        common_idx = s1.index.intersection(s2.index)
        if len(common_idx) < 16:
            return 0.0
        ratio = s1.loc[common_idx] / (s2.loc[common_idx] + 1e-6)
        macro_val, _ = self.calculate_v28_locked_momentum(ratio)
        return macro_val

    def detect_true_macro_regime(self, factors):
        """
        KURUMSAL REJİM TESPİT MOTORU:
        Büyüme Vektörü: %70 Kredi Piyasası + %15 Sektör + %15 Bakır
        Enflasyon/Sıkılık Vektörü: %50 Faiz Baskısı + %30 TIPS Reel Faiz + %20 Petrol
        """
        # Büyüme (Kredi çöküyorsa büyüme pozitif çıkamaz!)
        growth_vector = (0.35 * factors['Credit_Risk_Spread']) + \
                        (0.35 * factors['Credit_Flight_Safety']) + \
                        (0.15 * factors['Sector_Rotation']) + \
                        (0.15 * factors['Copper_Gold'])

        # Enflasyon / Likidite Sıkılığı
        tightness_vector = (0.40 * factors['Bond_Yield_Pressure']) + \
                           (0.35 * factors['Real_Yield_Shock']) + \
                           (0.25 * factors['Gold_Oil'])

        if growth_vector > 0 and tightness_vector <= 0:
            return {
                'name': "☀️ GOLDILOCKS (Güçlü Büyüme / Düşük Enflasyon)",
                'css': "regime-goldilocks",
                'desc': "Kredi piyasası sağlıklı, faiz baskısı yok. Hisse senetleri ve teknoloji için en ideal zemin."
            }
        elif growth_vector > 0 and tightness_vector > 0:
            return {
                'name': "🚀 REFLASYON (Güçlü Büyüme / Yükselen Enflasyon)",
                'css': "regime-reflation",
                'desc': "Kredi güçlü, talep yüksek. Sanayi metalleri, Gümüş ve Değer/Bankacılık hisseleri lider."
            }
        elif growth_vector <= 0 and tightness_vector > 0:
            return {
                'name': "🌋 STAGFLASYON & LİKİDİTE SIKIŞMASI (Kredi Stresi / Yüksek Faiz)",
                'css': "regime-stagflation",
                'desc': "Kredi piyasası ve büyüme baskı altında, faizler yüksek. Altın ve Nakit güvenli liman, hisseler kırılgan."
            }
        else:
            return {
                'name': "❄️ DEFLASYON / RESESYON (Düşük Büyüme / Düşen Faiz)",
                'css': "regime-deflation",
                'desc': "Büyüme çöküşte, faizler geriliyor. Uzun vadeli devlet tahvilleri en güçlü sığınak."
            }

    def compute_all_asset_scores(self, data):
        scores = {}
        
        # 1. v28 KİLİTLİ MAKRO İVMELERİ
        spx_macro, spx_micro = self.calculate_v28_locked_momentum(data.get('SPX'))
        nq_macro, nq_micro = self.calculate_v28_locked_momentum(data.get('NQ'))
        xau_macro, xau_micro = self.calculate_v28_locked_momentum(data.get('XAU'))
        xag_macro, xag_micro = self.calculate_v28_locked_momentum(data.get('XAG'))
        
        btc_macro, _ = self.calculate_v28_locked_momentum(data.get('BTC'))
        jpy_macro, _ = self.calculate_v28_locked_momentum(data.get('JPY'))
        dxy_macro = -self.calculate_v28_locked_momentum(data.get('EUR'))[0]
        yield_macro = -self.calculate_v28_locked_momentum(data.get('BONDS'))[0]
        
        real_yield_shock = self.calculate_ratio_locked(data.get('TIP'), data.get('TLT'))
        credit_risk = self.calculate_ratio_locked(data.get('HYG'), data.get('LQD'))
        credit_flight = self.calculate_ratio_locked(data.get('HYG'), data.get('TLT'))
        sector_rot = self.calculate_ratio_locked(data.get('XLK'), data.get('XLF'))
        breadth = self.calculate_ratio_locked(data.get('SPX'), data.get('RSP'))
        
        copper_gold = self.calculate_ratio_locked(data.get('COPPER'), data.get('XAU'))
        gold_oil = self.calculate_ratio_locked(data.get('XAU'), data.get('OIL'))
        slv_gld = self.calculate_ratio_locked(data.get('XAG'), data.get('XAU'))
        xme_gld = self.calculate_ratio_locked(data.get('XME'), data.get('XAU'))

        factors_pool = {
            'Credit_Risk_Spread': credit_risk, 'Credit_Flight_Safety': credit_flight,
            'Sector_Rotation': sector_rot, 'Copper_Gold': copper_gold,
            'Bond_Yield_Pressure': yield_macro, 'Real_Yield_Shock': real_yield_shock,
            'Gold_Oil': gold_oil
        }

        # HAKİKİ KREDİ AĞIRLIKLI REJİM TESPİTİ
        regime_info = self.detect_true_macro_regime(factors_pool)

        # ==========================================
        # 2. HESAPLAMA MOTORU
        # ==========================================
        def build_result(base_weights, factors_dict, target_macro, target_micro):
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
                    'Makro İvme': round(val, 2),
                    'Dinamik Ağırlık (%)': round(w, 1),
                    'Net Katkı': round(contribution, 3)
                })

            breakdown_df = pd.DataFrame(breakdown).sort_values('Dinamik Ağırlık (%)', ascending=False)
            total_score = sum(factors_dict.get(k, 0.0) * (dyn_weights[k] / 100.0) for k in dyn_weights)
            
            final_score = np.tanh(total_score / 1.0) * 100

            if final_score < -20 and target_micro > 1.2:
                msg = "💎 DİRENÇ TESTİ (Aşırı Alım Tepesi - Sahte Yükseliş/Satış Fırsatı)"
                css = "div-exhaust"
            elif final_score > 20 and target_micro < -1.2:
                msg = "💎 DESTEK TESTİ (Aşırı Satım Dibi - Sahte Düşüş/Alım Fırsatı)"
                css = "div-exhaust"
            elif final_score > 20:
                msg = "🚀 GÜÇLÜ BOĞA TRENDİ (4H Pozisyon Yönü: ALIM)"
                css = "div-bull"
            elif final_score < -20:
                msg = "🩸 GÜÇLÜ AYI BASKISI (4H Pozisyon Yönü: SATIŞ)"
                css = "div-bear"
            else:
                msg = "⚪ DENGELİ KONSOLİDASYON (Piyasa Yönsüz / Bekle)"
                css = "div-neutral"

            return {'score': final_score, 'table': breakdown_df, 'msg': msg, 'css': css}

        # S&P 500
        spx_factors = {
            'SPX_Mom': spx_macro, 'Credit_Flight_Safety': credit_flight, 'Credit_Risk_Spread': credit_risk,
            'Sector_Rotation': sector_rot, 'Carry_Trade': jpy_macro, 'BTC_Liquidity': btc_macro,
            'Copper_Gold': copper_gold, 'DXY_Pressure': dxy_macro, 'Real_Yield_Shock': real_yield_shock, 'Bond_Yield_Pressure': yield_macro
        }
        spx_base = {
            'SPX_Mom': 40.0, 'Credit_Flight_Safety': 15.0, 'Credit_Risk_Spread': 10.0,
            'Sector_Rotation': 10.0, 'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0,
            'Copper_Gold': 5.0, 'DXY_Pressure': -5.0, 'Real_Yield_Shock': -5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['SPX'] = build_result(spx_base, spx_factors, spx_macro, spx_micro)

        # NASDAQ
        nq_factors = {
            'NQ_Mom': nq_macro, 'Sector_Rotation': sector_rot, 'Credit_Flight_Safety': credit_flight,
            'Credit_Risk_Spread': credit_risk, 'Carry_Trade': jpy_macro, 'BTC_Liquidity': btc_macro,
            'Copper_Gold': copper_gold, 'DXY_Pressure': dxy_macro, 'Real_Yield_Shock': real_yield_shock, 'Bond_Yield_Pressure': yield_macro
        }
        nq_base = {
            'NQ_Mom': 40.0, 'Sector_Rotation': 15.0, 'Credit_Flight_Safety': 10.0,
            'Credit_Risk_Spread': 10.0, 'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0,
            'Copper_Gold': 5.0, 'DXY_Pressure': -5.0, 'Real_Yield_Shock': -5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['NQ'] = build_result(nq_base, nq_factors, nq_macro, nq_micro)

        # ALTIN
        xau_factors = {
            'XAU_Mom': xau_macro, 'Real_Yield_Shock': real_yield_shock, 'DXY_Pressure': dxy_macro,
            'Bond_Yield_Pressure': yield_macro, 'Gold_Oil': gold_oil, 'SLV_GLD_Beta': slv_gld,
            'Credit_Flight_Safety': credit_flight, 'Carry_Trade': jpy_macro, 'Copper_Gold': copper_gold, 'BTC_Liquidity': btc_macro
        }
        xau_base = {
            'XAU_Mom': 35.0, 'Real_Yield_Shock': 25.0, 'DXY_Pressure': -20.0,
            'Bond_Yield_Pressure': -15.0, 'Gold_Oil': 15.0, 'SLV_GLD_Beta': 10.0,
            'Credit_Flight_Safety': -5.0, 'Carry_Trade': 5.0, 'Copper_Gold': -3.0, 'BTC_Liquidity': -2.0
        }
        scores['XAU'] = build_result(xau_base, xau_factors, xau_macro, xau_micro)

        # GÜMÜŞ
        xag_factors = {
            'XAG_Mom': xag_macro, 'Copper_Gold': copper_gold, 'XME_GLD_Ratio': xme_gld,
            'SLV_GLD_Beta': slv_gld, 'Real_Yield_Shock': real_yield_shock, 'DXY_Pressure': dxy_macro,
            'BTC_Liquidity': btc_macro, 'Gold_Oil': gold_oil, 'Credit_Risk_Spread': credit_risk, 'Bond_Yield_Pressure': yield_macro
        }
        xag_base = {
            'XAG_Mom': 35.0, 'Copper_Gold': 20.0, 'XME_GLD_Ratio': 20.0,
            'SLV_GLD_Beta': 10.0, 'Real_Yield_Shock': 10.0, 'DXY_Pressure': -10.0,
            'BTC_Liquidity': 5.0, 'Gold_Oil': 5.0, 'Credit_Risk_Spread': 5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['XAG'] = build_result(xag_base, xag_factors, xag_macro, xag_micro)

        return scores, regime_info

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = CreditDrivenMacroEngine()

st.title("🏛️ TIER-1 MASTER TERMINAL (v32.0)")
st.markdown('<span class="status-badge">🛡️ CREDIT-DRIVEN MACRO REGIME ENGINE</span>', unsafe_allow_html=True)
st.caption("Kredi Piyasası Ağırlıklı Hakiki Büyüme/Enflasyon Rejim Dedektörü")

try:
    native_data = engine.fetch_all_native_data()
    
    if not native_data or len(native_data) < 3:
        st.warning("Veriler güncelleniyor, lütfen bekleyin...")
    else:
        results, regime_info = engine.compute_all_asset_scores(native_data)

        # HAKİKİ MAKRO REJİM BANDI
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
                st.markdown(f"### {asset_title} 4H Ana Rotası")
                
                if score > 20:
                    c = "#00E676"  # Yeşil (Boğa)
                elif score < -20:
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
