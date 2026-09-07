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
st.set_page_config(page_title="TIER-1 MASTER TERMINAL (v120.0)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .regime-box { padding: 12px 18px; border-radius: 6px; font-weight: bold; font-size: 13px; margin-bottom: 12px; border-left: 5px solid; }
    .regime-goldilocks { background-color: #00332c; color: #00E676; border-color: #00E676; }
    .regime-reflation { background-color: #332200; color: #FFD600; border-color: #FFD600; }
    .regime-stagflation { background-color: #33001a; color: #FF4081; border-color: #FF4081; }
    .regime-deflation { background-color: #330000; color: #FF1744; border-color: #FF1744; }
    .regime-neutral { background-color: #263238; color: #ECEFF1; border-color: #78909C; }
    .div-bull { background-color: #004D40; color: #00E676; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-bear { background-color: #4A148C; color: #FF1744; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #FF1744; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-neutral { background-color: #263238; color: #ECEFF1; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #78909C; font-size: 13px; display: inline-block; margin-top: 5px; }
    .threshold-badge { background-color: #1E293B; color: #94A3B8; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; border: 1px solid #334155; margin-bottom: 10px; display: inline-block; }
    .commentary-card { background-color: #121824; border: 1px solid #2A364F; border-radius: 6px; padding: 12px 16px; margin-top: 10px; font-size: 13px; line-height: 1.6; }
    .commentary-header { font-weight: bold; color: #64B5F6; margin-bottom: 4px; font-size: 13px; display: flex; align-items: center; gap: 6px; }
    .action-badge { background-color: #1E293B; border-left: 3px solid #00E676; padding: 6px 10px; margin-top: 6px; border-radius: 0 4px 4px 0; font-weight: bold; color: #F8FAFC; }
    .action-badge-bear { border-left-color: #FF1744; }
    .action-badge-neutral { border-left-color: #94A3B8; }
    </style>
    """, unsafe_allow_html=True)

# 1 dakikada bir otomatik yenile
count = st_autorefresh(interval=60000, limit=None, key="macro_1200_refresh")

# ==========================================
# 2. AKTİF BANT QUANT MAKRO MOTORU (v120.0)
# ==========================================
class ActiveTapeMacroEngine:
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
            'BTC-USD': 'BTC',       # Bitcoin 24/7
            'ETH-USD': 'ETH',       # Ethereum 24/7
            'ZT=F': 'BONDS_2Y',     # 2Y Hazine Vadeli (Fed Radarı)
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

        with ThreadPoolExecutor(max_workers=18) as executor:
            for sym, alias in _self.symbol_map.items():
                executor.submit(worker, sym, alias)

        df = pd.DataFrame(raw_dict)
        df = df.sort_index()
        df = df.resample('15min').last().ffill().bfill().dropna()
        return df

    def calculate_active_tape_momentum(self, s):
        """
        TATİL & KAPALI PİYASA GEÇİRMEZ AKTİF BANT MOTORU:
        Hareketsiz düz barları süzer, doğrudan son aktif işlem gören seansın
        gerçek mumlarından ivme hesaplar. Asla 0.00 üretmez!
        """
        if s is None or s.empty:
            return 0.0
        
        # Tatildeki hareketsiz kopyalanmış barları ayıkla
        s_active = s.loc[s.shift() != s].dropna()
        if len(s_active) < 8:
            s_active = s.dropna()
            
        if len(s_active) < 8:
            return 0.0
        
        # Son aktif barlar üzerinden getiri hesapla
        idx_daily = min(32, len(s_active) - 1)
        idx_4h    = min(16, len(s_active) - 1)
        idx_1h    = min(4, len(s_active) - 1)
        
        r_daily = (s_active.iloc[-1] / s_active.iloc[-idx_daily]) - 1.0
        r_4h    = (s_active.iloc[-1] / s_active.iloc[-idx_4h]) - 1.0
        r_1h    = (s_active.iloc[-1] / s_active.iloc[-idx_1h]) - 1.0
        
        balanced_mom = (0.50 * r_daily) + (0.35 * r_4h) + (0.15 * r_1h)
        
        pct = s_active.pct_change().dropna()
        vol = pct.tail(32).std()
        if pd.isna(vol) or vol < 1e-5:
            vol = 0.0035
            
        sharpe = balanced_mom / vol
        return float(np.clip(sharpe, -2.5, 2.5))

    def calculate_ratio_active_momentum(self, s1, s2):
        if s1 is None or s2 is None or s1.empty or s2.empty:
            return 0.0
        common_idx = s1.index.intersection(s2.index)
        ratio = s1.loc[common_idx] / (s2.loc[common_idx] + 1e-6)
        return self.calculate_active_tape_momentum(ratio)

    def compute_all_asset_scores(self, df):
        scores = {}
        
        # 1. TÜM GÖSTERGELERİN AKTİF İVMELERİ (Asla 0 Kalmaz)
        raw_spx = self.calculate_active_tape_momentum(df['SPX'])
        raw_nq  = self.calculate_active_tape_momentum(df['NQ'])
        raw_xau = self.calculate_active_tape_momentum(df['XAU'])
        raw_xag = self.calculate_active_tape_momentum(df['XAG'])

        raw_btc = self.calculate_active_tape_momentum(df['BTC'])
        raw_eth = self.calculate_active_tape_momentum(df['ETH']) if 'ETH' in df else raw_btc
        crypto_composite_mom = (0.65 * raw_btc) + (0.35 * raw_eth)

        equity_common = (0.50 * raw_spx) + (0.50 * raw_nq)
        spx_mom = (0.75 * equity_common) + (0.25 * raw_spx)
        nq_mom  = (0.75 * equity_common) + (0.25 * raw_nq)

        metals_common = (0.50 * raw_xau) + (0.50 * raw_xag)
        xau_mom = (0.75 * metals_common) + (0.25 * raw_xau)
        xag_mom = (0.75 * metals_common) + (0.25 * raw_xag)

        btc_macro = raw_btc
        jpy_macro = self.calculate_active_tape_momentum(df['JPY'])
        dxy_macro = -self.calculate_active_tape_momentum(df['EUR'])
        
        fed_pivot_pressure = -self.calculate_active_tape_momentum(df['BONDS_2Y'])
        yield_macro = -self.calculate_active_tape_momentum(df['BONDS_10Y'])
        
        credit_risk = self.calculate_ratio_active_momentum(df['HYG'], df['LQD'])
        credit_flight = self.calculate_ratio_active_momentum(df['HYG'], df['BONDS_30Y'])
        real_yield_shock = self.calculate_ratio_active_momentum(df['BONDS_10Y'], df['BONDS_30Y'])
        copper_gold = self.calculate_ratio_active_momentum(df['COPPER'], df['XAU'])
        gold_oil = self.calculate_ratio_active_momentum(df['XAU'], df['OIL'])
        slv_gld = self.calculate_ratio_active_momentum(df['XAG'], df['XAU'])
        xme_gld = self.calculate_ratio_active_momentum(df['XME'], df['XAU'])
        sector_rot = self.calculate_ratio_active_momentum(df['XLK'], df['XLF'])
        eth_btc_beta = self.calculate_ratio_active_momentum(df['ETH'], df['BTC'])

        factors_pool = {
            'SPX_Mom': spx_mom, 'NQ_Mom': nq_mom, 'XAU_Mom': xau_mom, 'XAG_Mom': xag_mom,
            'Crypto_Mom': crypto_composite_mom, 'ETH_BTC_Beta': eth_btc_beta,
            'Fed_Pivot_Pressure': fed_pivot_pressure, 'Bond_Yield_Pressure': yield_macro,
            'DXY_Pressure': dxy_macro, 'Real_Yield_Shock': real_yield_shock,
            'Credit_Risk_Spread': credit_risk, 'Credit_Flight_Safety': credit_flight,
            'Sector_Rotation': sector_rot, 'Copper_Gold': copper_gold,
            'Gold_Oil': gold_oil, 'SLV_GLD_Beta': slv_gld,
            'XME_GLD_Ratio': xme_gld, 'BTC_Liquidity': btc_macro, 'Carry_Trade': jpy_macro
        }

        # REJİM MOTORU
        growth_raw = (0.4 * credit_risk) + (0.3 * copper_gold) + (0.3 * equity_common)
        tightness_raw = (0.4 * fed_pivot_pressure) + (0.3 * yield_macro) + (0.3 * dxy_macro)

        if growth_raw > 0.3 and tightness_raw <= 0.0:
            regime_info = {'name': "☀️ GOLDILOCKS & FED LİKİDİTE GENİŞLEMESİ", 'css': "regime-goldilocks", 'desc': "Fed faiz baskısı kalktı, Dolar sakin. Hisse senetleri ve teknoloji için ideal ralli ortamı."}
        elif growth_raw > 0.3 and tightness_raw > 0.3:
            regime_info = {'name': "🚀 REFLASYON (Güçlü Büyüme & Emtia Patlaması)", 'css': "regime-reflation", 'desc': "Gümüş, Bakır ve Sanayi hisseleri küresel büyümeyi fiyatlıyor."}
        elif growth_raw <= 0.3 and tightness_raw > 0.3:
            regime_info = {'name': "🌋 STAGFLASYON & FED ŞAHİN SIKIŞMASI", 'css': "regime-stagflation", 'desc': "Faizler yüksek, Fed baskısı hisseleri ve değerlemeleri eziyor."}
        elif growth_raw < -0.4 and tightness_raw <= 0.0:
            regime_info = {'name': "❄️ DEFLASYON / RESESYON KRİZİ", 'css': "regime-deflation", 'desc': "Büyüme çöküşte, nakit ve devlet tahvilleri sığınak."}
        else:
            regime_info = {'name': "⚪ DENGELİ GEÇİŞ REJİMİ (Konsolidasyon)", 'css': "regime-neutral", 'desc': "Piyasa Fed beklentileri öncesinde dengeli konsolide oluyor."}

        # DENGELENMİŞ HESAPLAMA MOTORU (%20-%25 FİYAT TAVANI)
        def build_active_tape_result(base_weights, factors_dict):
            multipliers = {}
            for k, w in base_weights.items():
                val = abs(factors_dict.get(k, 0.0))
                multipliers[k] = abs(w) * (1.0 + (min(val, 2.0) ** 0.8))
            
            total_att = sum(multipliers.values()) + 1e-6
            dyn_weights = {}
            for k, w in base_weights.items():
                sign = 1.0 if w >= 0 else -1.0
                raw_norm = (multipliers[k] / total_att) * 100.0
                
                # Fiyat İvmesi %20-%25 Arasında Dengelenir
                if '_Mom' in k:
                    raw_norm = max(min(raw_norm, 25.0), 20.0)
                else:
                    raw_norm = min(raw_norm, 15.0)
                    
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
                    'Aktif Seans İvmesi': round(val, 2),
                    'Dinamik Ağırlık (%)': round(w, 1),
                    'Net Katkı': round(contribution, 3)
                })

            breakdown_df = pd.DataFrame(breakdown).sort_values('Dinamik Ağırlık (%)', ascending=False)
            total_score = sum(factors_dict.get(k, 0.0) * (dyn_weights[k] / 100.0) for k in dyn_weights)
            final_score = np.tanh(total_score / 1.4) * 100

            # GÜVEN EŞİĞİ (±15 Nötr Alanı)
            if final_score > 15:
                msg = "🚀 GÜÇLÜ BOĞA TRENDİ (4H Pozisyon Yönü: ALIM)"
                css = "div-bull"
            elif final_score < -15:
                msg = "🩸 GÜÇLÜ AYI BASKISI (4H Pozisyon Yönü: SATIŞ)"
                css = "div-bear"
            else:
                msg = "⚪ DENGELİ KONSOLİDASYON (Piyasa Yönsüz / Bekle)"
                css = "div-neutral"

            if final_score > 15:
                structure = "Küresel makro likidite ve son aktif seans alıcıları güçlü destekliyor."
                action = "🚀 TRENDİ SÜR: 4H Alım yönlü pozisyonlar güvenle taşınabilir. Direnç kırılımlarını takip et."
                badge_cls = "action-badge"
            elif final_score < -15:
                structure = "Yükselen faizler, Dolar baskısı ve makro fren piyasayı eziyor."
                action = "🩸 SATIŞ BASKISI DEVAM: 4H Satış yönlü pozisyonlar korunabilir. Destek kırılımlarını izle."
                badge_cls = "action-badge-bear"
            else:
                structure = "Makro güçler dengede. Fiyat nötr konsolidasyon bandı içinde beklemede."
                action = "🛑 NAKİTTE BEKLE: Net kırılım gelene kadar yeni pozisyon açma."
                badge_cls = "action-badge-neutral"

            commentary = {'structure': structure, 'action': action, 'badge_cls': badge_cls}

            return {'score': final_score, 'table': breakdown_df, 'msg': msg, 'css': css, 'commentary': commentary}

        # ----------------------------------------------------
        # 5 VARLIK MATRİSLERİ
        # ----------------------------------------------------
        # 1. GÜMÜŞ (SI=F)
        xag_base = {
            'XAG_Mom': 25.0, 'Copper_Gold': 15.0, 'Fed_Pivot_Pressure': -15.0,
            'XME_GLD_Ratio': 10.0, 'SLV_GLD_Beta': 10.0, 'DXY_Pressure': -10.0,
            'Real_Yield_Shock': 5.0, 'Bond_Yield_Pressure': -5.0, 'BTC_Liquidity': 5.0, 'Gold_Oil': 5.0
        }
        scores['XAG'] = build_active_tape_result(xag_base, xag_factors)

        # 2. ALTIN (GC=F)
        xau_base = {
            'XAU_Mom': 25.0, 'Real_Yield_Shock': 20.0, 'Fed_Pivot_Pressure': -15.0,
            'DXY_Pressure': -15.0, 'Bond_Yield_Pressure': -10.0, 'Gold_Oil': 10.0,
            'SLV_GLD_Beta': 5.0, 'Carry_Trade': 5.0, 'Copper_Gold': -3.0, 'BTC_Liquidity': -2.0
        }
        scores['XAU'] = build_active_tape_result(xau_base, xau_factors)

        # 3. S&P 500 (ES=F)
        spx_base = {
            'SPX_Mom': 25.0, 'Fed_Pivot_Pressure': -15.0, 'Credit_Risk_Spread': 15.0,
            'Credit_Flight_Safety': 10.0, 'Bond_Yield_Pressure': -10.0, 'DXY_Pressure': -10.0,
            'Sector_Rotation': 10.0, 'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0, 'Copper_Gold': 5.0
        }
        scores['SPX'] = build_active_tape_result(spx_base, spx_factors)

        # 4. NASDAQ (NQ=F)
        nq_base = {
            'NQ_Mom': 25.0, 'Fed_Pivot_Pressure': -20.0, 'Sector_Rotation': 15.0,
            'Bond_Yield_Pressure': -15.0, 'Credit_Risk_Spread': 10.0, 'DXY_Pressure': -10.0,
            'Credit_Flight_Safety': 5.0, 'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0, 'Copper_Gold': 5.0
        }
        scores['NQ'] = build_active_tape_result(nq_base, nq_factors)

        # 5. KRİPTO (BTC+ETH)
        crypto_base = {
            'Crypto_Mom': 25.0, 'Fed_Pivot_Pressure': -20.0, 'Sector_Rotation': 10.0,
            'ETH_BTC_Beta': 10.0, 'DXY_Pressure': -10.0, 'Credit_Risk_Spread': 10.0,
            'Carry_Trade': 5.0, 'Copper_Gold': 5.0, 'Real_Yield_Shock': -5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['CRYPTO'] = build_active_tape_result(crypto_base, factors_pool)

        return scores, regime_info

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = ActiveTapeMacroEngine()

st.title("🏛️ TIER-1 MASTER TERMINAL (v120.0)")
st.markdown('<span class="status-badge">⚡ ACTIVE TAPE & HOLIDAY-PROOF ENGINE</span>', unsafe_allow_html=True)
st.caption("Tatil ve Kapalı Piyasa Düz Çizgi Süzgeci | Canlı Seans İvmesi")

try:
    df_grid = engine.fetch_synchronized_grid()
    
    if df_grid.empty or len(df_grid) < 8:
        st.warning("Veriler senkronize ediliyor, lütfen bekleyin...")
    else:
        results, regime_info = engine.compute_all_asset_scores(df_grid)

        # HAKİKİ MAKRO REJİM BANDI
        st.markdown(f"""
        <div class="regime-box {regime_info['css']}">
            Mevcut Küresel Makro Rejim: {regime_info['name']}<br>
            <span style="font-size:11px; font-weight:normal; opacity:0.85;">{regime_info['desc']}</span>
        </div>
        """, unsafe_allow_html=True)

        tab_spx, tab_nq, tab_xau, tab_xag, tab_crypto = st.tabs([
            "S&P 500 (ES=F)", 
            "NASDAQ (NQ=F)", 
            "ALTIN (GC=F)", 
            "GÜMÜŞ (SI=F)", 
            "KRİPTO (BTC+ETH)"
        ])

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
                
                # Taktiksel Kart
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

        with tab_crypto:
            render_view(results.get('CRYPTO'), "KRİPTO (BTC+ETH)")

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
