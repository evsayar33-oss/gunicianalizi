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
st.set_page_config(page_title="TIER-1 MASTER TERMINAL (v80.0)", layout="wide", initial_sidebar_state="collapsed")
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
count = st_autorefresh(interval=60000, limit=None, key="macro_800_refresh")

# ==========================================
# 2. TAM OTONOM ADAPTİF QUANT MOTORU (v80.0)
# ==========================================
class SingularityMacroEngine:
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

    def calculate_daily_momentum_series(self, s):
        """Her bar için pürüzsüz çoklu-zaman dilimli ivme serisi üretir."""
        if s is None or len(s) < 32:
            return pd.Series(0.0, index=s.index if s is not None else [0])
        
        r_daily = s.pct_change(32).fillna(0)
        r_4h    = s.pct_change(16).fillna(0)
        r_1h    = s.pct_change(4).fillna(0)
        
        macro_mom = (0.50 * r_daily) + (0.30 * r_4h) + (0.20 * r_1h)
        vol = s.pct_change().rolling(32, min_periods=4).std().fillna(0.0035)
        sharpe = macro_mom / (vol + 1e-5)
        return sharpe.clip(-2.5, 2.5)

    def calculate_ratio_momentum_series(self, s1, s2):
        if s1 is None or s2 is None or s1.empty or s2.empty:
            return pd.Series(0.0, index=s1.index if s1 is not None else [0])
        common_idx = s1.index.intersection(s2.index)
        ratio = s1.loc[common_idx] / (s2.loc[common_idx] + 1e-6)
        return self.calculate_daily_momentum_series(ratio)

    def compute_all_asset_scores(self, df):
        scores = {}
        
        # 1. TÜM GÖSTERGELERİN CANLI ZAMAN SERİLERİ
        raw_spx = self.calculate_daily_momentum_series(df['SPX'])
        raw_nq  = self.calculate_daily_momentum_series(df['NQ'])
        raw_xau = self.calculate_daily_momentum_series(df['XAU'])
        raw_xag = self.calculate_daily_momentum_series(df['XAG'])

        # Varlık Sınıfı Eşbütünleşmesi (Kardeş Varlıklar)
        equity_common = (0.50 * raw_spx) + (0.50 * raw_nq)
        spx_mom = (0.80 * equity_common) + (0.20 * raw_spx)
        nq_mom  = (0.80 * equity_common) + (0.20 * raw_nq)

        metals_common = (0.50 * raw_xau) + (0.50 * raw_xag)
        xau_mom = (0.80 * metals_common) + (0.20 * raw_xau)
        xag_mom = (0.80 * metals_common) + (0.20 * raw_xag)

        btc_macro = self.calculate_daily_momentum_series(df['BTC'])
        jpy_macro = self.calculate_daily_momentum_series(df['JPY'])
        dxy_macro = -self.calculate_daily_momentum_series(df['EUR'])
        yield_macro = -self.calculate_daily_momentum_series(df['BONDS_10Y'])
        
        credit_risk = self.calculate_ratio_momentum_series(df['HYG'], df['LQD'])
        real_yield_shock = self.calculate_ratio_momentum_series(df['BONDS_10Y'], df['BONDS_30Y'])
        copper_gold = self.calculate_ratio_momentum_series(df['COPPER'], df['XAU'])
        gold_oil = self.calculate_ratio_momentum_series(df['XAU'], df['OIL'])
        slv_gld = self.calculate_ratio_momentum_series(df['XAG'], df['XAU'])
        xme_gld = self.calculate_ratio_momentum_series(df['XME'], df['XAU'])
        sector_rot = self.calculate_ratio_momentum_series(df['XLK'], df['XLF'])

        factors_series_pool = {
            'SPX_Mom': spx_mom, 'NQ_Mom': nq_mom, 'XAU_Mom': xau_mom, 'XAG_Mom': xag_mom,
            'Copper_Gold': copper_gold, 'Gold_Oil': gold_oil, 'SLV_GLD_Beta': slv_gld,
            'XME_GLD_Ratio': xme_gld, 'Credit_Risk_Spread': credit_risk,
            'Sector_Rotation': sector_rot, 'Real_Yield_Shock': real_yield_shock,
            'DXY_Pressure': dxy_macro, 'Bond_Yield_Pressure': yield_macro,
            'BTC_Liquidity': btc_macro, 'Carry_Trade': jpy_macro
        }

        # ==========================================================
        # 2. ÖZ-NORMALİZASYONLU ADAPTİF MAKRO REJİM MOTORU (Zero-Constant)
        # ==========================================================
        growth_raw = (0.4 * credit_risk) + (0.3 * copper_gold) + (0.3 * equity_common)
        tightness_raw = (0.5 * yield_macro) + (0.5 * dxy_macro)

        # Büyüme ve Sıkılık Vektörlerinin Kendi Standart Sapması
        g_vol = growth_raw.tail(64).std() if len(growth_raw) >= 64 else 0.5
        t_vol = tightness_raw.tail(64).std() if len(tightness_raw) >= 64 else 0.5
        
        z_growth = growth_raw.iloc[-1] / (g_vol + 1e-5)
        z_tightness = tightness_raw.iloc[-1] / (t_vol + 1e-5)

        if z_growth > 0.4 and z_tightness <= 0.0:
            regime_info = {'name': "☀️ GÜNLÜK BOĞA RALLİSİ (Goldilocks)", 'css': "regime-goldilocks", 'desc': "Dolar ve faizler sakin, hisseler ve büyüme varlıkları güçlü alıcılı."}
        elif z_growth > 0.4 and z_tightness > 0.4:
            regime_info = {'name': "🚀 REFLASYON (Güçlü Büyüme & Emtia)", 'css': "regime-reflation", 'desc': "Gümüş, Bakır ve Sanayi hisseleri küresel büyümeyi fiyatlıyor."}
        elif z_growth <= 0.4 and z_tightness > 0.4:
            regime_info = {'name': "🌋 STAGFLASYON & LİKİDİTE SIKIŞMASI", 'css': "regime-stagflation", 'desc': "Dolar ve Faiz baskısı hisseleri ve emtiaları baskılıyor."}
        elif z_growth < -0.5 and z_tightness <= 0.0:
            regime_info = {'name': "❄️ DEFLASYON / KRİZ (Toplu Satış Baskısı)", 'css': "regime-deflation", 'desc': "Nakit güvenli liman, riskli varlıklardan kaçış."}
        else:
            regime_info = {'name': "⚪ DENGELİ GÜNLÜK GEÇİŞ REJİMİ (Konsolidasyon)", 'css': "regime-neutral", 'desc': "Piyasa gün içi dengeli ve yönsüz konsolide oluyor."}

        # ==========================================================
        # 3. DİNAMİK YÜZDELİK DİLİM (ROLLING QUANTILE) EŞİK MOTORU
        # ==========================================================
        def build_singularity_result(base_weights, target_mom_series, asset_name):
            # Tarihsel tüm bar skorlarını hesapla (Dağılımı ve Eşiği bulmak için)
            bar_scores = []
            lookback_bars = min(len(df), 96) # Son 2-4 gün
            
            for i in range(-lookback_bars, 0):
                t_score = 0.0
                for k, w in base_weights.items():
                    val = factors_series_pool[k].iloc[i]
                    t_score += val * (w / 100.0)
                bar_scores.append(np.tanh(t_score / 1.4) * 100.0)

            scores_series = pd.Series(bar_scores)
            
            # ADAPTİF EŞİK: Son günlerin %65'lik Yüzdelik Dilimi (Volatiliteye göre nefes alır)
            adaptive_threshold = float(np.clip(scores_series.abs().quantile(0.65), 10.0, 22.0))
            
            # Son Bar Hesaplaması
            multipliers = {}
            for k, w in base_weights.items():
                val = abs(factors_series_pool[k].iloc[-1])
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
                val = factors_series_pool[k].iloc[-1]
                contribution = val * (w / 100.0)
                breakdown.append({
                    'Katman (Öncü Faktör)': k,
                    'Günlük Makro İvme': round(val, 2),
                    'Dinamik Ağırlık (%)': round(w, 1),
                    'Net Katkı': round(contribution, 3)
                })

            breakdown_df = pd.DataFrame(breakdown).sort_values('Dinamik Ağırlık (%)', ascending=False)
            total_score = sum(factors_series_pool[k].iloc[-1] * (dyn_weights[k] / 100.0) for k in dyn_weights)
            final_score = np.tanh(total_score / 1.4) * 100

            # ADAPTİF EŞİĞE GÖRE KARAR VE RENK
            micro_1h = target_mom_series.iloc[-1]
            if final_score > adaptive_threshold:
                msg = f"🚀 GÜÇLÜ BOĞA TRENDİ (Puan: +{adaptive_threshold:.1f} Eşiğini Aştı)"
                css = "div-bull"
            elif final_score < -adaptive_threshold:
                msg = f"🩸 GÜÇLÜ AYI BASKISI (Puan: -{adaptive_threshold:.1f} Eşiğini Aştı)"
                css = "div-bear"
            else:
                msg = f"⚪ DENGELİ KONSOLİDASYON (±{adaptive_threshold:.1f} Nötr Bandı İçinde)"
                css = "div-neutral"

            # Taktiksel Rehberlik
            if final_score > adaptive_threshold:
                structure = "Küresel makro hidrolikler ve fiyat ivmesi tam uyumlu şekilde alıcıları destekliyor."
                action = "🚀 TRENDİ SÜR: 4H Alım yönlü pozisyonlar güvenle taşınabilir. Direnç kırılımlarını takip et."
                badge_cls = "action-badge"
            elif final_score < -adaptive_threshold:
                structure = "Küresel makro baskı ve fiyat düşüşü satıcıların kontrolünde."
                action = "🩸 SATIŞ BASKISI DEVAM: 4H Satış yönlü pozisyonlar korunabilir. Destek kırılımlarını izle."
                badge_cls = "action-badge-bear"
            else:
                structure = f"Makro güçler dengede. Fiyat adaptif nötr bandı (±{adaptive_threshold:.1f}) içinde beklemede."
                action = "🛑 NAKİTTE BEKLE: Adaptif kırılım gelene kadar yeni pozisyon açma."
                badge_cls = "action-badge-neutral"

            commentary = {'structure': structure, 'action': action, 'badge_cls': badge_cls}

            return {
                'score': final_score,
                'table': breakdown_df,
                'msg': msg,
                'css': css,
                'threshold': adaptive_threshold,
                'commentary': commentary
            }

        # ----------------------------------------------------
        # 4 VARLIK MATRİSLERİ
        # ----------------------------------------------------
        spx_base = {
            'SPX_Mom': 40.0, 'Credit_Risk_Spread': 20.0, 'Bond_Yield_Pressure': -15.0,
            'DXY_Pressure': -10.0, 'Sector_Rotation': 5.0, 'Copper_Gold': 5.0,
            'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0, 'Real_Yield_Shock': -5.0
        }
        scores['SPX'] = build_singularity_result(spx_base, spx_mom, "S&P 500")

        nq_base = {
            'NQ_Mom': 40.0, 'Bond_Yield_Pressure': -20.0, 'Credit_Risk_Spread': 15.0,
            'DXY_Pressure': -10.0, 'Sector_Rotation': 5.0, 'Copper_Gold': 5.0,
            'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0, 'Real_Yield_Shock': -5.0
        }
        scores['NQ'] = build_singularity_result(nq_base, nq_mom, "NASDAQ")

        xau_base = {
            'XAU_Mom': 40.0, 'Real_Yield_Shock': 25.0, 'DXY_Pressure': -20.0,
            'Bond_Yield_Pressure': -15.0, 'Gold_Oil': 10.0, 'SLV_GLD_Beta': 5.0,
            'Copper_Gold': -3.0, 'Carry_Trade': 3.0, 'BTC_Liquidity': -2.0
        }
        scores['XAU'] = build_singularity_result(xau_base, xau_mom, "ALTIN")

        xag_base = {
            'XAG_Mom': 40.0, 'Real_Yield_Shock': 20.0, 'DXY_Pressure': -15.0,
            'Bond_Yield_Pressure': -10.0, 'Copper_Gold': 10.0, 'XME_GLD_Ratio': 10.0,
            'SLV_GLD_Beta': 5.0, 'Gold_Oil': 5.0, 'BTC_Liquidity': 5.0
        }
        scores['XAG'] = build_singularity_result(xag_base, xag_mom, "GÜMÜŞ")

        return scores, regime_info

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = SingularityMacroEngine()

st.title("🏛️ TIER-1 MASTER TERMINAL (v80.0)")
st.markdown('<span class="status-badge">⚡ FULLY AUTONOMOUS QUANTILE-ADAPTIVE ENGINE</span>', unsafe_allow_html=True)
st.caption("Kendi Kendini Kalibre Eden Dinamik Yüzdelik Dilim Eşikleri (Threshold Decay Korumalı)")

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
            th = res['threshold']
            commentary = res['commentary']

            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"### {asset_title} 4H Rotası")
                st.markdown(f'<span class="threshold-badge">🎯 Canlı Adaptif Eşik: ±{th:.1f}</span>', unsafe_allow_html=True)
                
                # Dinamik Adaptif Eşiğe Göre Renk!
                if score > th:
                    c = "#00E676"  # Yeşil (Boğa)
                elif score < -th:
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

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
