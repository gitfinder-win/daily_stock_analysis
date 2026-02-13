# -*- coding: utf-8 -*-
"""
===================================
期货行情数据获取模块
===================================

基于天勤SDK (TqSdk) 获取期货行情数据

功能：
- 连接天勤模拟/实盘账户
- 获取实时行情
- 获取K线数据
- 获取账户和持仓信息
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from src.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class FuturesQuote:
    """期货行情数据"""
    symbol: str                    # 合约代码 (如 SHFE.au2506)
    name: str = ""                 # 合约名称
    exchange: str = ""             # 交易所
    
    # 价格
    last_price: float = 0.0        # 最新价
    open: float = 0.0              # 开盘价
    high: float = 0.0              # 最高价
    low: float = 0.0               # 最低价
    pre_close: float = 0.0         # 昨收价
    upper_limit: float = 0.0       # 涨停价
    lower_limit: float = 0.0       # 跌停价
    
    # 成交量
    volume: int = 0                # 成交量
    open_interest: int = 0         # 持仓量
    turnover: float = 0.0          # 成交额
    
    # 涨跌
    change: float = 0.0            # 涨跌额
    change_pct: float = 0.0        # 涨跌幅
    
    # 时间
    datetime_str: str = ""         # 行情时间
    
    # 技术指标
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'exchange': self.exchange,
            'last_price': self.last_price,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'pre_close': self.pre_close,
            'change': self.change,
            'change_pct': self.change_pct,
            'volume': self.volume,
            'open_interest': self.open_interest,
            'ma5': self.ma5,
            'ma10': self.ma10,
            'ma20': self.ma20,
            'datetime': self.datetime_str,
        }


@dataclass
class FuturesKline:
    """期货K线数据"""
    symbol: str
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    open_interest: int = 0


@dataclass
class AccountInfo:
    """账户信息"""
    balance: float = 0.0           # 账户权益
    available: float = 0.0         # 可用资金
    margin: float = 0.0            # 占用保证金
    float_profit: float = 0.0      # 浮动盈亏
    close_profit: float = 0.0      # 平仓盈亏
    risk_ratio: float = 0.0        # 风险度


@dataclass
class PositionInfo:
    """持仓信息"""
    symbol: str                    # 合约代码
    exchange: str                  # 交易所
    direction: str                 # 方向 (LONG/SHORT)
    volume: int = 0                # 持仓手数
    cost_price: float = 0.0        # 开仓均价
    last_price: float = 0.0        # 最新价
    float_profit: float = 0.0      # 浮动盈亏
    margin: float = 0.0            # 占用保证金


class FuturesDataProvider:
    """
    期货行情数据提供者
    
    基于天勤SDK获取期货行情数据，支持模拟和实盘模式
    """
    
    # 交易所映射
    EXCHANGE_MAP = {
        'SHFE': '上海期货交易所',
        'DCE': '大连商品交易所',
        'CZCE': '郑州商品交易所',
        'CFFEX': '中国金融期货交易所',
        'INE': '上海国际能源交易中心',
    }
    
    # 常用合约名称映射
    SYMBOL_NAME_MAP = {
        'au': '沪金',
        'ag': '沪银',
        'cu': '沪铜',
        'al': '沪铝',
        'zn': '沪锌',
        'rb': '螺纹钢',
        'hc': '热卷',
        'm': '豆粕',
        'y': '豆油',
        'p': '棕榈油',
        'c': '玉米',
        'CF': '棉花',
        'SR': '白糖',
        'TA': 'PTA',
        'MA': '甲醇',
        'IF': '沪深300',
        'IC': '中证500',
        'IH': '上证50',
        'IM': '中证1000',
    }
    
    def __init__(self, use_sim: bool = True):
        """
        初始化数据提供者
        
        Args:
            use_sim: 是否使用模拟账户（默认True）
        """
        self._api = None
        self._use_sim = use_sim
        self._connected = False
        self._config = get_config()
        
        # 获取天勤账号密码
        self._tq_account = self._config.tq_account
        self._tq_password = self._config.tq_password
        
    def _get_symbol_name(self, symbol: str) -> str:
        """获取合约名称"""
        # 从合约代码提取品种代码 (如 SHFE.au2506 -> au)
        parts = symbol.split('.')
        if len(parts) == 2:
            exchange, contract = parts
            # 提取品种代码 (去除月份数字)
            variety = ''.join(c for c in contract if c.isalpha())
            name = self.SYMBOL_NAME_MAP.get(variety, variety)
            return f"{name}{contract[-4:]}"  # 名称+年月
        return symbol
    
    def connect(self) -> bool:
        """
        连接天勤服务器
        
        Returns:
            是否连接成功
        """
        if self._connected:
            return True
            
        if not self._tq_account or not self._tq_password:
            logger.error("天勤账号或密码未配置，请设置 TQ1/TQ2 或 TQ_ACCOUNT/TQ_PASSWORD 环境变量")
            return False
            
        try:
            from tqsdk import TqApi, TqAuth, TqKq, TqAccount
            
            # 选择连接模式
            if self._use_sim:
                # 模拟账户 - 使用TqKq持久化模拟
                self._api = TqApi(TqKq(), auth=TqAuth(self._tq_account, self._tq_password))
                logger.info("天勤模拟账户连接成功")
            else:
                # 实盘账户
                if not self._config.tq_broker or not self._config.tq_real_account:
                    logger.error("实盘模式需要配置期货公司(TQ_BROKER)和实盘账号(TQ_REAL_ACCOUNT)")
                    return False
                self._api = TqApi(
                    TqAccount(self._config.tq_broker, self._config.tq_real_account, self._config.tq_real_password),
                    auth=TqAuth(self._tq_account, self._tq_password)
                )
                logger.info("天勤实盘账户连接成功")
            
            self._connected = True
            return True
            
        except ImportError:
            logger.error("未安装天勤SDK，请运行: pip install tqsdk")
            return False
        except Exception as e:
            logger.error(f"连接天勤服务器失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self._api:
            try:
                self._api.close()
            except:
                pass
            self._api = None
            self._connected = False
            logger.info("已断开天勤连接")
    
    def get_quote(self, symbol: str) -> Optional[FuturesQuote]:
        """
        获取实时行情
        
        Args:
            symbol: 合约代码 (如 SHFE.au2506)
            
        Returns:
            FuturesQuote 对象
        """
        if not self._ensure_connection():
            return None
            
        try:
            quote = self._api.get_quote(symbol)
            self._api.wait_update()
            
            return FuturesQuote(
                symbol=symbol,
                name=self._get_symbol_name(symbol),
                exchange=symbol.split('.')[0] if '.' in symbol else '',
                last_price=float(quote.last_price) if quote.last_price else 0.0,
                open=float(quote.open) if quote.open else 0.0,
                high=float(quote.highest) if quote.highest else 0.0,
                low=float(quote.lowest) if quote.lowest else 0.0,
                pre_close=float(quote.pre_close) if quote.pre_close else 0.0,
                upper_limit=float(quote.upper_limit) if quote.upper_limit else 0.0,
                lower_limit=float(quote.lower_limit) if quote.lower_limit else 0.0,
                volume=int(quote.volume) if quote.volume else 0,
                open_interest=int(quote.open_interest) if quote.open_interest else 0,
                datetime_str=str(quote.datetime) if quote.datetime else '',
            )
        except Exception as e:
            logger.error(f"获取行情失败 {symbol}: {e}")
            return None
    
    def get_klines(
        self, 
        symbol: str, 
        duration_seconds: int = 86400,
        length: int = 100
    ) -> List[FuturesKline]:
        """
        获取K线数据
        
        Args:
            symbol: 合约代码
            duration_seconds: K线周期（秒），默认日线
            length: K线数量
            
        Returns:
            K线数据列表
        """
        if not self._ensure_connection():
            return []
            
        try:
            klines = self._api.get_kline_serial(symbol, duration_seconds, length)
            self._api.wait_update()
            
            result = []
            for i in range(len(klines)):
                row = klines.iloc[i]
                if row['close'] > 0:  # 过滤无效数据
                    result.append(FuturesKline(
                        symbol=symbol,
                        datetime=str(row.name),
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=int(row['volume']) if row['volume'] else 0,
                        open_interest=int(row['open_oi']) if row['open_oi'] else 0,
                    ))
            
            return result[-length:]  # 返回最近N根K线
            
        except Exception as e:
            logger.error(f"获取K线失败 {symbol}: {e}")
            return []
    
    def get_account(self) -> Optional[AccountInfo]:
        """获取账户信息"""
        if not self._ensure_connection():
            return None
            
        try:
            account = self._api.get_account()
            self._api.wait_update()
            
            return AccountInfo(
                balance=float(account.balance),
                available=float(account.available),
                margin=float(account.margin),
                float_profit=float(account.float_profit),
                close_profit=float(account.close_profit),
                risk_ratio=float(account.risk_ratio) if account.risk_ratio else 0.0,
            )
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return None
    
    def get_positions(self) -> List[PositionInfo]:
        """获取所有持仓"""
        if not self._ensure_connection():
            return []
            
        try:
            positions = self._api.get_position()
            self._api.wait_update()
            
            result = []
            # 遍历所有持仓
            for symbol in dir(positions):
                if symbol.startswith('_'):
                    continue
                pos = getattr(positions, symbol, None)
                if pos and (pos.pos_long > 0 or pos.pos_short > 0):
                    if pos.pos_long > 0:
                        result.append(PositionInfo(
                            symbol=symbol,
                            exchange=symbol.split('.')[0] if '.' in symbol else '',
                            direction='LONG',
                            volume=int(pos.pos_long),
                            cost_price=float(pos.open_price_long),
                            last_price=float(pos.last_price),
                            float_profit=float(pos.float_profit_long),
                            margin=float(pos.margin_long),
                        ))
                    if pos.pos_short > 0:
                        result.append(PositionInfo(
                            symbol=symbol,
                            exchange=symbol.split('.')[0] if '.' in symbol else '',
                            direction='SHORT',
                            volume=int(pos.pos_short),
                            cost_price=float(pos.open_price_short),
                            last_price=float(pos.last_price),
                            float_profit=float(pos.float_profit_short),
                            margin=float(pos.margin_short),
                        ))
            
            return result
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return []
    
    def _ensure_connection(self) -> bool:
        """确保已连接"""
        if not self._connected:
            return self.connect()
        return True
    
    def calculate_ma(self, klines: List[FuturesKline]) -> Dict[str, float]:
        """计算均线"""
        if len(klines) < 20:
            return {'ma5': 0, 'ma10': 0, 'ma20': 0}
        
        closes = [k.close for k in klines]
        
        return {
            'ma5': sum(closes[-5:]) / 5,
            'ma10': sum(closes[-10:]) / 10,
            'ma20': sum(closes[-20:]) / 20,
        }
    
    def get_analysis_context(self, symbol: str) -> Dict[str, Any]:
        """
        获取分析上下文（用于AI分析）
        
        Args:
            symbol: 合约代码
            
        Returns:
            包含行情、K线、技术指标的上下文
        """
        # 获取实时行情
        quote = self.get_quote(symbol)
        if not quote:
            return {'error': f'无法获取 {symbol} 行情数据'}
        
        # 获取K线数据
        klines = self.get_klines(symbol, 86400, 100)
        
        # 计算均线
        ma_data = self.calculate_ma(klines) if klines else {}
        
        # 计算涨跌
        if quote.pre_close > 0:
            quote.change = quote.last_price - quote.pre_close
            quote.change_pct = (quote.change / quote.pre_close) * 100
        
        # 计算技术指标
        trend_status = self._analyze_trend(klines, quote, ma_data)
        
        return {
            'symbol': symbol,
            'name': quote.name,
            'exchange': quote.exchange,
            'datetime': quote.datetime_str,
            'quote': quote.to_dict(),
            'klines': [
                {
                    'datetime': k.datetime,
                    'open': k.open,
                    'high': k.high,
                    'low': k.low,
                    'close': k.close,
                    'volume': k.volume,
                    'open_interest': k.open_interest,
                } for k in klines[-30:]  # 最近30根K线
            ],
            'ma': ma_data,
            'trend': trend_status,
            'volume_analysis': self._analyze_volume(klines),
        }
    
    def _analyze_trend(self, klines: List[FuturesKline], quote: FuturesQuote, ma: Dict) -> Dict:
        """分析趋势"""
        if not klines or not ma:
            return {'status': 'unknown', 'signal': 'unknown'}
        
        last_close = quote.last_price or klines[-1].close
        ma5 = ma.get('ma5', 0)
        ma10 = ma.get('ma10', 0)
        ma20 = ma.get('ma20', 0)
        
        # 均线排列
        if ma5 > ma10 > ma20:
            alignment = '多头排列'
            trend = 'up'
        elif ma5 < ma10 < ma20:
            alignment = '空头排列'
            trend = 'down'
        else:
            alignment = '缠绕震荡'
            trend = 'sideways'
        
        # 乖离率
        bias_ma5 = (last_close - ma5) / ma5 * 100 if ma5 > 0 else 0
        
        # 信号判断
        if trend == 'up' and bias_ma5 < 3:
            signal = 'buy'
            signal_desc = '多头趋势，乖离率安全，可考虑买入'
        elif trend == 'up' and bias_ma5 >= 5:
            signal = 'hold'
            signal_desc = '多头趋势但乖离率过高，不宜追高'
        elif trend == 'down':
            signal = 'sell'
            signal_desc = '空头趋势，建议观望或做空'
        else:
            signal = 'wait'
            signal_desc = '趋势不明，建议观望'
        
        return {
            'status': trend,
            'alignment': alignment,
            'bias_ma5': round(bias_ma5, 2),
            'signal': signal,
            'signal_desc': signal_desc,
            'ma5': round(ma5, 2),
            'ma10': round(ma10, 2),
            'ma20': round(ma20, 2),
        }
    
    def _analyze_volume(self, klines: List[FuturesKline]) -> Dict:
        """分析成交量"""
        if len(klines) < 5:
            return {'status': 'unknown'}
        
        recent_vol = [k.volume for k in klines[-5:]]
        avg_vol = sum(recent_vol) / 5
        
        last_vol = klines[-1].volume
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1
        
        if vol_ratio > 2:
            status = '放量'
        elif vol_ratio > 1.2:
            status = '温和放量'
        elif vol_ratio < 0.5:
            status = '缩量'
        else:
            status = '平量'
        
        return {
            'status': status,
            'volume_ratio': round(vol_ratio, 2),
            'avg_volume': int(avg_vol),
            'last_volume': last_vol,
        }
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# 便捷函数
def get_futures_data_provider(use_sim: bool = True) -> FuturesDataProvider:
    """获取期货数据提供者"""
    return FuturesDataProvider(use_sim=use_sim)
