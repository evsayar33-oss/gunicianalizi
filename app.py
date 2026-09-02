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
st.set_page_config(page_title="TIER-1 MASTER TERMINAL (v70.1)", layout="wide", initial_sidebar_state="collapsed")
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
    .regime-neutral { background-color: #263238; color: #ECEFF1; border-color: #78909C; }
    .div-bull { background-color: #004D40; color: #00E676; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-bear { background-color: #4A148C; color: #FF1744; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #FF1744; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-neutral { background-color: #263238; color: #ECEFF1; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #78909C; font-size: 13px; display: inline-block; margin-top: 5px; }
    .commentary-card { background-color: #121824; border: 1px solid #2A364F; border-radius: 6px; padding: 12px 16px; margin-top: 10px; font-size: 13px; line-height: 1.6; }
    .commentary-header { font-weight: bold; color: #64B5F6; margin-bottom: 4px; font-size: 13px; display: flex; align-items: center; gap: 6px; }
    .action-badge { background-color: #1E293B; border-left: 3px solid #00E676; padding: 6px 10px; margin-top: 6px; border-radius: 0 4px 4px 0; font-weight: bold; color: #F8FAFC; }
    .action-badge-bear { border-left-color: #FF1744; }
    .action-badge-neutral { border-left-color: #94A3B8; }
    </style>
    """, unsafe_allow_html=True)

# 1 dakikada bir otomatik yenile
count = st_autorefresh(interval=60000, limit=None, key="macro_701_refresh")

# ==========================================
# 2. v70.0 MATEMATİKSEL QUANT MOTORU (DOKUNULMADI)
# ==========================================
class UnifiedMacroEngine:
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

    def calculate_daily_momentum(self, s):
        if s is None or len(s) < 32:
            return 0.0, 0.0
        
        r_daily = (s.iloc[-1] / s.iloc[-32]) - 1.0
        r_4h    = (s.iloc[-1] / s.iloc[-17]) - 1.0
        r_1h    = (s.iloc[-1] / s.iloc[-5])  - 1.0
        
        macro_mom = (0.50 * r_daily) + (0.30 * r_4h) + (0.20 * r_1h)
        
        pct = s.pct_change().dropna()
        vol = pct.tail(32).std()
        if pd.isna(vol) or vol < 1e-5:
            vol = 0.0035
            
        sharpe = macro_mom / vol
        raw_1h = r_1h / vol
        return float(np.clip(sharpe, -2.5, 2.5)), float(np.clip(raw_1h, -2.5, 2.5))

    def compute_all_asset_scores(self, df):
        scores = {}
        
        # 1. GÜNLÜK VE HAFTALIK SARSILMAZ MAKRO ÇAPALAR
        dxy_macro = -self.calculate_daily_momentum(df['EUR'])[0]
        yield_macro = -self.calculate_daily_momentum(df['BONDS_10Y'])[0]
        credit_risk = self.calculate_daily_momentum(df['HYG'] / (df['LQD'] + 1e-6))[0]
        real_yield_shock = self.calculate_daily_momentum(df['BONDS_10Y'] / (df['BONDS_30Y'] + 1e-6))[0]
        copper_gold = self.calculate_daily_momentum(df['COPPER'] / (df['XAU'] + 1e-6))[0]
        gold_oil = self.calculate_daily_momentum(df['XAU'] / (df['OIL'] + 1e-6))[0]
        slv_gld = self.calculate_daily_momentum(df['XAG'] / (df['XAU'] + 1e-6))[0]
        xme_gld = self.calculate_daily_momentum(df['XME'] / (df['XAU'] + 1e-6))[0]
        sector_rot = self.calculate_daily_momentum(df['XLK'] / (df['XLF'] + 1e-6))[0]
        carry_macro = self.calculate_daily_momentum(df['JPY'])[0]
        btc_macro = self.calculate_daily_momentum(df['BTC'])[0]

        # 2. HAM FİYAT İVMELERİ
        raw_spx, spx_1h = self.calculate_daily_momentum(df['SPX'])
        raw_nq, nq_1h   = self.calculate_daily_momentum(df['NQ'])
        raw_xau, xau_1h = self.calculate_daily_momentum(df['XAU'])
        raw_xag, xag_1h = self.calculate_daily_momentum(df['XAG'])

        # 3. VARLIK SINIFI EŞBÜTÜNLEŞMESİ (SENKRONİZASYON)
        equity_market_momentum = (0.50 * raw_spx) + (0.50 * raw_nq)
        spx_mom = (0.80 * equity_market_momentum) + (0.20 * raw_spx)
        nq_mom  = (0.80 * equity_market_momentum) + (0.20 * raw_nq)

        metals_market_momentum = (0.50 * raw_xau) + (0.50 * raw_xag)
        xau_mom = (0.80 * metals_market_momentum) + (0.20 * raw_xau)
        xag_mom = (0.80 * metals_market_momentum) + (0.20 * raw_xag)

        # 4. GÜNLÜK HAKİKİ MAKRO REJİM
        growth_v = (0.4 * credit_risk) + (0.3 * copper_gold) + (0.3 * equity_market_momentum)
        tightness_v = (0.5 * yield_macro) + (0.5 * dxy_macro)

        if growth_v > 0.2 and tightness_v <= 0:
            regime_info = {'name': "☀️ GÜNLÜK BOĞA RALLİSİ (Goldilocks)", 'css': "regime-goldilocks", 'desc': "Dolar ve faizler sakin, hisseler ve büyüme varlıkları güçlü alıcılı."}
        elif growth_v > 0.2 and tightness_v > 0.2:
            regime_info = {'name': "🚀 REFLASYON (Güçlü Büyüme & Emtia)", 'css': "regime-reflation", 'desc': "Gümüş, Bakır ve Sanayi hisseleri küresel büyümeyi fiyatlıyor."}
        elif growth_v <= 0.2 and tightness_v > 0.2:
            regime_info = {'name': "🌋 STAGFLASYON & LİKİDİTE SIKIŞMASI", 'css': "regime-stagflation", 'desc': "Dolar ve Faiz baskısı hisseleri ve emtiaları baskılıyor."}
        elif growth_v < -0.3 and tightness_v <= 0:
            regime_info = {'name': "❄️ DEFLASYON / KRİZ (Toplu Satış Baskısı)", 'css': "regime-deflation", 'desc': "Nakit güvenli liman, riskli varlıklardan kaçış."}
        else:
            regime_info = {'name': "⚪ DENGELİ GÜNLÜK GEÇİŞ REJİMİ (Konsolidasyon)", 'css': "regime-neutral", 'desc': "Piyasa gün içi dengeli ve yönsüz konsolide oluyor."}

        # 5. YORUMLAMA MOTORU (DETAYLI TAKTİKSEL REHBER)
        def generate_commentary(score, micro_1h, asset_name):
            if score > 15:
                if micro_1h < -0.3:
                    structure = f"4 Saatlik ana makro rüzgar güçlü alıcılı. Ancak son 1-2 saatte seans içi kâr satışı / düzeltme (pullback) yaşanıyor. Bu süzülme ana yükseliş trendini bozmamıştır."
                    action = "⚠️ TUZAĞA DÜŞME: Fiyat düşüyor diye aceleyle Short açma. Destek seviyelerinden dönüş ara veya Long pozisyonunu koru."
                    badge_cls = "action-badge"
                else:
                    structure = f"Fiyat momentumu ve küresel makro hidrolikler tam uyumlu şekilde yükselişi destekliyor."
                    action = "🚀 TRENDİ SÜR: 4H Alım yönlü pozisyonlar güvenle taşınabilir. Direnç kırılımlarını takip et."
                    badge_cls = "action-badge"
            elif score < -15:
                if micro_1h > 0.3:
                    structure = f"4 Saatlik ana makro zemin satıcılı. Ancak fiyatta kısa vadeli bir tepki yükselişi (dead-cat bounce) görülüyor. Yükselişin arkasında kurumsal yakıt zayıf."
                    action = "⚠️ DİKKAT: Yükselişe kanıp tepeden Long kovalama. Direnç seviyelerinden satış fırsatı (Sell the Rip) kolla."
                    badge_cls = "action-badge-bear"
                else:
                    structure = f"Fiyat düşüşü ve küresel makro baskı tam uyumlu şekilde satıcıların elinde."
                    action = "🩸 SATIŞ BASKISI DEVAM: 4H Satış yönlü pozisyonlar korunabilir. Destek kırılımlarını izle."
                    badge_cls = "action-badge-bear"
            else:
                structure = "Pozitif ve negatif makro güçler birbirini dengeliyor. Piyasa ana bir kırılım öncesinde dengeli ve yönsüz."
                action = "🛑 NAKİTTE BEKLE: Net bir trend kırılımı (+15 üstü veya -15 altı) gelene kadar yeni pozisyon açma."
                badge_cls = "action-badge-neutral"

            return {'structure': structure, 'action': action, 'badge_cls': badge_cls}

        # 6. HESAPLAMA MOTORU
        def build_unified_result(base_weights, factors_dict, micro_1h, asset_name):
            multipliers = {}
            for k, w in base_weights.items():
                val = abs(factors_dict.get(k, 0.0))
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
                    'Günlük Makro İvme': round(val, 2),
                    'Dinamik Ağırlık (%)': round(w, 1),
                    'Net Katkı': round(contribution, 3)
                })

            breakdown_df = pd.DataFrame(breakdown).sort_values('Dinamik Ağırlık (%)', ascending=False)
            total_score = sum(factors_dict.get(k, 0.0) * (dyn_weights[k] / 100.0) for k in dyn_weights)
            final_score = np.tanh(total_score / 1.4) * 100

            if final_score > 15:
                msg = "🚀 GÜÇLÜ BOĞA TRENDİ (4H Pozisyon Yönü: ALIM)"
                css = "div-bull"
            elif final_score < -15:
                msg = "🩸 GÜÇLÜ AYI BASKISI (4H Pozisyon Yönü: SATIŞ)"
                css = "div-bear"
            else:
                msg = "⚪ DENGELİ KONSOLİDASYON (Piyasa Yönsüz / Bekle)"
                css = "div-neutral"

            commentary = generate_commentary(final_score, micro_1h, asset_name)

            return {'score': final_score, 'table': breakdown_df, 'msg': msg, 'css': css, 'commentary': commentary}

        # S&P 500
        spx_factors = {
            'SPX_Mom': spx_mom, 'Credit_Risk_Spread': credit_risk,
            'Bond_Yield_Pressure': yield_macro, 'DXY_Pressure': dxy_macro,
            'Sector_Rotation': sector_rot, 'Copper_Gold': copper_gold,
            'Carry_Trade': carry_macro, 'BTC_Liquidity': btc_macro,
            'Real_Yield_Shock': real_yield_shock
        }
        spx_base = {
            'SPX_Mom': 40.0, 'Credit_Risk_Spread': 20.0, 'Bond_Yield_Pressure': -15.0,
            'DXY_Pressure': -10.0, 'Sector_Rotation': 5.0, 'Copper_Gold': 5.0,
            'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0, 'Real_Yield_Shock': -5.0
        }
        scores['SPX'] = build_unified_result(spx_base, spx_factors, spx_1h, "S&P 500")

        # NASDAQ
        nq_factors = {
            'NQ_Mom': nq_mom, 'Bond_Yield_Pressure': yield_macro,
            'Credit_Risk_Spread': credit_risk, 'DXY_Pressure': dxy_macro,
            'Sector_Rotation': sector_rot, 'Copper_Gold': copper_gold,
            'Carry_Trade': carry_macro, 'BTC_Liquidity': btc_macro,
            'Real_Yield_Shock': real_yield_shock
        }
        nq_base = {
            'NQ_Mom': 40.0, 'Bond_Yield_Pressure': -20.0, 'Credit_Risk_Spread': 15.0,
            'DXY_Pressure': -10.0, 'Sector_Rotation': 5.0, 'Copper_Gold': 5.0,
            'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0, 'Real_Yield_Shock': -5.0
        }
        scores['NQ'] = build_unified_result(nq_base, nq_factors, nq_1h, "NASDAQ")

        # ALTIN
        xau_factors = {
            'XAU_Mom': xau_mom, 'Real_Yield_Shock': real_yield_shock, 'DXY_Pressure': dxy_macro,
            'Bond_Yield_Pressure': yield_macro, 'Gold_Oil': gold_oil, 'SLV_GLD_Beta': slv_gld,
            'Copper_Gold': copper_gold, 'Carry_Trade': carry_macro, 'BTC_Liquidity': btc_macro
        }
        xau_base = {
            'XAU_Mom': 40.0, 'Real_Yield_Shock': 25.0, 'DXY_Pressure': -20.0,
            'Bond_Yield_Pressure': -15.0, 'Gold_Oil': 10.0, 'SLV_GLD_Beta': 5.0,
            'Copper_Gold': -3.0, 'Carry_Trade': 3.0, 'BTC_Liquidity': -2.0
        }
        scores['XAU'] = build_unified_result(xau_base, xau_factors, xau_1h, "ALTIN")

        # GÜMÜŞ
        xag_factors = {
            'XAG_Mom': xag_mom, 'Real_Yield_Shock': real_yield_shock, 'DXY_Pressure': dxy_macro,
            'Bond_Yield_Pressure': yield_macro, 'Copper_Gold': copper_gold, 'XME_GLD_Ratio': xme_gld,
            'SLV_GLD_Beta': slv_gld, 'Gold_Oil': gold_oil, 'BTC_Liquidity': btc_macro
        }
        xag_base = {
            'XAG_Mom': 40.0, 'Real_Yield_Shock': 20.0, 'DXY_Pressure': -15.0,
            'Bond_Yield_Pressure': -10.0, 'Copper_Gold': 10.0, 'XME_GLD_Ratio': 10.0,
            'SLV_GLD_Beta': 5.0, 'Gold_Oil': 5.0, 'BTC_Liquidity': 5.0
        }
        scores['XAG'] = build_unified_result(xag_base, xag_factors, xag_1h, "GÜMÜŞ")

        return scores, regime_info

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = UnifiedMacroEngine()

st.title("🏛️ TIER-1 UNIFIED TERMINAL (v70.1)")
st.markdown('<span class="status-badge">🛡️ INSTITUTIONAL TACTICAL COMMENTARY ACTIVE</span>', unsafe_allow_html=True)
st.caption("v70.0 Sarsılmaz Makro Çekirdeği + Canlı Taktiksel İşlem Yorum Paneli")

try:
    df_grid = engine.fetch_synchronized_grid()
    
    if df_grid.empty or len(df_grid) < 24:
        st.warning("Veriler senkronize ediliyor, lütfen bekleyin...")
    else:
        results, regime_info = engine.compute_all_asset_scores(df_grid)

        # GÜNLÜK HAKİKİ REJİM BANDI
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
            commentary = res['commentary']

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
                
                # YENİ EKLENEN KURUMSAL YORUM VE AKSİYON KARTI
                st.markdown(f"""
                <div class="commentary-card">
                    <div class="commentary-header">📊 Portföy Masası Teşhisi:</div>
                    <div>{commentary['structure']}</div>
                    <div class="{commentary['badge_cls']}">🎯 Aksiyon: {commentary['action']}</div>
                </div>
                """, unsafe_allow_html=True)

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
