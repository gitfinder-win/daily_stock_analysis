# -*- coding: utf-8 -*-
"""
===================================
期货分析模块
===================================

基于天勤SDK (TqSdk) 的期货分析和交易模块

功能：
- 期货行情数据获取
- 期货技术分析
- AI智能分析
- 自动交易执行

使用方式：
    from src.futures import FuturesAnalyzer, FuturesTrader
"""

from .data_provider import FuturesDataProvider
from .analyzer import FuturesAnalyzer, FuturesAnalysisResult
from .trader import FuturesTrader, TradeSignal, TradeResult

__all__ = [
    'FuturesDataProvider',
    'FuturesAnalyzer',
    'FuturesAnalysisResult',
    'FuturesTrader',
    'TradeSignal',
    'TradeResult',
]
