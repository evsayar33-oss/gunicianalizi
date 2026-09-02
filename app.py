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
st.set_page_config(page_title="TIER-1 AUTONOMOUS BRAIN (v40.0)", layout="wide", initial_sidebar_state="collapsed")
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

# 1 dakikada bir otomatik yenile
count = st_autorefresh(interval=60000, limit=None, key="macro_400_refresh")

# ==========================================
# 2. OTONOM ÖĞRENEN QUANT MAKRO BEYNİ (v40.0)
# ==========================================
class AutonomousMacroBrain:
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

    def calculate_kinetic_series(self, s):
        """Her bar için 15m (%50) + 1H (%30) + 4H (%20) kinetik ivme serisi üretir."""
        if s is None or len(s) < 32:
            return pd.Series(0.0, index=s.index if s is not None else [0])
        
        r15m = s.pct_change(1).fillna(0)
        r1h  = s.pct_change(4).fillna(0)
        r4h  = s.pct_change(16).fillna(0)
        
        kinetic_series = (0.50 * r15m) + (0.30 * r1h) + (0.20 * r4h)
        vol = s.pct_change().rolling(32, min_periods=4).std().fillna(0.003)
        sharpe_series = kinetic_series / (vol + 1e-5)
        return sharpe_series.clip(-2.5, 2.5)

    def calculate_ratio_kinetic_series(self, s1, s2):
        if s1 is None or s2 is None or s1.empty or s2.empty:
            return pd.Series(0.0, index=s1.index if s1 is not None else [0])
        common_idx = s1.index.intersection(s2.index)
        ratio = s1.loc[common_idx] / (s2.loc[common_idx] + 1e-6)
        return self.calculate_kinetic_series(ratio)

    def compute_online_learning_ic(self, factor_series, target_price_series, lag=4, window=48):
        """
        WALK-FORWARD ML (ONLINE IC LEARNING):
        Faktörün son 12 saatteki (48 bar) tahmin doğruluğunu ve PnL korelasyonunu ölçer.
        Doğru bilen faktörü ödüllendirir, terse düşeni cezalandırır.
        """
        if len(factor_series) < window + lag or len(target_price_series) < window + lag:
            return 0.0
        
        # 4 bar (1 saat) sonraki gerçek hedef getirisi
        target_fwd_ret = target_price_series.pct_change(lag).shift(-lag).tail(window)
        f_past_signal  = factor_series.tail(window)
        
        valid_mask = ~(target_fwd_ret.isna() | f_past_signal.isna())
        if valid_mask.sum() < 12:
            return 0.0
            
        corr = f_past_signal[valid_mask].corr(target_fwd_ret[valid_mask])
        return float(np.clip(0.0 if pd.isna(corr) else corr, -0.9, 0.9))

    def detect_consensus_macro_regime(self, factors):
        spx = factors['SPX_Mom'].iloc[-1]
        nq = factors['NQ_Mom'].iloc[-1]
        copper = factors['Copper_Gold'].iloc[-1]
        sector = factors['Sector_Rotation'].iloc[-1]
        dxy = factors['DXY_Pressure'].iloc[-1]
        yields = factors['Bond_Yield_Pressure'].iloc[-1]
        credit = factors['Credit_Risk_Spread'].iloc[-1]

        if spx > 0.3 and nq > 0.3 and sector >= -0.5 and copper >= -0.5 and dxy <= 0.5:
            return {'name': "☀️ GENİŞ TABANLI BOĞA RALLİSİ (Goldilocks)", 'css': "regime-goldilocks", 'desc': "Teknoloji ve sanayi katılımıyla genişleyen sağlıklı küresel ralli."}
        elif dxy < -0.5 and (sector < -0.6 or copper < -0.6):
            return {'name': "⚠️ SEÇİCİ DOLAR GEVŞEMESİ & SAVUNMACI ROTASYON", 'css': "regime-mixed", 'desc': "Dolar düşüşü hisseleri tutuyor ancak Teknoloji ve Sanayi zayıf."}
        elif copper > 0.8 and factors['Gold_Oil'].iloc[-1] > 0 and spx > 0:
            return {'name': "🚀 REFLASYON (Sanayi & Emtia Liderliği)", 'css': "regime-reflation", 'desc': "Gümüş ve Bakır küresel büyümeyi fiyatlıyor."}
        elif yields > 0.8 and (spx < 0 or nq < 0):
            return {'name': "🌋 STAGFLASYON & LİKİDİTE SIKIŞMASI", 'css': "regime-stagflation", 'desc': "Yükselen faizler değerlemeleri baskılıyor."}
        elif spx < -0.5 and credit < -0.8:
            return {'name': "❄️ DEFLASYONİST ÇÖKÜŞ & KREDİ KRİZİ", 'css': "regime-deflation", 'desc': "Tüm riskli varlıklardan nakde kaçış."}
        else:
            return {'name': "⚪ DENGELİ GEÇİŞ REJİMİ (Konsolidasyon)", 'css': "regime-goldilocks", 'desc': "Piyasa dengeli ve yönsüz konsolide oluyor."}

    def compute_all_asset_scores(self, df):
        scores = {}
        
        # 1. TÜM KİNETİK ZAMAN SERİLERİ
        spx_mom = self.calculate_kinetic_series(df['SPX'])
        nq_mom = self.calculate_kinetic_series(df['NQ'])
        xau_mom = self.calculate_kinetic_series(df['XAU'])
        xag_mom = self.calculate_kinetic_series(df['XAG'])
        
        btc_mom = self.calculate_kinetic_series(df['BTC'])
        jpy_mom = self.calculate_kinetic_series(df['JPY'])
        dxy_mom = -self.calculate_kinetic_series(df['EUR'])
        yield_mom = -self.calculate_kinetic_series(df['BONDS_10Y'])
        
        copper_gold = self.calculate_ratio_kinetic_series(df['COPPER'], df['XAU'])
        gold_oil = self.calculate_ratio_kinetic_series(df['XAU'], df['OIL'])
        slv_gld = self.calculate_ratio_kinetic_series(df['XAG'], df['XAU'])
        xme_gld = self.calculate_ratio_kinetic_series(df['XME'], df['XAU'])
        
        credit_risk = self.calculate_ratio_kinetic_series(df['HYG'], df['LQD'])
        credit_flight = self.calculate_ratio_kinetic_series(df['HYG'], df['BONDS_30Y'])
        sector_rot = self.calculate_ratio_kinetic_series(df['XLK'], df['XLF'])
        real_yield_shock = self.calculate_ratio_kinetic_series(df['BONDS_10Y'], df['BONDS_30Y'])

        factors_series_pool = {
            'SPX_Mom': spx_mom, 'NQ_Mom': nq_mom, 'XAU_Mom': xau_mom, 'XAG_Mom': xag_mom,
            'Copper_Gold': copper_gold, 'Gold_Oil': gold_oil, 'SLV_GLD_Beta': slv_gld,
            'XME_GLD_Ratio': xme_gld, 'Credit_Risk_Spread': credit_risk, 'Credit_Flight_Safety': credit_flight,
            'Sector_Rotation': sector_rot, 'Real_Yield_Shock': real_yield_shock,
            'DXY_Pressure': dxy_mom, 'Bond_Yield_Pressure': yield_mom, 'BTC_Liquidity': btc_mom, 'Carry_Trade': jpy_mom
        }

        # REJİM KONSENSÜSÜ
        regime_info = self.detect_consensus_macro_regime(factors_series_pool)

        # ==========================================
        # 2. OTONOM ÖĞRENEN HESAPLAMA MOTORU
        # ==========================================
        def build_autonomous_result(base_weights, target_sym, target_mom_val):
            target_price_series = df[target_sym]
            
            multipliers = {}
            factor_ics = {}
            
            for k, w_base in base_weights.items():
                f_s = factors_series_pool[k]
                latest_val = abs(f_s.iloc[-1])
                
                # 1. CANLI IC / PnL ÖĞRENME KATSAYISI
                ic = self.compute_online_learning_ic(f_s, target_price_series)
                factor_ics[k] = ic
                
                # Doğru tahmin eden faktörün ağırlığı katlanır (exp(sign * ic))
                sign = 1.0 if w_base >= 0 else -1.0
                learning_factor = np.exp(sign * ic * 1.0)
                
                # 2. ŞOK DİKKAT ÇARPAN
                shock_boost = (1.0 + (min(latest_val, 2.5) ** 1.0))
                
                multipliers[k] = abs(w_base) * learning_factor * shock_boost

            total_att = sum(multipliers.values()) + 1e-6
            dyn_weights = {}
            for k, w_base in base_weights.items():
                sign = 1.0 if w_base >= 0 else -1.0
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
                    'Kinetik İvme': round(val, 2),
                    'Öğrenilmiş Ağırlık (%)': round(w, 1),
                    'Net Katkı': round(contribution, 3)
                })

            breakdown_df = pd.DataFrame(breakdown).sort_values('Öğrenilmiş Ağırlık (%)', ascending=False)
            total_score = sum(factors_series_pool[k].iloc[-1] * (dyn_weights[k] / 100.0) for k in dyn_weights)
            
            final_score = np.tanh(total_score / 1.3) * 100

            if final_score > 15:
                msg = "🚀 GÜÇLÜ BOĞA TRENDİ (Alıcılar ve Öğrenilmiş Makro Güç Hakim)"
                css = "div-bull"
            elif final_score < -15:
                msg = "🩸 GÜÇLÜ AYI BASKISI (Satıcılar ve Makro Fren Üstün)"
                css = "div-bear"
            else:
                msg = "⚪ DENGELİ KONSOLİDASYON (Piyasa Yönsüz / Bekle)"
                css = "div-neutral"

            return {'score': final_score, 'table': breakdown_df, 'msg': msg, 'css': css}

        # ----------------------------------------------------
        # 10 KATMANLI EKSİKSİZ KURUMSAL MATRİSLER
        # ----------------------------------------------------
        # 1. GÜMÜŞ (XAG)
        xag_base = {
            'XAG_Mom': 30.0, 'Copper_Gold': 20.0, 'XME_GLD_Ratio': 20.0,
            'SLV_GLD_Beta': 10.0, 'Real_Yield_Shock': 10.0, 'DXY_Pressure': -10.0,
            'BTC_Liquidity': 5.0, 'Gold_Oil': 5.0, 'Credit_Risk_Spread': 5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['XAG'] = build_autonomous_result(xag_base, 'XAG', xag_mom.iloc[-1])

        # 2. ALTIN (XAU)
        xau_base = {
            'XAU_Mom': 30.0, 'Real_Yield_Shock': 25.0, 'DXY_Pressure': -20.0,
            'Bond_Yield_Pressure': -15.0, 'Gold_Oil': 15.0, 'SLV_GLD_Beta': 10.0,
            'Credit_Flight_Safety': -5.0, 'Carry_Trade': 5.0, 'Copper_Gold': -3.0, 'BTC_Liquidity': -2.0
        }
        scores['XAU'] = build_autonomous_result(xau_base, 'XAU', xau_mom.iloc[-1])

        # 3. S&P 500 (SPX)
        spx_base = {
            'SPX_Mom': 30.0, 'Credit_Flight_Safety': 15.0, 'Credit_Risk_Spread': 15.0,
            'Sector_Rotation': 10.0, 'Carry_Trade': 10.0, 'BTC_Liquidity': 5.0,
            'Copper_Gold': 5.0, 'DXY_Pressure': -5.0, 'Real_Yield_Shock': -5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['SPX'] = build_autonomous_result(spx_base, 'SPX', spx_mom.iloc[-1])

        # 4. NASDAQ (NQ)
        nq_base = {
            'NQ_Mom': 30.0, 'Sector_Rotation': 20.0, 'Credit_Flight_Safety': 10.0,
            'Credit_Risk_Spread': 10.0, 'Carry_Trade': 10.0, 'BTC_Liquidity': 5.0,
            'Copper_Gold': 5.0, 'DXY_Pressure': -5.0, 'Real_Yield_Shock': -5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['NQ'] = build_autonomous_result(nq_base, 'NQ', nq_mom.iloc[-1])

        return scores, regime_info

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = AutonomousMacroBrain()

st.title("🏛️ TIER-1 AUTONOMOUS BRAIN (v40.0)")
st.markdown('<span class="status-badge">🧠 WALK-FORWARD ML & ONLINE PnL ADAPTATION ACTIVE</span>', unsafe_allow_html=True)
st.caption("10-Katmanlı Canlı Matris + Tahmin Doğruluğuna Göre Kendi Kendine Öğrenen Ağırlık Motoru")

try:
    df_grid = engine.fetch_synchronized_grid()
    
    if df_grid.empty or len(df_grid) < 24:
        st.warning("Veriler 15m ızgarasında senkronize ediliyor, lütfen bekleyin...")
    else:
        results, regime_info = engine.compute_all_asset_scores(df_grid)

        # ÜST REJİM BANDI
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
                        x=table['Öğrenilmiş Ağırlık (%)'], y=table['Katman (Öncü Faktör)'], orientation='h',
                        marker_color=np.where(table['Öğrenilmiş Ağırlık (%)'] > 0, '#00E676', '#FF1744')
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
