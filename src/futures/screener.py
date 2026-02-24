# -*- coding: utf-8 -*-
"""
===================================
期货筛选排名模块
===================================

功能：
- 获取所有主力期货合约
- 对期货进行分析评分
- 筛选出排名靠前的期货标的
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FuturesRanking:
    """期货排名结果"""
    symbol: str                    # 合约代码
    name: str                      # 合约名称
    exchange: str                  # 交易所
    
    # 评分维度
    trend_score: float = 0.0       # 趋势评分 (0-100)
    volume_score: float = 0.0      # 量能评分 (0-100)
    sentiment_score: float = 0.0   # AI情感评分 (0-100)
    total_score: float = 0.0       # 综合评分 (0-100)
    
    # 交易建议
    direction: str = 'WAIT'        # LONG/SHORT/WAIT
    operation_advice: str = ''     # 操作建议
    entry_price: float = 0.0       # 入场价
    stop_loss: float = 0.0         # 止损价
    take_profit: float = 0.0       # 止盈价
    
    # 分析结果
    analysis_summary: str = ''     # 分析摘要
    confidence_level: str = '低'   # 置信度
    
    # 排名
    rank: int = 0                  # 排名
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'exchange': self.exchange,
            'trend_score': self.trend_score,
            'volume_score': self.volume_score,
            'sentiment_score': self.sentiment_score,
            'total_score': self.total_score,
            'direction': self.direction,
            'operation_advice': self.operation_advice,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'rank': self.rank,
        }


class FuturesScreener:
    """
    期货筛选器
    
    获取所有可交易期货，进行分析评分，筛选出最优标的
    """
    
    # 主力合约品种列表（主流品种）
    MAIN_VARIETIES = [
        # 上期所
        ('SHFE', 'au'),   # 沪金
        ('SHFE', 'ag'),   # 沪银
        ('SHFE', 'cu'),   # 沪铜
        ('SHFE', 'al'),   # 沪铝
        ('SHFE', 'zn'),   # 沪锌
        ('SHFE', 'rb'),   # 螺纹钢
        ('SHFE', 'hc'),   # 热卷
        ('SHFE', 'ni'),   # 镍
        ('SHFE', 'sn'),   # 锡
        ('SHFE', 'pb'),   # 铅
        ('SHFE', 'ss'),   # 不锈钢
        ('SHFE', 'sp'),   # 纸浆
        ('SHFE', 'ru'),   # 橡胶
        ('SHFE', 'fu'),   # 燃油
        ('SHFE', 'bu'),   # 沥青
        ('SHFE', 'ao'),   # 氧化铝
        
        # 大商所
        ('DCE', 'm'),     # 豆粕
        ('DCE', 'y'),     # 豆油
        ('DCE', 'p'),     # 棕榈油
        ('DCE', 'c'),     # 玉米
        ('DCE', 'a'),     # 豆一
        ('DCE', 'b'),     # 豆二
        ('DCE', 'jd'),    # 鸡蛋
        ('DCE', 'l'),     # 塑料
        ('DCE', 'v'),     # PVC
        ('DCE', 'pp'),    # PP
        ('DCE', 'j'),     # 焦炭
        ('DCE', 'jm'),    # 焦煤
        ('DCE', 'i'),     # 铁矿石
        ('DCE', 'fb'),    # 纤维板
        ('DCE', 'bb'),    # 胶合板
        ('DCE', 'pg'),    # 液化石油气
        ('DCE', 'eg'),    # 乙二醇
        ('DCE', 'rr'),    # 粳米
        ('DCE', 'eb'),    # 苯乙烯
        
        # 郑商所
        ('CZCE', 'CF'),   # 棉花
        ('CZCE', 'SR'),   # 白糖
        ('CZCE', 'TA'),   # PTA
        ('CZCE', 'MA'),   # 甲醇
        ('CZCE', 'FG'),   # 玻璃
        ('CZCE', 'OI'),   # 菜油
        ('CZCE', 'RM'),   # 菜粕
        ('CZCE', 'ZC'),   # 动力煤
        ('CZCE', 'SF'),   # 硅铁
        ('CZCE', 'SM'),   # 锰硅
        ('CZCE', 'AP'),   # 苹果
        ('CZCE', 'CJ'),   # 红枣
        ('CZCE', 'UR'),   # 尿素
        ('CZCE', 'SA'),   # 纯碱
        ('CZCE', 'PF'),   # 短纤
        ('CZCE', 'PK'),   # 花生
        
        # 中金所
        ('CFFEX', 'IF'),  # 沪深300
        ('CFFEX', 'IC'),  # 中证500
        ('CFFEX', 'IH'),  # 上证50
        ('CFFEX', 'IM'),  # 中证1000
        
        # 能源中心
        ('INE', 'sc'),    # 原油
        ('INE', 'lu'),    # 低硫燃油
        ('INE', 'nr'),    # 20号胶
        ('INE', 'bc'),    # 国际铜
    ]
    
    # 交易所映射
    EXCHANGE_NAMES = {
        'SHFE': '上期所',
        'DCE': '大商所',
        'CZCE': '郑商所',
        'CFFEX': '中金所',
        'INE': '能源中心',
    }
    
    def __init__(self, provider=None, analyzer=None):
        """
        初始化筛选器
        
        Args:
            provider: FuturesDataProvider 实例
            analyzer: FuturesAnalyzer 实例
        """
        self.provider = provider
        self.analyzer = analyzer
        
    def get_main_contracts(self, year: int = None) -> List[str]:
        """
        获取所有主力合约代码
        
        天勤SDK主力合约格式: KQ.m@交易所.品种
        例如: KQ.m@SHFE.au (沪金主力), KQ.m@DCE.m (豆粕主力)
        
        Args:
            year: 年份，默认当前年份（主力合约不需要年月）
            
        Returns:
            主力合约代码列表
        """
        contracts = []
        
        for exchange, variety in self.MAIN_VARIETIES:
            # 天勤主力合约格式: KQ.m@交易所.品种
            # KQ.m 表示主力合约
            main_symbol = f"KQ.m@{exchange}.{variety}"
            contracts.append(main_symbol)
            
        return contracts
    
    def get_active_contracts(self) -> List[str]:
        """
        获取活跃合约代码列表
        
        使用主力合约标记获取
        
        Returns:
            活跃合约代码列表
        """
        return self.get_main_contracts()
    
    def screen(
        self,
        top_n: int = 3,
        min_score: float = 50.0,
        only_tradeable: bool = True,
        varieties: List[str] = None,
    ) -> List[FuturesRanking]:
        """
        筛选期货合约
        
        Args:
            top_n: 返回前N个
            min_score: 最低评分
            only_tradeable: 只返回可交易的（LONG/SHORT）
            varieties: 指定品种列表（可选）
            
        Returns:
            排名结果列表
        """
        if not self.provider or not self.analyzer:
            logger.error("需要 provider 和 analyzer 才能进行筛选")
            return []
            
        # 获取合约列表
        if varieties:
            # 使用指定品种
            contracts = []
            for variety in varieties:
                if '.' in variety:
                    contracts.append(variety)
                else:
                    # 自动添加主力标记
                    contracts.append(f"{variety}@主力")
        else:
            contracts = self.get_active_contracts()
            
        logger.info(f"开始分析 {len(contracts)} 个主力合约...")
        
        rankings = []
        
        for i, symbol in enumerate(contracts):
            try:
                logger.info(f"[{i+1}/{len(contracts)}] 分析: {symbol}")
                
                # 获取分析上下文
                context = self.provider.get_analysis_context(symbol)
                
                if 'error' in context:
                    logger.warning(f"跳过 {symbol}: {context['error']}")
                    continue
                
                # AI分析
                result = self.analyzer.analyze(context)
                
                if not result.success:
                    logger.warning(f"跳过 {symbol}: 分析失败")
                    continue
                
                # 计算评分
                ranking = self._calculate_ranking(result, context)
                rankings.append(ranking)
                
                logger.info(f"   评分: {ranking.total_score:.1f} | 方向: {ranking.direction}")
                
            except Exception as e:
                logger.warning(f"分析 {symbol} 失败: {e}")
                continue
        
        # 按评分排序
        rankings.sort(key=lambda x: x.total_score, reverse=True)
        
        # 分配排名
        for i, r in enumerate(rankings):
            r.rank = i + 1
            
        # 过滤
        filtered = []
        for r in rankings:
            if r.total_score < min_score:
                continue
            if only_tradeable and r.direction == 'WAIT':
                continue
            filtered.append(r)
            if len(filtered) >= top_n:
                break
                
        logger.info(f"筛选完成，共 {len(rankings)} 个合约，筛选出 {len(filtered)} 个")
        
        return filtered
    
    def _calculate_ranking(self, result, context: Dict) -> FuturesRanking:
        """
        计算排名评分
        
        Args:
            result: AI分析结果
            context: 分析上下文
            
        Returns:
            FuturesRanking 对象
        """
        # 基础评分
        sentiment_score = result.sentiment_score
        
        # 趋势评分（基于技术分析）
        trend_data = context.get('trend', {})
        trend_status = trend_data.get('status', 'unknown')
        
        if trend_status == 'up':
            trend_score = 70 + (20 if result.direction == 'LONG' else -20)
        elif trend_status == 'down':
            trend_score = 70 + (20 if result.direction == 'SHORT' else -20)
        else:
            trend_score = 50
        trend_score = max(0, min(100, trend_score))
        
        # 量能评分
        volume_data = context.get('volume_analysis', {})
        volume_status = volume_data.get('status', 'normal')
        if volume_status == 'active':
            volume_score = 80
        elif volume_status == 'very_active':
            volume_score = 90
        else:
            volume_score = 60
            
        # 综合评分加权
        # sentiment_score 60%, trend_score 25%, volume_score 15%
        total_score = (
            sentiment_score * 0.6 +
            trend_score * 0.25 +
            volume_score * 0.15
        )
        
        # 如果方向是WAIT，降低评分
        if result.direction == 'WAIT':
            total_score *= 0.5
        
        return FuturesRanking(
            symbol=result.symbol,
            name=result.name,
            exchange=result.exchange,
            trend_score=trend_score,
            volume_score=volume_score,
            sentiment_score=sentiment_score,
            total_score=total_score,
            direction=result.direction,
            operation_advice=result.operation_advice,
            entry_price=result.entry_price,
            stop_loss=result.stop_loss,
            take_profit=result.take_profit,
            analysis_summary=result.analysis_summary,
            confidence_level=result.confidence_level,
        )


def screen_top_futures(
    top_n: int = 3,
    min_score: float = 50.0,
    only_tradeable: bool = True,
    varieties: List[str] = None,
) -> List[FuturesRanking]:
    """
    筛选最优期货合约的便捷函数
    
    Args:
        top_n: 返回前N个
        min_score: 最低评分
        only_tradeable: 只返回可交易的
        varieties: 指定品种列表
        
    Returns:
        排名结果列表
    """
    from .data_provider import FuturesDataProvider
    from .analyzer import FuturesAnalyzer
    
    provider = FuturesDataProvider(use_sim=True)
    
    try:
        if not provider.connect():
            logger.error("连接天勤失败")
            return []
            
        analyzer = FuturesAnalyzer()
        screener = FuturesScreener(provider, analyzer)
        
        return screener.screen(
            top_n=top_n,
            min_score=min_score,
            only_tradeable=only_tradeable,
            varieties=varieties,
        )
    finally:
        provider.disconnect()
