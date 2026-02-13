# -*- coding: utf-8 -*-
"""
===================================
期货交易执行模块
===================================

基于天勤SDK的期货交易执行

功能：
- 接收分析结果执行交易
- 风险控制
- 仓位管理
- 交易记录
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from src.config import get_config
from .data_provider import FuturesDataProvider, AccountInfo, PositionInfo
from .analyzer import FuturesAnalysisResult

logger = logging.getLogger(__name__)


class TradeDirection(Enum):
    """交易方向"""
    LONG = "LONG"       # 做多
    SHORT = "SHORT"     # 做空
    CLOSE = "CLOSE"     # 平仓


@dataclass
class TradeSignal:
    """交易信号"""
    symbol: str                    # 合约代码
    direction: TradeDirection      # 方向
    volume: int = 1                # 手数
    price: Optional[float] = None  # 价格（None为市价）
    stop_loss: Optional[float] = None  # 止损价
    take_profit: Optional[float] = None # 止盈价
    reason: str = ""               # 交易理由
    source: str = "AI"             # 信号来源
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'direction': self.direction.value,
            'volume': self.volume,
            'price': self.price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'reason': self.reason,
            'source': self.source,
        }


@dataclass
class TradeResult:
    """交易结果"""
    success: bool
    symbol: str
    direction: str
    volume: int
    price: float = 0.0
    order_id: str = ""
    message: str = ""
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'symbol': self.symbol,
            'direction': self.direction,
            'volume': self.volume,
            'price': self.price,
            'order_id': self.order_id,
            'message': self.message,
            'timestamp': self.timestamp,
        }


class FuturesTrader:
    """
    期货交易执行器
    
    负责根据分析结果执行交易，包含风险控制逻辑
    """
    
    def __init__(self, use_sim: bool = True):
        """
        初始化交易执行器
        
        Args:
            use_sim: 是否使用模拟账户（默认True，安全第一）
        """
        self._config = get_config()
        self._provider = FuturesDataProvider(use_sim=use_sim)
        self._connected = False
        self._trade_history: List[Dict] = []
        
    def connect(self) -> bool:
        """连接交易接口"""
        if self._connected:
            return True
        
        if self._provider.connect():
            self._connected = True
            logger.info("交易执行器连接成功")
            return True
        return False
    
    def disconnect(self):
        """断开连接"""
        self._provider.disconnect()
        self._connected = False
    
    def execute_signal(self, signal: TradeSignal, dry_run: bool = False) -> TradeResult:
        """
        执行交易信号
        
        Args:
            signal: 交易信号
            dry_run: 是否模拟运行（不实际下单）
            
        Returns:
            TradeResult 交易结果
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 检查连接
        if not dry_run and not self._ensure_connection():
            return TradeResult(
                success=False,
                symbol=signal.symbol,
                direction=signal.direction.value,
                volume=signal.volume,
                message="交易接口未连接",
                timestamp=timestamp,
            )
        
        # 风险检查
        risk_check = self._risk_check(signal)
        if not risk_check['passed']:
            return TradeResult(
                success=False,
                symbol=signal.symbol,
                direction=signal.direction.value,
                volume=signal.volume,
                message=f"风险检查未通过: {risk_check['reason']}",
                timestamp=timestamp,
            )
        
        # 模拟运行
        if dry_run:
            logger.info(f"[模拟交易] {signal.direction.value} {signal.symbol} x{signal.volume} @ {signal.price or '市价'}")
            return TradeResult(
                success=True,
                symbol=signal.symbol,
                direction=signal.direction.value,
                volume=signal.volume,
                price=signal.price or 0,
                message="模拟交易成功",
                timestamp=timestamp,
            )
        
        # 实际下单
        try:
            return self._place_order(signal, timestamp)
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return TradeResult(
                success=False,
                symbol=signal.symbol,
                direction=signal.direction.value,
                volume=signal.volume,
                message=f"下单失败: {e}",
                timestamp=timestamp,
            )
    
    def execute_analysis(self, analysis: FuturesAnalysisResult, dry_run: bool = False) -> TradeResult:
        """
        根据分析结果执行交易
        
        Args:
            analysis: 分析结果
            dry_run: 是否模拟运行
            
        Returns:
            TradeResult
        """
        # 不交易的情况
        if analysis.direction == 'WAIT' or analysis.operation_advice == '观望':
            return TradeResult(
                success=True,
                symbol=analysis.symbol,
                direction='WAIT',
                volume=0,
                message=f"建议观望: {analysis.analysis_summary[:100]}",
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            )
        
        # 构建交易信号
        direction = TradeDirection.LONG if analysis.direction == 'LONG' else TradeDirection.SHORT
        
        signal = TradeSignal(
            symbol=analysis.symbol,
            direction=direction,
            volume=analysis.position_size or 1,
            price=analysis.entry_price if analysis.entry_price > 0 else None,
            stop_loss=analysis.stop_loss,
            take_profit=analysis.take_profit,
            reason=f"AI分析: {analysis.operation_advice} (评分: {analysis.sentiment_score})",
            source="AI",
        )
        
        return self.execute_signal(signal, dry_run)
    
    def close_position(
        self, 
        symbol: str, 
        direction: str = "ALL",
        volume: int = 0,
        dry_run: bool = False
    ) -> TradeResult:
        """
        平仓
        
        Args:
            symbol: 合约代码
            direction: 平仓方向 (ALL/LONG/SHORT)
            volume: 平仓手数（0表示全部）
            dry_run: 是否模拟
            
        Returns:
            TradeResult
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if not dry_run and not self._ensure_connection():
            return TradeResult(
                success=False,
                symbol=symbol,
                direction='CLOSE',
                volume=volume,
                message="交易接口未连接",
                timestamp=timestamp,
            )
        
        # 获取当前持仓
        positions = self._provider.get_positions()
        target_pos = None
        
        for pos in positions:
            if pos.symbol == symbol:
                if direction == "ALL" or pos.direction == direction:
                    target_pos = pos
                    break
        
        if not target_pos:
            return TradeResult(
                success=False,
                symbol=symbol,
                direction='CLOSE',
                volume=0,
                message="没有找到对应持仓",
                timestamp=timestamp,
            )
        
        close_volume = volume if volume > 0 else target_pos.volume
        
        if dry_run:
            logger.info(f"[模拟平仓] {symbol} {target_pos.direction} {close_volume}手")
            return TradeResult(
                success=True,
                symbol=symbol,
                direction='CLOSE',
                volume=close_volume,
                message="模拟平仓成功",
                timestamp=timestamp,
            )
        
        # 实际平仓
        try:
            return self._close_order(symbol, target_pos.direction, close_volume, timestamp)
        except Exception as e:
            return TradeResult(
                success=False,
                symbol=symbol,
                direction='CLOSE',
                volume=close_volume,
                message=f"平仓失败: {e}",
                timestamp=timestamp,
            )
    
    def _risk_check(self, signal: TradeSignal) -> Dict[str, Any]:
        """风险检查"""
        # 检查最大持仓
        max_pos = self._config.futures_max_position
        if signal.volume > max_pos:
            return {
                'passed': False,
                'reason': f'超过最大持仓限制 ({signal.volume} > {max_pos})'
            }
        
        # 检查账户余额
        account = self._provider.get_account()
        if account and account.available < signal.volume * 10000:  # 简单估算
            return {
                'passed': False,
                'reason': f'可用资金不足 (可用: {account.available:.2f})'
            }
        
        # 检查是否启用自动交易
        if not self._config.futures_auto_trade:
            return {
                'passed': False,
                'reason': '自动交易未启用 (设置 FUTURES_AUTO_TRADE=true)'
            }
        
        return {'passed': True, 'reason': ''}
    
    def _place_order(self, signal: TradeSignal, timestamp: str) -> TradeResult:
        """下单"""
        try:
            from tqsdk import TqApi
            
            # 确定开仓方向
            if signal.direction == TradeDirection.LONG:
                offset = "OPEN"
                direction = "BUY"
            else:
                offset = "OPEN"
                direction = "SELL"
            
            # 下单
            order = self._provider._api.insert_order(
                symbol=signal.symbol,
                direction=direction,
                offset=offset,
                volume=signal.volume,
                limit_price=signal.price,
            )
            
            # 等待成交
            while True:
                self._provider._api.wait_update()
                if order.status == "FINISHED":
                    break
            
            result = TradeResult(
                success=True,
                symbol=signal.symbol,
                direction=signal.direction.value,
                volume=signal.volume,
                price=float(order.trade_price) if order.trade_price else 0,
                order_id=str(order.order_id),
                message="下单成功",
                timestamp=timestamp,
            )
            
            # 记录交易
            self._trade_history.append(result.to_dict())
            
            # 设置止损止盈（如果配置了）
            if signal.stop_loss or signal.take_profit:
                self._set_stop_loss_take_profit(signal)
            
            return result
            
        except Exception as e:
            raise Exception(f"下单异常: {e}")
    
    def _close_order(
        self, 
        symbol: str, 
        pos_direction: str, 
        volume: int, 
        timestamp: str
    ) -> TradeResult:
        """平仓"""
        try:
            # 平仓方向与持仓相反
            if pos_direction == "LONG":
                direction = "SELL"
                offset = "CLOSE"
            else:
                direction = "BUY"
                offset = "CLOSE"
            
            order = self._provider._api.insert_order(
                symbol=symbol,
                direction=direction,
                offset=offset,
                volume=volume,
            )
            
            while True:
                self._provider._api.wait_update()
                if order.status == "FINISHED":
                    break
            
            return TradeResult(
                success=True,
                symbol=symbol,
                direction='CLOSE',
                volume=volume,
                price=float(order.trade_price) if order.trade_price else 0,
                order_id=str(order.order_id),
                message="平仓成功",
                timestamp=timestamp,
            )
            
        except Exception as e:
            raise Exception(f"平仓异常: {e}")
    
    def _set_stop_loss_take_profit(self, signal: TradeSignal):
        """设置止损止盈（使用TargetPosTask自动管理）"""
        # TODO: 实现止损止盈逻辑
        logger.info(f"止损止盈设置: SL={signal.stop_loss}, TP={signal.take_profit}")
    
    def _ensure_connection(self) -> bool:
        """确保连接"""
        if not self._connected:
            return self.connect()
        return True
    
    def get_account_info(self) -> Optional[AccountInfo]:
        """获取账户信息"""
        if self._ensure_connection():
            return self._provider.get_account()
        return None
    
    def get_positions(self) -> List[PositionInfo]:
        """获取持仓"""
        if self._ensure_connection():
            return self._provider.get_positions()
        return []
    
    def get_trade_history(self) -> List[Dict]:
        """获取交易历史"""
        return self._trade_history.copy()
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def get_futures_trader(use_sim: bool = True) -> FuturesTrader:
    """获取期货交易执行器"""
    return FuturesTrader(use_sim=use_sim)
