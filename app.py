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
st.set_page_config(page_title="TIER-1 PREDICTIVE TERMINAL (v180.0)", layout="wide", initial_sidebar_state="collapsed")
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
    .regime-mixed { background-color: #262000; color: #FFB300; border-color: #FFB300; }
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
count = st_autorefresh(interval=60000, limit=None, key="macro_v180_refresh")

# ==========================================
# 2. SAĞLAMLAŞTIRILMIŞ QUANT MAKRO MOTORU
# ==========================================
class PredictiveKinematicEngine:
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
            'ZT=F': 'BONDS_2Y',     # 2Y Hazine Vadeli
            'ZN=F': 'BONDS_10Y',    # 10Y Hazine Vadeli
            'ZB=F': 'BONDS_30Y',    # 30Y Uzun Vade Vadeli
            'HYG': 'HYG',           # Junk Kredi
            'LQD': 'LQD',           # IG Kredi
            'KRE': 'KRE',           # Bankacılık Stresi
            'XLK': 'XLK',           # Teknoloji
            'XLF': 'XLF',           # Finans
            'RSP': 'RSP',           # Eşit Ağırlıklı S&P 500
            'XME': 'XME'            # Madencilik Endeksi
        }

    def fetch_single_ticker(self, symbol, session):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=15m"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'application/json,text/plain,*/*',
            'Referer': 'https://finance.yahoo.com/'
        }
        try:
            r = session.get(url, headers=headers, timeout=4.5)
            if r.status_code == 200:
                data = r.json()
                res = data['chart']['result'][0]
                timestamps = res['timestamp']
                closes = res['indicators']['quote'][0]['close']
                df = pd.DataFrame({'time': pd.to_datetime(timestamps, unit='s'), 'Close': closes}).dropna()
                if not df.empty:
                    df.set_index('time', inplace=True)
                    return df['Close']
        except Exception:
            pass
        return pd.Series(dtype=float)

    @st.cache_data(ttl=60, show_spinner=False)
    def fetch_synchronized_grid(_self):
        raw_dict = {}
        session = requests.Session()
        
        def worker(sym, alias):
            s = _self.fetch_single_ticker(sym, session)
            if not s.empty and len(s) > 4:
                raw_dict[alias] = s

        with ThreadPoolExecutor(max_workers=10) as executor:
            for sym, alias in _self.symbol_map.items():
                executor.submit(worker, sym, alias)

        if not raw_dict:
            return pd.DataFrame()

        df = pd.DataFrame(raw_dict).sort_index()
        # İleri ve geri doldurma ile senkronizasyon (asla satır silmeyerek göstergeleri korur)
        df = df.resample('15min').last().ffill().bfill()

        # Eksik kalan sembol varsa kardeş varlıktan tamamla (Streamlit Cloud veri kesilmesini önler)
        if 'SPX' not in df and 'NQ' in df: df['SPX'] = df['NQ']
        if 'NQ' not in df and 'SPX' in df: df['NQ'] = df['SPX']
        if 'ETH' not in df and 'BTC' in df: df['ETH'] = df['BTC']
        if 'XAG' not in df and 'XAU' in df: df['XAG'] = df['XAU']
        if 'COPPER' not in df and 'XAU' in df: df['COPPER'] = df['XAU']
        if 'KRE' not in df and 'XLF' in df: df['KRE'] = df['XLF']
        if 'XLK' not in df and 'NQ' in df: df['XLK'] = df['NQ']
        if 'BONDS_2Y' not in df and 'BONDS_10Y' in df: df['BONDS_2Y'] = df['BONDS_10Y']
        if 'BONDS_30Y' not in df and 'BONDS_10Y' in df: df['BONDS_30Y'] = df['BONDS_10Y']
        if 'HYG' not in df and 'SPX' in df: df['HYG'] = df['SPX']
        if 'LQD' not in df and 'BONDS_10Y' in df: df['LQD'] = df['BONDS_10Y']

        return df.ffill().bfill()

    def calculate_predictive_kinematics(self, s):
        """
        SENİN ORİJİNAL ÇALIŞAN KİNEMATİK MOTORUN:
        Sıfırlama yapmaz, net hız, ivme ve elastisite üretir.
        """
        if s is None or s.empty:
            return 0.0
        
        s_active = s.loc[s.shift() != s].dropna()
        if len(s_active) < 16:
            s_active = s.dropna()
            
        if len(s_active) < 16:
            return 0.0
        
        # 1. HIZLAR (1H ve 4H Getiri Hızı)
        v1h = (s_active.iloc[-1] / s_active.iloc[-min(4, len(s_active)-1)]) - 1.0
        v4h = (s_active.iloc[-1] / s_active.iloc[-min(16, len(s_active)-1)]) - 1.0
        
        # 2. İKİNCİ TÜREV (İvme / Güç Tükenmesi)
        v1h_prev = (s_active.iloc[-min(4, len(s_active)-1)] / s_active.iloc[-min(8, len(s_active)-1)]) - 1.0 if len(s_active) >= 8 else v1h
        acceleration = v1h - v1h_prev
        
        # 3. LASTİK BANDI ELASTİSİTESİ
        rolling_mean_24 = s_active.tail(24).mean()
        elasticity_stretch = (s_active.iloc[-1] - rolling_mean_24) / (rolling_mean_24 + 1e-6)
        
        pct = s_active.pct_change().dropna()
        vol = pct.tail(32).std()
        if pd.isna(vol) or vol < 1e-5:
            vol = 0.0035
            
        predictive_mom = (0.45 * v1h) + (0.35 * acceleration * 2.0) - (0.20 * elasticity_stretch * 0.5) + (0.20 * v4h)
        sharpe = predictive_mom / vol
        return float(np.clip(sharpe, -2.5, 2.5))

    def calculate_ratio_predictive(self, s1, s2):
        if s1 is None or s2 is None or s1.empty or s2.empty:
            return 0.0
        common_idx = s1.index.intersection(s2.index)
        ratio = s1.loc[common_idx] / (s2.loc[common_idx] + 1e-6)
        return self.calculate_predictive_kinematics(ratio)

    def detect_rigorous_macro_regime(self, factors):
        carry = factors['Carry_Trade']
        copper = factors['Copper_Gold']
        dxy = factors['DXY_Pressure']
        yields = factors['Bond_Yield_Pressure']
        fed_pivot = factors['Fed_Pivot_Pressure']
        credit = factors['Credit_Risk_Spread']
        funding_stress = factors['Funding_Liquidity_Stress']
        spx = factors['SPX_Mom']

        if dxy < -0.5 and (carry < -0.8 or yields > 0.8 or fed_pivot > 0.5 or copper < 0.3 or funding_stress < -0.8):
            return {
                'name': "⚠️ KARIŞIK LİKİDİTE KONSOLİDASYONU (Dolar Gevşemesi vs. Fonlama/Faiz Stresi)",
                'css': "regime-mixed",
                'desc': "Zayıf Dolar taban sağlıyor ancak faiz ve bankalararası fonlama stresi baskı yaratıyor. Yönsüz denge."
            }
        elif copper > 0.6 and carry > -0.2 and spx > 0:
            return {
                'name': "🚀 HAKİKİ REFLASYON (Güçlü Büyüme & Sanayi Emtiası Liderliği)",
                'css': "regime-reflation",
                'desc': "Bakır, Gümüş ve Sanayi hisseleri küresel büyümeyi teyitli şekilde fiyatlıyor."
            }
        elif spx > 0.3 and dxy < 0.2 and yields < 0.5 and carry > -0.2:
            return {
                'name': "☀️ GENİŞ TABANLI BOĞA RALLİSİ (Goldilocks)",
                'css': "regime-goldilocks",
                'desc': "Fonlama stresi yok, Dolar zayıf, faiz baskısı kalktı. Tüm varlıklar güçlü alıcılı."
            }
        elif yields > 1.0 and fed_pivot > 0.8 and spx <= 0:
            return {
                'name': "🌋 STAGFLASYON & FED ŞAHİN SIKIŞMASI",
                'css': "regime-stagflation",
                'desc': "Yükselen faizler değerlemeleri eziyor. Güvenli liman arayışı."
            }
        elif spx < -0.5 and (credit < -0.8 or funding_stress < -1.0):
            return {
                'name': "❄️ DEFLASYONİST ÇÖKÜŞ & FONLAMA KRİZİ",
                'css': "regime-deflation",
                'desc': "Kredi piyasasında stres tırmanıyor; likidite güvenli liman tahvillere ve nakde sığınıyor."
            }
        else:
            return {
                'name': "⚪ DENGELİ GÜNLÜK GEÇİŞ REJİMİ (Konsolidasyon)",
                'css': "regime-neutral",
                'desc': "Piyasa ana bir kırılım öncesinde dengeli ve yönsüz konsolide oluyor."
            }

    def compute_all_asset_scores(self, df):
        scores = {}
        
        # 1. HAM İVMELER
        raw_spx = self.calculate_predictive_kinematics(df['SPX'])
        raw_nq  = self.calculate_predictive_kinematics(df['NQ'])
        raw_xau = self.calculate_predictive_kinematics(df['XAU'])
        raw_xag = self.calculate_predictive_kinematics(df['XAG'])

        raw_btc = self.calculate_predictive_kinematics(df['BTC'])
        raw_eth = self.calculate_predictive_kinematics(df['ETH']) if 'ETH' in df else raw_btc
        crypto_composite_mom = (0.65 * raw_btc) + (0.35 * raw_eth)

        # SPX ve NQ ARASINDAKİ YAPAY AYRIŞMAYI ÖNLEYEN ÇAPA:
        # İki endeks aynı yöne giderken birinin Boğa diğerinin Ayı çıkmasını engelleyen ana piyasa faktörü
        equity_common = (0.50 * raw_spx) + (0.50 * raw_nq)
        spx_mom = (0.70 * equity_common) + (0.30 * raw_spx)
        nq_mom  = (0.70 * equity_common) + (0.30 * raw_nq)

        metals_common = (0.50 * raw_xau) + (0.50 * raw_xag)
        xau_mom = (0.70 * metals_common) + (0.30 * raw_xau)
        xag_mom = (0.70 * metals_common) + (0.30 * raw_xag)

        btc_macro = raw_btc
        jpy_macro = self.calculate_predictive_kinematics(df['JPY'])
        dxy_macro = -self.calculate_predictive_kinematics(df['EUR'])
        
        fed_pivot_pressure = -self.calculate_predictive_kinematics(df['BONDS_2Y'])
        yield_macro = -self.calculate_predictive_kinematics(df['BONDS_10Y'])
        
        credit_risk = self.calculate_ratio_predictive(df['HYG'], df['LQD'])
        funding_stress = self.calculate_ratio_predictive(df['KRE'], df['XLF'])
        
        curve_slope = self.calculate_ratio_predictive(df['BONDS_10Y'], df['BONDS_30Y'])
        copper_gold = self.calculate_ratio_predictive(df['COPPER'], df['XAU'])
        gold_oil = self.calculate_ratio_predictive(df['XAU'], df['OIL'])
        slv_gld = self.calculate_ratio_predictive(df['XAG'], df['XAU'])
        xme_gld = self.calculate_ratio_predictive(df['XME'], df['XAU'])
        sector_rot = self.calculate_ratio_predictive(df['XLK'], df['XLF'])
        eth_btc_beta = self.calculate_ratio_predictive(df['ETH'], df['BTC'])

        factors_pool = {
            'SPX_Mom': spx_mom, 'NQ_Mom': nq_mom, 'XAU_Mom': xau_mom, 'XAG_Mom': xag_mom,
            'Crypto_Mom': crypto_composite_mom, 'ETH_BTC_Beta': eth_btc_beta,
            'Fed_Pivot_Pressure': fed_pivot_pressure, 'Bond_Yield_Pressure': yield_macro,
            'DXY_Pressure': dxy_macro, 'Yield_Curve_Slope': curve_slope,
            'Credit_Risk_Spread': credit_risk, 'Funding_Liquidity_Stress': funding_stress,
            'Sector_Rotation': sector_rot, 'Copper_Gold': copper_gold,
            'Gold_Oil': gold_oil, 'SLV_GLD_Beta': slv_gld,
            'XME_GLD_Ratio': xme_gld, 'BTC_Liquidity': btc_macro, 'Carry_Trade': jpy_macro
        }

        regime_info = self.detect_rigorous_macro_regime(factors_pool)

        # HESAPLAMA MOTORU (Fiyat Momentum Ağırlığı Güçlendirildi)
        def build_predictive_result(base_weights, factors_dict):
            multipliers = {}
            for k, w in base_weights.items():
                val = abs(factors_dict.get(k, 0.0))
                multipliers[k] = abs(w) * (1.0 + (min(val, 2.0) ** 0.8))
            
            total_att = sum(multipliers.values()) + 1e-6
            dyn_weights = {}
            for k, w in base_weights.items():
                sign = 1.0 if w >= 0 else -1.0
                raw_norm = (multipliers[k] / total_att) * 100.0
                
                # Fiyat İvmesi Çapası: Grafiğin ana yönünün ezilmesini önlemek için %30-%35'e çekildi
                if '_Mom' in k:
                    raw_norm = max(min(raw_norm, 35.0), 30.0)
                else:
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
                    'Öngörüsel İvme (Kinematics)': round(val, 2),
                    'Dinamik Ağırlık (%)': round(w, 1),
                    'Net Katkı': round(contribution, 3)
                })

            breakdown_df = pd.DataFrame(breakdown).sort_values('Net Katkı', ascending=False)
            total_score = sum(factors_dict.get(k, 0.0) * (dyn_weights[k] / 100.0) for k in dyn_weights)
            final_score = np.tanh(total_score / 1.25) * 100

            if final_score > 15:
                msg = "🚀 GÜÇLÜ BOĞA TRENDİ (4H Pozisyon Yönü: ALIM)"
                css = "div-bull"
            elif final_score < -15:
                msg = "🩸 GÜÇLÜ AYI BASKISI (4H Pozisyon Yönü: SATIŞ)"
                css = "div-bear"
            else:
                msg = "⚪ DENGELİ KONSOLİDASYON (Piyasa Yönsüz / Bekle)"
                css = "div-neutral"

            top_positive = breakdown_df.iloc[0] if not breakdown_df.empty else None
            top_negative = breakdown_df.iloc[-1] if not breakdown_df.empty else None

            pos_desc = f"{top_positive['Katman (Öncü Faktör)']} (+{top_positive['Net Katkı']:.3f})" if top_positive is not None and top_positive['Net Katkı'] > 0 else "Belirgin pozitif itiş yok"
            neg_desc = f"{top_negative['Katman (Öncü Faktör)']} ({top_negative['Net Katkı']:.3f})" if top_negative is not None and top_negative['Net Katkı'] < 0 else "Belirgin negatif baskı yok"

            if final_score > 15:
                structure = f"Öngörüsel alıcılar üstün. En büyük itiş: {pos_desc}. Ana fren: {neg_desc}."
                action = "🚀 TRENDİ SÜR: 4H Alım yönlü pozisyonlar taşınabilir. Direnç kırılımlarını izle."
                badge_cls = "action-badge"
            elif final_score < -15:
                structure = f"Öngörüsel satıcılar üstün. En büyük baskı: {neg_desc}. Karşı itiş: {pos_desc}."
                action = "🩸 SATIŞ BASKISI DEVAM: 4H Satış yönlü pozisyonlar korunabilir. Destek kırılımlarını izle."
                badge_cls = "action-badge-bear"
            else:
                structure = f"Gelecek beklentileri dengede. İtici güç: {pos_desc} vs Frenleyici güç: {neg_desc} birbirini dengeliyor."
                action = "🛑 NAKİTTE BEKLE: Net kırılım (+15 üstü veya -15 altı) gelene kadar yeni pozisyon açma."
                badge_cls = "action-badge-neutral"

            return {'score': final_score, 'table': breakdown_df, 'msg': msg, 'css': css, 'commentary': {'structure': structure, 'action': action, 'badge_cls': badge_cls}}

        # MATRİSLER (Aşırı Cezalandırmalar Dengelendi)
        spx_base = {
            'SPX_Mom': 35.0, 'Funding_Liquidity_Stress': 12.0, 'Credit_Risk_Spread': 12.0,
            'Fed_Pivot_Pressure': -10.0, 'Bond_Yield_Pressure': -8.0, 'DXY_Pressure': -8.0,
            'Sector_Rotation': 8.0, 'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0, 'Copper_Gold': 5.0
        }
        scores['SPX'] = build_predictive_result(spx_base, factors_pool)

        # NASDAQ Matrisi: SPX ile yapay ayrışmayı önlemek için faiz cezası dengelendi
        nq_base = {
            'NQ_Mom': 35.0, 'Sector_Rotation': 12.0, 'Fed_Pivot_Pressure': -12.0,
            'Bond_Yield_Pressure': -10.0, 'Funding_Liquidity_Stress': 8.0, 'Credit_Risk_Spread': 8.0,
            'DXY_Pressure': -8.0, 'Carry_Trade': 5.0, 'BTC_Liquidity': 5.0, 'Copper_Gold': 5.0
        }
        scores['NQ'] = build_predictive_result(nq_base, factors_pool)

        xau_base = {
            'XAU_Mom': 35.0, 'Yield_Curve_Slope': 15.0, 'Fed_Pivot_Pressure': -12.0,
            'DXY_Pressure': -15.0, 'Bond_Yield_Pressure': -8.0, 'Funding_Liquidity_Stress': -8.0,
            'Gold_Oil': 5.0, 'SLV_GLD_Beta': 5.0, 'Carry_Trade': 5.0, 'Copper_Gold': -3.0
        }
        scores['XAU'] = build_predictive_result(xau_base, factors_pool)

        xag_base = {
            'XAG_Mom': 35.0, 'Copper_Gold': 15.0, 'Fed_Pivot_Pressure': -12.0,
            'XME_GLD_Ratio': 10.0, 'SLV_GLD_Beta': 10.0, 'DXY_Pressure': -10.0,
            'Yield_Curve_Slope': 5.0, 'Bond_Yield_Pressure': -5.0, 'BTC_Liquidity': 5.0, 'Gold_Oil': 5.0
        }
        scores['XAG'] = build_predictive_result(xag_base, factors_pool)

        crypto_base = {
            'Crypto_Mom': 35.0, 'Fed_Pivot_Pressure': -15.0, 'Sector_Rotation': 10.0,
            'ETH_BTC_Beta': 10.0, 'DXY_Pressure': -10.0, 'Funding_Liquidity_Stress': 8.0,
            'Credit_Risk_Spread': 5.0, 'Carry_Trade': 5.0, 'Copper_Gold': 5.0, 'Bond_Yield_Pressure': -5.0
        }
        scores['CRYPTO'] = build_predictive_result(crypto_base, factors_pool)

        return scores, regime_info

# ==========================================
# 3. DASHBOARD VE GÖRSELLEŞTİRME
# ==========================================
engine = PredictiveKinematicEngine()

st.title("🏛️ TIER-1 PREDICTIVE TERMINAL (v180.0)")
st.markdown('<span class="threshold-badge">🔮 RESILIENT KINEMATICS & BALANCED FACTOR ENGINE</span>', unsafe_allow_html=True)

try:
    df_grid = engine.fetch_synchronized_grid()
    
    if df_grid.empty or len(df_grid) < 8:
        st.warning("Veriler senkronize ediliyor, lütfen birkaç saniye bekleyin...")
    else:
        results, regime_info = engine.compute_all_asset_scores(df_grid)

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
                c = "#00E676" if score > 15 else ("#FF1744" if score < -15 else "#ECEFF1")

                st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score:.1f}</h1>", unsafe_allow_html=True)
                st.markdown(f'<div class="{div_class}">{div_msg}</div>', unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="commentary-card">
                    <div class="commentary-header">📊 Öngörüsel Teşhis:</div>
                    <div>{commentary['structure']}</div>
                    <div class="{commentary['badge_cls']}">🎯 Aksiyon: {commentary['action']}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                if not table.empty:
                    fig = go.Figure(go.Bar(
                        x=table['Net Katkı'], y=table['Katman (Öncü Faktör)'], orientation='h',
                        marker_color=np.where(table['Net Katkı'] > 0, '#00E676', '#FF1744')
                    ))
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=10, b=0), height=280, 
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                        font=dict(color='#CFD8DC', size=10),
                        xaxis=dict(gridcolor='#1E293B'), yaxis=dict(gridcolor='#1E293B')
                    )
                    st.plotly_chart(fig, use_container_width=True)

            st.dataframe(table, use_container_width=True, hide_index=True)

        with tab_spx: render_view(results.get('SPX'), "S&P 500 (ES=F)")
        with tab_nq: render_view(results.get('NQ'), "NASDAQ (NQ=F)")
        with tab_xau: render_view(results.get('XAU'), "ALTIN (GC=F)")
        with tab_xag: render_view(results.get('XAG'), "GÜMÜŞ (SI=F)")
        with tab_crypto: render_view(results.get('CRYPTO'), "KRİPTO (BTC+ETH)")

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
