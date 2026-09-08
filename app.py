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
st.set_page_config(page_title="TIER-1 MULTI-API QUANT TERMINAL (v200-FULL)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { font-family: 'Courier New', monospace; font-size: 20px; }
    h2, h3 { color: #ECEFF1; font-size: 14px; }
    .regime-card { padding: 14px 20px; border-radius: 6px; font-weight: bold; font-size: 13px; margin-bottom: 15px; border-left: 6px solid; }
    .regime-bull { background-color: #002B22; color: #00E676; border-color: #00E676; }
    .regime-bear { background-color: #330000; color: #FF1744; border-color: #FF1744; }
    .regime-crisis { background-color: #4A0000; color: #FF5252; border-color: #FF1744; animation: blink 1.5s infinite; }
    .regime-neutral { background-color: #262000; color: #FFB300; border-color: #FFB300; }
    .badge-lock { background-color: #B71C1C; color: #FFFFFF; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-bull { background-color: #004D40; color: #00E676; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-bear { background-color: #4A148C; color: #FF1744; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .action-box { background-color: #121824; border: 1px solid #2A364F; border-radius: 6px; padding: 12px; margin-top: 10px; font-size: 12px; line-height: 1.5; }
    </style>
    """, unsafe_allow_html=True)

st_autorefresh(interval=60000, limit=None, key="deep_quant_refresh")

# ==========================================
# 2. ÇOKLU API VERİ TOPLAMA MOTORU (FRED + BINANCE + DEFILLAMA + YAHOO)
# ==========================================
class MultiApiDataEngine:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    # 1. ABD MAKRO LİGİDİTESİ (FRED API / Direct Public Feed)
    def fetch_fred_series(self, series_id):
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        try:
            df = pd.read_csv(url)
            df['DATE'] = pd.to_datetime(df['DATE'])
            df.set_index('DATE', inplace=True)
            df[series_id] = pd.to_numeric(df[series_id], errors='coerce')
            return df[series_id].ffill()
        except Exception:
            return pd.Series(dtype=float)

    def fetch_us_net_liquidity(self):
        walcl = self.fetch_fred_series('WALCL')       # Fed Bilanço Toplamı
        wtregen = self.fetch_fred_series('WTREGEN')   # Hazine Genel Hesabı (TGA)
        rrp = self.fetch_fred_series('RRPONTSYD')     # Ters Repo
        tips = self.fetch_fred_series('DFII10')       # 10Y Reel Faiz (TIPS)
        hy_spread = self.fetch_fred_series('BAMLH0A0HYM2') # High Yield Spread

        df = pd.DataFrame({'WALCL': walcl, 'WTREGEN': wtregen, 'RRP': rrp, 'TIPS': tips, 'HY_SPREAD': hy_spread}).ffill().dropna()
        df['NET_USD_LIQUIDITY'] = df['WALCL'] - df['WTREGEN'] - df['RRP']
        return df

    # 2. KRİPTO GERÇEK ORDER FLOW VE ON-CHAIN (BINANCE + DEFILLAMA)
    def fetch_binance_taker_ratio(self, symbol="BTCUSDT"):
        url = f"https://fapi.binance.com/futures/data/takerlongshortRatio?symbol={symbol}&period=15m&limit=48"
        try:
            r = self.session.get(url, headers=self.headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                df = pd.DataFrame(data)
                df['buySellRatio'] = df['buySellRatio'].astype(float)
                return df['buySellRatio'].iloc[-1], df['buySellRatio'].pct_change().dropna()
        except Exception:
            pass
        return 1.0, pd.Series(dtype=float)

    def fetch_binance_open_interest(self, symbol="BTCUSDT"):
        url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
        try:
            r = self.session.get(url, headers=self.headers, timeout=5)
            if r.status_code == 200:
                return float(r.json()['openInterest'])
        except Exception:
            pass
        return 0.0

    def fetch_stablecoin_supply_delta(self):
        url = "https://stablecoins.llama.fi/stablecoins?includePrices=true"
        try:
            r = self.session.get(url, headers=self.headers, timeout=5)
            if r.status_code == 200:
                pegged = r.json()['peggedAssets']
                usdt_mcap = next(item['circulating']['peggedUSD'] for item in pegged if item['symbol'] == 'USDT')
                usdc_mcap = next(item['circulating']['peggedUSD'] for item in pegged if item['symbol'] == 'USDC')
                return usdt_mcap + usdc_mcap
        except Exception:
            pass
        return 0.0

    # 3. KÜRESEL PİYASA FİYAT IZGARASI (YAHOO FINANCE API)
    def fetch_yahoo_grid(self):
        symbols = {
            'SPX': 'ES=F', 'NQ': 'NQ=F', 'XAU': 'GC=F', 'XAG': 'SI=F',
            'COPPER': 'HG=F', 'OIL': 'CL=F', 'EUR': 'EURUSD=X', 'JPY': 'USDJPY=X',
            'BTC': 'BTC-USD', 'ETH': 'ETH-USD', 'TNX': '^TNX', 'VIX': '^VIX', 'XME': 'XME'
        }
        data = {}
        for alias, sym in symbols.items():
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5d&interval=15m"
            try:
                r = self.session.get(url, headers=self.headers, timeout=4)
                if r.status_code == 200:
                    res = r.json()['chart']['result'][0]
                    s = pd.Series(res['indicators']['quote'][0]['close'], index=pd.to_datetime(res['timestamp'], unit='s'))
                    data[alias] = s.dropna()
            except Exception:
                pass
        return pd.DataFrame(data).ffill().bfill()

# ==========================================
# 3. HESAPLAMA MOTORU VE ANOMALİ SİSTEMİ
# ==========================================
class DynamicQuantProcessor:
    def compute_z_score(self, series, window=32):
        if series is None or len(series) < 5:
            return 0.0
        pct = series.pct_change().dropna() if isinstance(series, pd.Series) else pd.Series(series).pct_change().dropna()
        if pct.empty:
            return 0.0
        mean = pct.rolling(window=window, min_periods=3).mean().iloc[-1]
        std = pct.rolling(window=window, min_periods=3).std().iloc[-1]
        std = 1e-6 if std == 0 or np.isnan(std) else std
        curr = pct.iloc[-1]
        return float(np.clip((curr - mean) / std, -3.5, 3.5))

    def sigmoid_transform(self, z, k=1.5):
        return float(np.tanh(z / k))

    def execute_layer_analysis(self, us_macro_df, binance_taker, crypto_oi, market_grid):
        # Layer 1 & 2: ABD ve Küresel Makro
        net_liq_z = self.compute_z_score(us_macro_df['NET_USD_LIQUIDITY']) if not us_macro_df.empty else 0.0
        tips_yield_z = self.compute_z_score(us_macro_df['TIPS']) if not us_macro_df.empty else 0.0
        hy_spread_z = self.compute_z_score(us_macro_df['HY_SPREAD']) if not us_macro_df.empty else 0.0
        vix_z = self.compute_z_score(market_grid['VIX']) if 'VIX' in market_grid else 0.0

        # Anomali Engine (Systemic Stress Detection)
        stress_matrix = np.array([hy_spread_z, tips_yield_z, vix_z, -net_liq_z])
        anomali_index = float(np.linalg.norm(stress_matrix) / 2.0)
        is_systemic_crisis = anomali_index > 1.80 or hy_spread_z > 2.0 or vix_z > 2.2

        # Layer 3: Varlık Özgün Mikro Matrisleri
        
        # A) Kripto Mikro Engine (Order Flow Driven)
        taker_ratio_val, taker_pct_series = binance_taker
        taker_z = self.compute_z_score(taker_pct_series)
        btc_z = self.compute_z_score(market_grid['BTC']) if 'BTC' in market_grid else 0.0
        eth_btc_ratio = market_grid['ETH'] / market_grid['BTC'] if 'ETH' in market_grid and 'BTC' in market_grid else None
        eth_btc_z = self.compute_z_score(eth_btc_ratio) if eth_btc_ratio is not None else 0.0

        crypto_factors = {
            'Binance Taker Buy/Sell Volume Ratio': {'z': taker_z, 'dir': 1.0, 'w': 3.0},
            'BTC Pure Price Momentum': {'z': btc_z, 'dir': 1.0, 'w': 2.0},
            'ETH/BTC Beta Ratio (Leverage Appetite)': {'z': eth_btc_z, 'dir': 1.0, 'w': 1.5},
            'US Net Liquidity (FRED)': {'z': net_liq_z, 'dir': 1.0, 'w': 2.0},
            'HY Credit Spread Stress': {'z': hy_spread_z, 'dir': -1.0, 'w': 1.8} # Ters
        }

        # B) Gümüş (XAG) Mikro Engine (Physical & Industrial Drivers)
        xag_z = self.compute_z_score(market_grid['XAG']) if 'XAG' in market_grid else 0.0
        copper_gold = market_grid['COPPER'] / market_grid['XAU'] if 'COPPER' in market_grid and 'XAU' in market_grid else None
        copper_gold_z = self.compute_z_score(copper_gold) if copper_gold is not None else 0.0
        xme_z = self.compute_z_score(market_grid['XME']) if 'XME' in market_grid else 0.0

        xag_factors = {
            'XAG Pure Momentum': {'z': xag_z, 'dir': 1.0, 'w': 2.5},
            'Copper/Gold Ratio (Sanayi Talebi)': {'z': copper_gold_z, 'dir': 1.0, 'w': 2.2},
            'XME Mining Equity Flow': {'z': xme_z, 'dir': 1.0, 'w': 1.5},
            '10Y TIPS Real Yield (Reel Faiz)': {'z': tips_yield_z, 'dir': -1.0, 'w': 2.0}, # Ters
            'DXY FX Strain (Dolar Gücü)': {'z': self.compute_z_score(-market_grid['EUR']) if 'EUR' in market_grid else 0.0, 'dir': -1.0, 'w': 1.5} # Ters
        }

        def process_factors(factors, is_crisis, asset_name):
            tot_score = 0.0
            tot_w = 0.0
            rows = []
            for name, d in factors.items():
                eff = self.sigmoid_transform(d['z']) * d['dir']
                w = d['w'] * (2.5 if is_crisis and d['dir'] < 0 else 1.0)
                contrib = eff * w
                tot_score += contrib
                tot_w += w
                rows.append({'Gösterge': name, 'Z-Score': round(d['z'], 2), 'Yön': 'Doğrudan (+)' if d['dir'] > 0 else 'Ters (-)', 'Net Katkı': round(contrib, 3)})

            score = (tot_score / (tot_w + 1e-6)) * 100.0
            if is_crisis and asset_name in ['CRYPTO', 'XAG', 'SPX', 'NQ']:
                score = min(score, -70.0) # Short Lock

            return float(np.clip(score, -100.0, 100.0)), pd.DataFrame(rows).sort_values('Net Katkı', ascending=False)

        crypto_score, crypto_df = process_factors(crypto_factors, is_systemic_crisis, 'CRYPTO')
        xag_score, xag_df = process_factors(xag_factors, is_systemic_crisis, 'XAG')

        return {
            'anomali_index': anomali_index,
            'is_crisis': is_systemic_crisis,
            'net_liq_z': net_liq_z,
            'crypto': {'score': crypto_score, 'df': crypto_df, 'taker_val': taker_ratio_val},
            'xag': {'score': xag_score, 'df': xag_df}
        }

# ==========================================
# 4. DASHBOARD ARAYÜZÜ
# ==========================================
st.title("🏛️ TIER-1 MULTI-API QUANT ENGINE (v200-FULL)")
st.caption("FRED Net Liquidity | Binance Futures Taker Order Flow | DefiLlama | Anomali Short Lock")

data_engine = MultiApiDataEngine()
processor = DynamicQuantProcessor()

try:
    with st.spinner("FRED, Binance Order Flow ve Küresel Izgara Verisi Çekiliyor..."):
        us_macro = data_engine.fetch_us_net_liquidity()
        binance_taker = data_engine.fetch_binance_taker_ratio("BTCUSDT")
        crypto_oi = data_engine.fetch_binance_open_interest("BTCUSDT")
        grid = data_engine.fetch_yahoo_grid()

    res = processor.execute_layer_analysis(us_macro, binance_taker, crypto_oi, grid)

    # Rejim Alanı
    if res['is_crisis']:
        st.markdown(f"""
        <div class="regime-card regime-crisis">
            🚨 SİSTEMİK ANOMALİ VE ŞOK ALARMI (Anomali Skoru: {res['anomali_index']:.2f})<br>
            <span style="font-weight:normal; font-size:11px;">High Yield Spread veya Volatilite Z > 2.0 üzerine çıktı. Long filtreleri kapatıldı, Short kilit devreye sokuldu.</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="regime-card regime-bull">
            🌐 DİNAMİK MAKRO REJİM: AKTİF DENGELİ SİSTEM (Anomali Skoru: {res['anomali_index']:.2f})<br>
            <span style="font-weight:normal; font-size:11px;">FRED Net Dolar Likiditesi Z-Score: {res['net_liq_z']:.2f} | Binance Taker Volume Ratio: {res['crypto']['taker_val']:.3f}</span>
        </div>
        """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["KRİPTO (Order Flow Engine)", "GÜMÜŞ (XAG Physical & Industrial)"])

    with tab1:
        c_score = res['crypto']['score']
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("### Kripto Mikro Yön Skoru")
            col_code = "#00E676" if c_score > 18 else ("#FF1744" if c_score < -18 else "#FFB300")
            if c_score <= -70: col_code = "#B71C1C"
            st.markdown(f"<h1 style='color: {col_code}; font-size: 50px;'>{c_score:.1f}</h1>", unsafe_allow_html=True)
            if c_score <= -70:
                st.markdown('<span class="badge-lock">🚨 SHORT KİLİTLENDİ (ANOMALİ)</span>', unsafe_allow_html=True)
            elif c_score > 18:
                st.markdown('<span class="badge-bull">🚀 LONG POZİSYON TAŞI</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge-bear">🩸 SHORT / SATIŞ BASKISI</span>', unsafe_allow_html=True)

            st.markdown(f"""
            <div class="action-box">
                <b>Canlı Binance Akış Verileri:</b><br>
                • BTC Taker Buy/Sell Ratio: <b>{res['crypto']['taker_val']:.3f}</b><br>
                • BTC Open Interest (Açık Poz.): <b>${crypto_oi/1e6:.1f}M</b>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            fig = go.Figure(go.Bar(
                x=res['crypto']['df']['Net Katkı'], y=res['crypto']['df']['Gösterge'], orientation='h',
                marker_color=np.where(res['crypto']['df']['Net Katkı'] > 0, '#00E676', '#FF1744')
            ))
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=220, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(res['crypto']['df'], use_container_width=True, hide_index=True)

    with tab2:
        x_score = res['xag']['score']
        xc1, xc2 = st.columns([1, 2])
        with xc1:
            st.markdown("### Gümüş Mikro Yön Skoru")
            x_col = "#00E676" if x_score > 18 else ("#FF1744" if x_score < -18 else "#FFB300")
            st.markdown(f"<h1 style='color: {x_col}; font-size: 50px;'>{x_score:.1f}</h1>", unsafe_allow_html=True)
            if x_score > 18:
                st.markdown('<span class="badge-bull">🚀 SANAYİ TALEBİ / LONG</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge-bear">🩸 REEL FAİZ BASKISI / SHORT</span>', unsafe_allow_html=True)

        with xc2:
            fig_x = go.Figure(go.Bar(
                x=res['xag']['df']['Net Katkı'], y=res['xag']['df']['Gösterge'], orientation='h',
                marker_color=np.where(res['xag']['df']['Net Katkı'] > 0, '#00E676', '#FF1744')
            ))
            fig_x.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=220, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
            st.plotly_chart(fig_x, use_container_width=True)

        st.dataframe(res['xag']['df'], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Sistem Bağlantı / Hesaplama Hatası: {str(e)}")
