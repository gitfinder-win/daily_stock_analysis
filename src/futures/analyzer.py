# -*- coding: utf-8 -*-
"""
===================================
期货分析模块
===================================

基于AI的期货智能分析

功能：
- 复用股票分析器的AI能力
- 期货特定的交易理念
- 风险控制逻辑
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from src.config import get_config
from src.analyzer import GeminiAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class FuturesAnalysisResult:
    """期货分析结果"""
    symbol: str                    # 合约代码
    name: str                      # 合约名称
    exchange: str                  # 交易所
    
    # 核心指标
    sentiment_score: int           # 综合评分 0-100
    trend_prediction: str          # 趋势预测
    operation_advice: str          # 操作建议
    confidence_level: str = "中"   # 置信度
    
    # 交易建议
    direction: str = ""            # 方向 (LONG/SHORT/WAIT)
    entry_price: float = 0.0       # 建议入场价
    stop_loss: float = 0.0         # 止损价
    take_profit: float = 0.0       # 止盈价
    position_size: int = 1         # 建议手数
    
    # 风险提示
    risk_level: str = "中"         # 风险等级
    risk_warning: str = ""         # 风险提示
    
    # 分析详情
    analysis_summary: str = ""     # 分析摘要
    key_points: str = ""           # 核心要点
    dashboard: Optional[Dict] = None  # 完整的决策仪表盘
    
    # 元数据
    raw_response: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'exchange': self.exchange,
            'sentiment_score': self.sentiment_score,
            'trend_prediction': self.trend_prediction,
            'operation_advice': self.operation_advice,
            'confidence_level': self.confidence_level,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'position_size': self.position_size,
            'risk_level': self.risk_level,
            'risk_warning': self.risk_warning,
            'analysis_summary': self.analysis_summary,
            'key_points': self.key_points,
            'success': self.success,
        }
    
    def get_emoji(self) -> str:
        """根据操作建议返回emoji"""
        emoji_map = {
            '做多': '🟢',
            '买入': '🟢',
            '做空': '🔴',
            '卖出': '🔴',
            '观望': '⚪',
            '持有': '🟡',
        }
        return emoji_map.get(self.operation_advice, '🟡')


class FuturesAnalyzer:
    """
    期货智能分析器
    
    复用股票分析器的AI能力，针对期货市场特点调整分析逻辑
    """
    
    # 期货分析专用系统提示词
    SYSTEM_PROMPT = """你是一位专业的期货投资分析师，负责生成专业的【期货决策仪表盘】。

## 核心交易理念（必须严格遵守）

### 1. 趋势交易（顺势而为）
- **多头排列**：MA5 > MA10 > MA20，看多
- **空头排列**：MA5 < MA10 < MA20，看空
- 均线缠绕时，趋势不明，建议观望

### 2. 风险控制（期货市场高杠杆）
- 单笔交易风险不超过总资金的2%
- 设置明确止损位，严格执行
- 避免在重要经济数据公布前开仓

### 3. 成交量和持仓量
- 放量增仓：趋势加强信号
- 放量减仓：趋势可能反转
- 缩量减仓：趋势动能减弱

### 4. 乖离率策略
- 乖离率 > 3%：价格偏离均线过远，注意回调风险
- 乖离率 < -3%：超卖，可能反弹

### 5. 交易所特点
- 上期所(SHFE)：贵金属、有色金属，波动较大
- 大商所(DCE)：农产品，季节性明显
- 郑商所(CZCE)：化工品、农产品
- 中金所(CFFEX)：股指期货，与股市联动

## 输出格式：期货决策仪表盘 JSON

```json
{
    "sentiment_score": 0-100整数,
    "trend_prediction": "看多/看空/震荡",
    "operation_advice": "做多/做空/观望",
    "confidence_level": "高/中/低",
    
    "dashboard": {
        "core_conclusion": {
            "one_sentence": "一句话核心结论（30字以内）",
            "signal_type": "🟢做多信号/🔴做空信号/⚪观望信号",
            "position_advice": {
                "no_position": "空仓者建议",
                "has_position": "持仓者建议"
            }
        },
        
        "trade_plan": {
            "direction": "LONG/SHORT/WAIT",
            "entry_price": 入场价格数值,
            "stop_loss": 止损价格数值,
            "take_profit": 止盈价格数值,
            "position_size": 建议手数,
            "risk_reward_ratio": 风险收益比
        },
        
        "data_perspective": {
            "trend_status": {
                "ma_alignment": "均线排列状态",
                "trend": "up/down/sideways",
                "bias_ma5": 乖离率数值
            },
            "volume_analysis": {
                "volume_status": "放量/缩量/平量",
                "oi_change": "增仓/减仓",
                "volume_strength": "强/中/弱"
            },
            "price_position": {
                "current_price": 当前价格,
                "ma5": MA5数值,
                "ma10": MA10数值,
                "ma20": MA20数值,
                "support_level": 支撑位,
                "resistance_level": 压力位
            }
        },
        
        "risk_assessment": {
            "risk_level": "高/中/低",
            "risk_points": ["风险点1", "风险点2"],
            "precautions": ["防范措施1", "防范措施2"]
        }
    },
    
    "analysis_summary": "100字综合分析摘要",
    "key_points": "3-5个核心要点，逗号分隔",
    "risk_warning": "风险提示"
}
```

## 评分标准

### 强烈做多（80-100分）：
- ✅ 多头排列，趋势向上
- ✅ 放量增仓，资金流入
- ✅ 乖离率适中（-2%~2%）
- ✅ 支撑位明确

### 做多（60-79分）：
- ✅ 偏多趋势
- ✅ 量能正常
- ⚪ 允许一项次要条件不满足

### 观望（40-59分）：
- ⚠️ 趋势不明
- ⚠️ 乖离率过大（>3%）
- ⚠️ 重要数据公布前

### 做空（0-39分）：
- ❌ 空头排列
- ❌ 放量下跌
- ❌ 跌破支撑"""

    def __init__(self):
        """初始化期货分析器"""
        self._stock_analyzer = GeminiAnalyzer()
        
    def is_available(self) -> bool:
        """检查分析器是否可用"""
        return self._stock_analyzer.is_available()
    
    def analyze(self, context: Dict[str, Any]) -> FuturesAnalysisResult:
        """
        分析期货合约
        
        Args:
            context: 从 FuturesDataProvider.get_analysis_context() 获取的上下文
            
        Returns:
            FuturesAnalysisResult 对象
        """
        symbol = context.get('symbol', 'Unknown')
        name = context.get('name', symbol)
        exchange = context.get('exchange', '')
        
        if not self.is_available():
            return FuturesAnalysisResult(
                symbol=symbol,
                name=name,
                exchange=exchange,
                sentiment_score=50,
                trend_prediction='震荡',
                operation_advice='观望',
                confidence_level='低',
                direction='WAIT',
                analysis_summary='AI分析功能未启用',
                risk_warning='请配置API Key后重试',
                success=False,
                error_message='AI API未配置',
            )
        
        try:
            # 构建期货专用提示词
            prompt = self._format_prompt(context)
            
            logger.info(f"========== 期货AI分析 {name}({symbol}) ==========")
            
            # 调用AI API
            config = get_config()
            generation_config = {
                "temperature": config.gemini_temperature,
                "max_output_tokens": 4096,
            }
            
            # 使用股票分析器的API调用方法
            response_text = self._stock_analyzer._call_api_with_retry(prompt, generation_config)
            
            # 解析响应
            result = self._parse_response(response_text, symbol, name, exchange)
            result.raw_response = response_text
            
            logger.info(f"期货分析完成: {name}({symbol}) - {result.operation_advice}, 评分 {result.sentiment_score}")
            
            return result
            
        except Exception as e:
            logger.error(f"期货分析失败 {symbol}: {e}")
            return FuturesAnalysisResult(
                symbol=symbol,
                name=name,
                exchange=exchange,
                sentiment_score=50,
                trend_prediction='震荡',
                operation_advice='观望',
                confidence_level='低',
                analysis_summary=f'分析出错: {str(e)[:100]}',
                risk_warning='分析失败，建议人工判断',
                success=False,
                error_message=str(e),
            )
    
    def _format_prompt(self, context: Dict[str, Any]) -> str:
        """格式化分析提示词"""
        symbol = context.get('symbol', 'Unknown')
        name = context.get('name', symbol)
        quote = context.get('quote', {})
        trend = context.get('trend', {})
        volume = context.get('volume_analysis', {})
        ma = context.get('ma', {})
        
        prompt = f"""# 期货决策仪表盘分析请求

## 📊 合约基础信息
| 项目 | 数据 |
|------|------|
| 合约代码 | **{symbol}** |
| 合约名称 | **{name}** |
| 交易所 | {context.get('exchange', '未知')} |
| 行情时间 | {quote.get('datetime', '未知')} |

---

## 📈 行情数据

### 最新行情
| 指标 | 数值 |
|------|------|
| 最新价 | {quote.get('last_price', 'N/A')} |
| 开盘价 | {quote.get('open', 'N/A')} |
| 最高价 | {quote.get('high', 'N/A')} |
| 最低价 | {quote.get('low', 'N/A')} |
| 昨收价 | {quote.get('pre_close', 'N/A')} |
| 涨跌幅 | {quote.get('change_pct', 'N/A')}% |
| 成交量 | {quote.get('volume', 'N/A')} |
| 持仓量 | {quote.get('open_interest', 'N/A')} |

### 均线系统
| 均线 | 数值 | 说明 |
|------|------|------|
| MA5 | {ma.get('ma5', 'N/A')} | 短期趋势线 |
| MA10 | {ma.get('ma10', 'N/A')} | 中短期趋势线 |
| MA20 | {ma.get('ma20', 'N/A')} | 中期趋势线 |

### 趋势分析
| 指标 | 数值 | 判定 |
|------|------|------|
| 趋势状态 | {trend.get('status', '未知')} | up/down/sideways |
| 均线排列 | {trend.get('alignment', '未知')} | |
| 乖离率(MA5) | {trend.get('bias_ma5', 'N/A')}% | >3%注意风险 |
| 系统信号 | {trend.get('signal', '未知')} | |

### 成交量分析
| 指标 | 数值 | 说明 |
|------|------|------|
| 量能状态 | {volume.get('status', '未知')} | |
| 量比 | {volume.get('volume_ratio', 'N/A')} | |

---

## ✅ 分析任务

请为 **{name}({symbol})** 生成期货决策仪表盘，严格按照JSON格式输出。

### 重点关注：
1. 趋势方向（多/空/震荡）
2. 入场价位和止损止盈设置
3. 风险收益比
4. 仓位建议

请输出完整的JSON格式决策仪表盘。"""
        
        return prompt
    
    def _parse_response(
        self, 
        response_text: str, 
        symbol: str, 
        name: str, 
        exchange: str
    ) -> FuturesAnalysisResult:
        """解析AI响应"""
        try:
            # 清理响应文本
            cleaned = response_text
            if '```json' in cleaned:
                cleaned = cleaned.replace('```json', '').replace('```', '')
            elif '```' in cleaned:
                cleaned = cleaned.replace('```', '')
            
            # 找到JSON
            start = cleaned.find('{')
            end = cleaned.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = cleaned[start:end]
                
                # 尝试修复常见JSON格式问题
                # 1. 移除控制字符
                import re
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
                # 2. 修复未闭合的字符串（尝试找到最后一个有效的JSON对象）
                
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    # 尝试截断到错误位置之前
                    logger.warning(f"JSON解析失败，尝试修复: {e}")
                    # 使用更宽松的解析方式
                    data = self._extract_json_fields(json_str, symbol, name, exchange)
                
                dashboard = data.get('dashboard', {})
                trade_plan = dashboard.get('trade_plan', {})
                
                # 获取操作建议
                operation_advice = data.get('operation_advice', '观望')
                
                # 根据操作建议推断方向（确保一致性）
                advice_lower = operation_advice.lower() if operation_advice else ''
                if any(w in advice_lower for w in ['买入', '做多', 'buy', 'long']):
                    direction = 'LONG'
                elif any(w in advice_lower for w in ['卖出', '做空', 'sell', 'short']):
                    direction = 'SHORT'
                else:
                    direction = trade_plan.get('direction', 'WAIT')
                
                return FuturesAnalysisResult(
                    symbol=symbol,
                    name=name,
                    exchange=exchange,
                    sentiment_score=int(data.get('sentiment_score', 50)),
                    trend_prediction=data.get('trend_prediction', '震荡'),
                    operation_advice=operation_advice,
                    confidence_level=data.get('confidence_level', '中'),
                    direction=direction,
                    entry_price=float(trade_plan.get('entry_price', 0)),
                    stop_loss=float(trade_plan.get('stop_loss', 0)),
                    take_profit=float(trade_plan.get('take_profit', 0)),
                    position_size=int(trade_plan.get('position_size', 1)),
                    risk_level=dashboard.get('risk_assessment', {}).get('risk_level', '中'),
                    risk_warning=data.get('risk_warning', ''),
                    analysis_summary=data.get('analysis_summary', ''),
                    key_points=data.get('key_points', ''),
                    dashboard=dashboard,
                    success=True,
                )
            else:
                return self._parse_text_response(response_text, symbol, name, exchange)
                
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}")
            return self._parse_text_response(response_text, symbol, name, exchange)
    
    def _parse_text_response(
        self, 
        text: str, 
        symbol: str, 
        name: str, 
        exchange: str
    ) -> FuturesAnalysisResult:
        """从文本中提取信息"""
        text_lower = text.lower()
        
        # 简单情绪判断
        positive = ['看多', '做多', '买入', '上涨', '多头', 'bullish', 'long']
        negative = ['看空', '做空', '卖出', '下跌', '空头', 'bearish', 'short']
        
        pos_count = sum(1 for w in positive if w in text_lower)
        neg_count = sum(1 for w in negative if w in text_lower)
        
        if pos_count > neg_count + 1:
            score, trend, advice, direction = 70, '看多', '做多', 'LONG'
        elif neg_count > pos_count + 1:
            score, trend, advice, direction = 30, '看空', '做空', 'SHORT'
        else:
            score, trend, advice, direction = 50, '震荡', '观望', 'WAIT'
        
        return FuturesAnalysisResult(
            symbol=symbol,
            name=name,
            exchange=exchange,
            sentiment_score=score,
            trend_prediction=trend,
            operation_advice=advice,
            confidence_level='低',
            direction=direction,
            analysis_summary=text[:300],
            key_points='JSON解析失败，仅供参考',
            risk_warning='分析结果可能不准确',
            raw_response=text,
            success=True,
        )
    
    def _extract_json_fields(self, json_str: str, symbol: str, name: str, exchange: str) -> dict:
        """
        从损坏的JSON中提取字段（容错处理）
        """
        import re
        
        def extract_value(pattern: str, text: str, default: str = '') -> str:
            match = re.search(pattern, text, re.IGNORECASE)
            return match.group(1) if match else default
        
        # 提取核心字段
        sentiment_score = extract_value(r'"sentiment_score"[\s:]+(\d+)', json_str, '50')
        trend_prediction = extract_value(r'"trend_prediction"[\s:]+\"([^\"]+)\"', json_str, '震荡')
        operation_advice = extract_value(r'"operation_advice"[\s:]+\"([^\"]+)\"', json_str, '观望')
        confidence_level = extract_value(r'"confidence_level"[\s:]+\"([^\"]+)\"', json_str, '低')
        direction = extract_value(r'"direction"[\s:]+\"([^\"]+)\"', json_str, 'WAIT')
        entry_price = extract_value(r'"entry_price"[\s:]+([\d.]+)', json_str, '0')
        stop_loss = extract_value(r'"stop_loss"[\s:]+([\d.]+)', json_str, '0')
        take_profit = extract_value(r'"take_profit"[\s:]+([\d.]+)', json_str, '0')
        
        logger.info(f"从损坏JSON中提取字段: score={sentiment_score}, trend={trend_prediction}")
        
        return {
            'sentiment_score': int(sentiment_score),
            'trend_prediction': trend_prediction,
            'operation_advice': operation_advice,
            'confidence_level': confidence_level,
            'dashboard': {
                'trade_plan': {
                    'direction': direction,
                    'entry_price': float(entry_price),
                    'stop_loss': float(stop_loss),
                    'take_profit': float(take_profit),
                }
            },
            'analysis_summary': f'{name}期货分析',
            'risk_warning': 'JSON解析异常，结果可能不完整',
        }


def get_futures_analyzer() -> FuturesAnalyzer:
    """获取期货分析器实例"""
    return FuturesAnalyzer()
