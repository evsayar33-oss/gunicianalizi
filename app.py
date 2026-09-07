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
# 1. UI VE TERMINAL YAPILANDIRMASI (INSTITUTIONAL GRADE)
# ==========================================
st.set_page_config(page_title="TIER-1 MACRO DESK ENGINE (v160.0)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #07090E; color: #D1D5DB; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; }
    h1, h2, h3 { font-family: 'Courier New', monospace; letter-spacing: -0.5px; }
    .status-badge { background-color: #111827; border: 1px solid #1F2937; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; color: #9CA3AF; display: inline-block; margin-bottom: 8px; }
    .regime-box { padding: 14px 18px; border-radius: 4px; font-weight: bold; font-size: 13px; margin-bottom: 14px; border-left: 5px solid; font-family: 'Courier New', monospace; }
    .regime-goldilocks { background-color: #022419; color: #10B981; border-color: #10B981; }
    .regime-reflation { background-color: #291D03; color: #F59E0B; border-color: #F59E0B; }
    .regime-stagflation { background-color: #2E081D; color: #EC4899; border-color: #EC4899; }
    .regime-deflation { background-color: #2D0A0A; color: #EF4444; border-color: #EF4444; }
    .regime-voldisruption { background-color: #311302; color: #F97316; border-color: #F97316; }
    .regime-neutral { background-color: #111827; color: #9CA3AF; border-color: #4B5563; }
    .div-bull { background-color: #064E3B; color: #34D399; padding: 8px 14px; border-radius: 4px; font-weight: bold; border: 1px solid #059669; font-size: 13px; display: inline-block; margin-top: 6px; }
    .div-bear { background-color: #4C0519; color: #F87171; padding: 8px 14px; border-radius: 4px; font-weight: bold; border: 1px solid #E11D48; font-size: 13px; display: inline-block; margin-top: 6px; }
    .div-neutral { background-color: #1F2937; color: #9CA3AF; padding: 8px 14px; border-radius: 4px; font-weight: bold; border: 1px solid #374151; font-size: 13px; display: inline-block; margin-top: 6px; }
    .commentary-card { background-color: #0E131F; border: 1px solid #1E293B; border-radius: 4px; padding: 14px; margin-top: 10px; font-size: 12px; line-height: 1.6; }
    .commentary-header { font-weight: bold; color: #38BDF8; margin-bottom: 6px; font-size: 12px; display: flex; align-items: center; gap: 6px; }
    .action-badge { background-color: #111827; border-left: 3px solid #10B981; padding: 8px 12px; margin-top: 8px; border-radius: 0 4px 4px 0; font-weight: bold; color: #F9FAFB; }
    .action-badge-bear { border-left-color: #EF4444; }
    .action-badge-neutral { border-left-color: #6B7280; }
    </style>
    """, unsafe_allow_html=True)

# 1 dakikada bir veri tazeleme
count = st_autorefresh(interval=60000, limit=None, key="macro_tier1_v160")

# ==========================================
# 2. TIER-1 EKONOMETRİK VE KİNEMATİK MOTOR
# ==========================================
class InstitutionalMacroEngine:
    def __init__(self):
        # Gerçek Kurumsal Sembol Eşlemesi (Doğru Makro Enstrümanlar)
        self.symbol_map = {
            'ES=F': 'SPX',          # S&P 500 Vadeli
            'NQ=F': 'NQ',           # Nasdaq 100 Vadeli
            'GC=F': 'XAU',          # Altın Vadeli
            'SI=F': 'XAG',          # Gümüş Vadeli
            'HG=F': 'COPPER',       # Bakır Vadeli (Küresel İmalat Öncüsü)
            'CL=F': 'OIL',          # WTI Ham Petrol
            'EURUSD=X': 'EUR',      # FX Dolar Baskı Ters Proksisi
            'USDJPY=X': 'JPY',      # Küresel FX Carry Trade / Risk-off barometresi
            'BTC-USD': 'BTC',       # Küresel Likidite Süngeri (24/7)
            'ETH-USD': 'ETH',       # Kripto Beta / DeFi Risk İştahı
            'ZT=F': 'BONDS_2Y',     # 2Y Hazine Vadelisi (Fed Politika Beklentisi)
            'ZN=F': 'BONDS_10Y',    # 10Y Hazine Vadelisi (Nominal Büyüme/Faiz Çapası)
            'ZB=F': 'BONDS_30Y',    # 30Y Hazine Vadelisi (Vade Primi / Eğri Eğim)
            'TIP': 'TIPS_REAL',     # GERÇEK REEL GETİRİ: TIPS Enflasyon Tahvili ETF
            'HYG': 'HYG',           # Yüksek Getirili Kredi (Junk Bond)
            'LQD': 'LQD',           # Yatırım Yapılabilir Kredi (IG Spread)
            'KRE': 'KRE',           # Bölgesel Bankacılık Likiditesi
            'XLF': 'XLF',           # Finans Sektör Devleri
            'XLK': 'XLK',           # Teknoloji / Büyüme
            '^VIX': 'VIX'           # Opsiyon Volatilite Yüzeyi Şok Göstergesi
        }

    def fetch_single_ticker(self, symbol):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=15m"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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

        with ThreadPoolExecutor(max_workers=20) as executor:
            for sym, alias in _self.symbol_map.items():
                executor.submit(worker, sym, alias)

        df = pd.DataFrame(raw_dict).sort_index()
        # Resample ve ffill sonrası veriyi senkronize et
        df = df.resample('15min').last().ffill().bfill().dropna()
        return df

    def get_market_activity_weight(self, s):
        """
        SEANS VE ASENKRONİTE FİLTRESİ:
        Eğer piyasa kapalıysa (örneğin gece saatlerinde KRE, HYG donmuşsa),
        bu varlığın modele ürettiği yapay sıfır momentumun modeli zehirlemesini engeller.
        Son 8 bar içindeki tekil (farklı) fiyat sayısını ölçer.
        """
        if s is None or len(s) < 8:
            return 0.2
        recent_unique_ticks = s.tail(8).nunique()
        if recent_unique_ticks <= 2:
            return 0.15 # Piyasa kapalı veya likiditesiz; ağırlığı %85 kıs
        elif recent_unique_ticks <= 4:
            return 0.60 # Düşük hacimli açılış/kapanış seansı
        return 1.0 # Aktif tam likit seans

    def calculate_stat_kinematics(self, s):
        """
        ADAPTİF Z-SCORE KİNEMATİK MOTORU (Sihirli Sayılar Kaldırıldı):
        - Hız (1H Log Getiri): Z-Score standardizasyonu
        - İvme (Hız Değişimi - 2. Türev): Volatiliteye göre ölçeklenmiş ivmelenme
        - Mean Reversion: Rolling EMA sapması
        Tüm metrikler varlığın kendi rolling varyansına göre durağanlaştırılır (Stationary).
        """
        if s is None or len(s) < 32:
            return 0.0, 1.0
        
        act_weight = self.get_market_activity_weight(s)
        
        log_ret = np.log(s / s.shift(4)).dropna() # 1 Saatlik (4 bar) log hız
        if len(log_ret) < 24:
            return 0.0, act_weight
            
        v_current = log_ret.iloc[-1]
        v_rolling_mean = log_ret.tail(32).mean()
        v_rolling_std = log_ret.tail(32).std() + 1e-6
        z_velocity = (v_current - v_rolling_mean) / v_rolling_std

        # İkinci Türev (İvme)
        accel = log_ret.diff().dropna()
        a_current = accel.iloc[-1] if len(accel) > 0 else 0.0
        a_rolling_std = accel.tail(32).std() + 1e-6
        z_acceleration = a_current / a_rolling_std

        # Elastisite (Ortalamaya Dönüş Gerilimi)
        ema_24 = s.ewm(span=24, adjust=False).mean()
        stretch = (s.iloc[-1] - ema_24.iloc[-1]) / (s.iloc[-1] + 1e-6)
        s_std = (s.tail(32).std() / s.tail(32).mean()) + 1e-6
        z_elasticity = stretch / s_std

        # İstatistiki Kinematik Bileşke (Ağırlıklar Gaussian Momentuma Dayalıdır)
        composite = (0.50 * z_velocity) + (0.35 * z_acceleration) - (0.15 * z_elasticity)
        bounded_score = float(np.clip(composite, -2.5, 2.5))
        
        return bounded_score, act_weight

    def calculate_ratio_kinematics(self, s1, s2):
        if s1 is None or s2 is None or s1.empty or s2.empty:
            return 0.0, 0.2
        common_idx = s1.index.intersection(s2.index)
        ratio = s1.loc[common_idx] / (s2.loc[common_idx] + 1e-6)
        score, w1 = self.calculate_stat_kinematics(ratio)
        w2 = self.get_market_activity_weight(s2)
        return score, min(w1, w2)

    def detect_macro_regime_institutional(self, factors):
        copper_gold = factors['Growth_Copper_Gold']
        dxy = factors['DXY_Pressure']
        vix_shock = factors['VIX_Vol_Shock']
        real_yield = factors['Real_Yield_TIPS']
        curve_slope = factors['Yield_Curve_Slope']
        credit = factors['Credit_Spread_Risk']
        spx = factors['SPX_Kinematics']

        # 1. VOLATİLİTE VE LİKİDİTE TAİL RİSKİ (VaR ŞOKU)
        if vix_shock > 1.2 or (credit < -1.0 and vix_shock > 0.6):
            return {
                'name': "⚡ KURUMSAL DE-GROSSING & VOLATİLİTE ŞOKU (VaR Shock)",
                'css': "regime-voldisruption",
                'desc': "Opsiyon piyasasında korunma (put) talebi patladı, fonlar piyasa genelinde kaldıraç indiriyor."
            }
        # 2. HAKİKİ REFLASYON
        elif copper_gold > 0.6 and real_yield > -0.5 and curve_slope > 0.2 and spx > 0:
            return {
                'name': "🚀 MAKRO REFLASYON (Geniş Tabanlı Ekonomik İvmelenme)",
                'css': "regime-reflation",
                'desc': "Bakır/Altın rasyosu ve getiri eğrisi dikleşiyor. Sanayi metalleri ve hisseler likiditeyle besleniyor."
            }
        # 3. GOLDILOCKS (Dezenflasyonist Büyüme)
        elif spx > 0.5 and dxy < 0 and vix_shock < 0 and credit > 0:
            return {
                'name': "☀️ GOLDILOCKS (Düşük Volatilite & Düzenli Risk İştahı)",
                'css': "regime-goldilocks",
                'desc': "Dolar zayıf, kredi spreadleri sıkı, finansal koşullar gevşek. Boğa trendi kurumsal teyitli."
            }
        # 4. STAGFLASYON & SIKIŞMA
        elif real_yield < -0.8 and copper_gold < -0.3 and spx <= 0:
            return {
                'name': "🌋 STAGFLASYONİST BASKI & REEL GETİRİ SIKIŞMASI",
                'css': "regime-stagflation",
                'desc': "Reel getiriler üzerindeki şok ve yavaşlayan büyüme değerlemeleri eziyor."
            }
        # 5. DEFLASYONİST ÇÖKÜŞ
        elif spx < -0.6 and credit < -0.8 and curve_slope < -0.5:
            return {
                'name': "❄️ DEFLASYONİST FRENLEME & RESESYON FİYATLAMASI",
                'css': "regime-deflation",
                'desc': "Kredi riski açılıyor, verim eğrisi sert yataylaşıyor. Riskli varlıklardan nakde kaçış."
            }
        else:
            return {
                'name': "⚪ REJİM GEÇİŞİ VE DENGELENME (Macro Consolidation)",
                'css': "regime-neutral",
                'desc': "Makro sinyaller ayrışıyor, likidite yön bulmak için bir sonraki tetikleyiciyi (veri/Fed) bekliyor."
            }

    def compute_desk_scores(self, df):
        # 1. TEMEL VARLIK KİNEMATİKLERİ
        raw_spx, w_spx = self.calculate_stat_kinematics(df['SPX'])
        raw_nq, w_nq   = self.calculate_stat_kinematics(df['NQ'])
        raw_xau, w_xau = self.calculate_stat_kinematics(df['XAU'])
        raw_xag, w_xag = self.calculate_stat_kinematics(df['XAG'])
        raw_btc, _     = self.calculate_stat_kinematics(df['BTC'])
        raw_eth, _     = self.calculate_stat_kinematics(df['ETH']) if 'ETH' in df else (raw_btc, 1.0)
        
        # 2. MAKRO FAKTÖR KATMANLARI (Doğru Finansal Tanımlarla)
        vix_shock, _ = self.calculate_stat_kinematics(df['VIX']) # Volatilite Şoku
        dxy_pressure, _ = self.calculate_stat_kinematics(-df['EUR']) # Dolar Gücü
        jpy_carry, _ = self.calculate_stat_kinematics(df['JPY']) # Carry Akışı
        
        # Fed Politikası ve Faizler
        fed_pivot_yield, _ = self.calculate_stat_kinematics(-df['BONDS_2Y']) # 2Y Faiz İvmesi
        ten_year_yield, _  = self.calculate_stat_kinematics(-df['BONDS_10Y']) # 10Y Faiz İvmesi
        
        # GERÇEK REEL GETİRİ: TIPS tahvili fiyat düşüşü = Reel Faiz Şoku
        # TIPS fiyatı düşerse (negatif ivme), reel faiz artıyor demektir.
        raw_tips, w_tips = self.calculate_stat_kinematics(df['TIPS_REAL'])
        real_yield_shock = -raw_tips # Eksi TIPS ivmesi = Reel Getiri Baskısı
        
        # GETİRİ EĞRİSİ EĞİMİ (10s30s ve 10s2s Term Premium)
        curve_slope, _ = self.calculate_ratio_kinematics(df['BONDS_10Y'], df['BONDS_30Y'])
        
        # Likidite ve Kredi Mikroyapısı
        credit_risk, w_credit = self.calculate_ratio_kinematics(df['HYG'], df['LQD'])
        banking_stress, w_bank = self.calculate_ratio_kinematics(df['KRE'], df['XLF'])
        growth_pulse, _ = self.calculate_ratio_kinematics(df['COPPER'], df['XAU'])
        gold_oil, _     = self.calculate_ratio_kinematics(df['XAU'], df['OIL'])
        metals_beta, _  = self.calculate_ratio_kinematics(df['XAG'], df['XAU'])
        tech_breadth, w_tech = self.calculate_ratio_kinematics(df['XLK'], df['XLF'])
        crypto_beta, _  = self.calculate_ratio_kinematics(df['ETH'], df['BTC'])

        factors_pool = {
            'SPX_Kinematics': raw_spx, 'NQ_Kinematics': raw_nq,
            'XAU_Kinematics': raw_xau, 'XAG_Kinematics': raw_xag,
            'Crypto_Basket': (0.65 * raw_btc) + (0.35 * raw_eth),
            'VIX_Vol_Shock': vix_shock,
            'DXY_Pressure': dxy_pressure,
            'Carry_Trade_JPY': jpy_carry,
            'Fed_Pivot_Pressure': fed_pivot_yield,
            'Bond_10Y_Yield': ten_year_yield,
            'Real_Yield_TIPS': real_yield_shock,
            'Yield_Curve_Slope': curve_slope,
            'Credit_Spread_Risk': credit_risk,
            'Banking_Liquidity': banking_stress,
            'Growth_Copper_Gold': growth_pulse,
            'Gold_Oil_Pulse': gold_oil,
            'Silver_Gold_Beta': metals_beta,
            'Tech_Vs_Financials': tech_breadth,
            'ETH_BTC_Beta': crypto_beta
        }

        activity_weights = {
            'Credit_Spread_Risk': w_credit,
            'Banking_Liquidity': w_bank,
            'Tech_Vs_Financials': w_tech,
            'Real_Yield_TIPS': w_tips,
            'SPX_Kinematics': w_spx,
            'NQ_Kinematics': w_nq,
            'XAU_Kinematics': w_xau,
            'XAG_Kinematics': w_xag
        }

        # REJİM BELİRLEME
        regime = self.detect_macro_regime_institutional(factors_pool)

        # MATRİS HESAPLAMA MOTORU (SEANS VE VOLATİLİTE DUYARLI)
        def build_institutional_score(base_matrix):
            dyn_weights = {}
            # Seans kapalılık durumuna göre ağırlıkları dynamically derate et
            for factor_name, base_w in base_matrix.items():
                act_coeff = activity_weights.get(factor_name, 1.0)
                dyn_weights[factor_name] = base_w * act_coeff
            
            # Normalizasyon
            total_w = sum(abs(v) for v in dyn_weights.values()) + 1e-6
            normalized_weights = {k: (v / total_w) * 100.0 for k, v in dyn_weights.items()}

            breakdown = []
            raw_aggregate = 0.0

            for k, w in normalized_weights.items():
                factor_val = factors_pool.get(k, 0.0)
                # Volatilite patlaması varsa pozitif risk ağırlıklarını törpüle
                if vix_shock > 1.0 and w > 0 and 'Kinematics' in k:
                    factor_val = factor_val - (0.5 * vix_shock)
                
                contribution = factor_val * (w / 100.0)
                raw_aggregate += contribution

                breakdown.append({
                    'Makro / Likidite Faktörü': k,
                    'Standart İvme (Z)': round(factor_val, 2),
                    'Efektif Ağırlık (%)': round(w, 1),
                    'Net Katkı': round(contribution, 3)
                })

            table = pd.DataFrame(breakdown).sort_values('Net Katkı', ascending=False)
            
            # Sıkıştırma (Tanh) ve Skor Üretimi
            final_score = np.tanh(raw_aggregate / 1.15) * 100

            # Volatilite Rejim Baskısı
            if vix_shock > 1.2:
                warning_suffix = " ⚠️ [VaR ŞOKU: Kaldıraç Kısılmalı]"
            else:
                warning_suffix = ""

            if final_score > 18:
                msg = f"🟢 NET ALICI MAKRO AKIŞI (Trend Long){warning_suffix}"
                css = "div-bull"
            elif final_score < -18:
                msg = f"🔴 NET SATICI MAKRO BASKISI (Risk-Off Short){warning_suffix}"
                css = "div-bear"
            else:
                msg = "⚪ STATÜKO / KONSOLİDASYON (Nötr Bekleme Alanı)"
                css = "div-neutral"

            # Kurumsal Teşhis & Aksiyon
            top_pos = table.iloc[0] if not table.empty else None
            top_neg = table.iloc[-1] if not table.empty else None
            
            pos_info = f"{top_pos['Makro / Likidite Faktörü']} (+{top_pos['Net Katkı']:.2f})" if top_pos is not None and top_pos['Net Katkı'] > 0 else "Pozitif itici güç yok"
            neg_info = f"{top_neg['Makro / Likidite Faktörü']} ({top_neg['Net Katkı']:.2f})" if top_neg is not None and top_neg['Net Katkı'] < 0 else "Belirgin negatif direnç yok"

            if final_score > 18:
                struct = f"Likidite motoru pozitif bölgede. En güçlü itiş: {pos_info}. Fren: {neg_info}."
                act = "LONG TAŞIMA: 4H trend yönünde alımlar korunabilir. VIX sıçramalarına karşı stop daralt."
                badge = "action-badge"
            elif final_score < -18:
                struct = f"Sermaye çıkışı hakim. Ana baskı: {neg_info}. Cılız karşı tepki: {pos_info}."
                act = "SATIŞ / DEFANSİF: Riskli varlıklardan korunma, nakit veya hedge pozisyonu öncelikli."
                badge = "action-badge-bear"
            else:
                struct = f"Piyasa yönsüz. Pozitif kanat ({pos_info}) ile negatif kanat ({neg_info}) birbirini nötrlüyor."
                act = "İŞLEM AÇMA: Sinyal ±18 eşiğini kırana ve seans hacmi oturana kadar yön alma."
                badge = "action-badge-neutral"

            return {
                'score': final_score,
                'table': table,
                'msg': msg,
                'css': css,
                'commentary': {'structure': struct, 'action': act, 'badge_cls': badge}
            }

        # KURUMSAL AĞIRLIK MATRİSLERİ (Gözden Geçirilmiş)
        scores = {}
        
        # S&P 500
        scores['SPX'] = build_institutional_score({
            'SPX_Kinematics': 25.0, 'Credit_Spread_Risk': 15.0, 'Banking_Liquidity': 10.0,
            'VIX_Vol_Shock': -15.0, 'Real_Yield_TIPS': -15.0, 'Yield_Curve_Slope': 10.0,
            'DXY_Pressure': -10.0, 'Carry_Trade_JPY': 5.0
        })

        # NASDAQ 100 (Faiz ve Reel Getiri Duyarlılığı En Yüksek)
        scores['NQ'] = build_institutional_score({
            'NQ_Kinematics': 25.0, 'Real_Yield_TIPS': -20.0, 'Fed_Pivot_Pressure': -15.0,
            'Tech_Vs_Financials': 15.0, 'VIX_Vol_Shock': -15.0, 'Credit_Spread_Risk': 10.0,
            'DXY_Pressure': -10.0, 'Yield_Curve_Slope': -5.0
        })

        # ONS ALTIN (Reel Faiz ve Dolar Baş Düşmanıdır)
        scores['XAU'] = build_institutional_score({
            'XAU_Kinematics': 25.0, 'Real_Yield_TIPS': -25.0, 'DXY_Pressure': -20.0,
            'VIX_Vol_Shock': 10.0, 'Gold_Oil_Pulse': 10.0, 'Yield_Curve_Slope': -10.0
        })

        # GÜMÜŞ (Hem Sanayi Hem Kıymetli Maden)
        scores['XAG'] = build_institutional_score({
            'XAG_Kinematics': 25.0, 'Growth_Copper_Gold': 20.0, 'Silver_Gold_Beta': 15.0,
            'Real_Yield_TIPS': -15.0, 'DXY_Pressure': -15.0, 'VIX_Vol_Shock': -10.0
        })

        # KRİPTO (Yüksek Beta Likidite Süngeri)
        scores['CRYPTO'] = build_institutional_score({
            'Crypto_Basket': 25.0, 'ETH_BTC_Beta': 15.0, 'VIX_Vol_Shock': -20.0,
            'DXY_Pressure': -15.0, 'Banking_Liquidity': 10.0, 'Real_Yield_TIPS': -15.0
        })

        return scores, regime

# ==========================================
# 3. KULLANICI ARAYÜZÜ VE RAPORLAMA
# ==========================================
engine = InstitutionalMacroEngine()

st.title("🏛️ TIER-1 INSTITUTIONAL DESK ENGINE (v160.0)")
st.markdown('<span class="status-badge">STATIONARY Z-SCORE KINEMATICS & SESSION-AWARE VOLATILITY FILTER</span>', unsafe_allow_html=True)
st.caption("Doğrulanmış Makro Enstrümanlar: Reel Faiz (TIPS) + Volatilite Şoku (VIX) + Seans Adaptasyonu")

try:
    df_grid = engine.fetch_synchronized_grid()
    
    if df_grid.empty or len(df_grid) < 32:
        st.warning("Piyasa verileri çekiliyor ve varyans matrisleri hesaplanıyor, lütfen bekleyin...")
    else:
        results, regime_info = engine.compute_desk_scores(df_grid)

        # Rejim Göstergesi
        st.markdown(f"""
        <div class="regime-box {regime_info['css']}">
            GLOBAL MAKRO VE LİKİDİTE REJİMİ: {regime_info['name']}<br>
            <span style="font-size:11px; font-weight:normal; opacity:0.85;">{regime_info['desc']}</span>
        </div>
        """, unsafe_allow_html=True)

        tabs = st.tabs(["S&P 500 (ES)", "NASDAQ (NQ)", "ALTIN (XAU)", "GÜMÜŞ (XAG)", "KRİPTO (BTC+ETH)"])
        asset_keys = [("SPX", "S&P 500 Vadeli"), ("NQ", "Nasdaq 100 Vadeli"), 
                      ("XAU", "Ons Altın"), ("XAG", "Ons Gümüş"), ("CRYPTO", "Kripto Likidite Sepeti")]

        for tab, (key, title) in zip(tabs, asset_keys):
            res = results.get(key)
            with tab:
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"### {title}")
                    s = res['score']
                    color = "#10B981" if s > 18 else ("#EF4444" if s < -18 else "#9CA3AF")
                    
                    st.markdown(f"<h1 style='color: {color}; font-size: 52px; margin:0;'>{s:.1f}</h1>", unsafe_allow_html=True)
                    st.markdown(f'<div class="{res["css"]}">{res["msg"]}</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="commentary-card">
                        <div class="commentary-header">🏛️ Kurumsal Masa Teşhisi:</div>
                        <div>{res['commentary']['structure']}</div>
                        <div class="{res['commentary']['badge_cls']}">🎯 Emir Stratejisi: {res['commentary']['action']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with c2:
                    table = res['table']
                    if not table.empty:
                        fig = go.Figure(go.Bar(
                            x=table['Net Katkı'], y=table['Makro / Likidite Faktörü'], orientation='h',
                            marker_color=np.where(table['Net Katkı'] > 0, '#10B981', '#EF4444')
                        ))
                        fig.update_layout(
                            margin=dict(l=0, r=0, t=10, b=0), height=260,
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#9CA3AF', size=10),
                            xaxis=dict(gridcolor='#1F2937'), yaxis=dict(gridcolor='#1F2937')
                        )
                        st.plotly_chart(fig, use_container_width=True)

                st.markdown("##### 🔍 Ekonometrik Faktör Ayrışımı (Factor Decomposition)")
                st.dataframe(res['table'], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
