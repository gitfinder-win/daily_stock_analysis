# -*- coding: utf-8 -*-
"""
===================================
期货分析报告生成器
===================================

生成期货分析报告的Markdown文档
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .analyzer import FuturesAnalysisResult
from .data_provider import AccountInfo

logger = logging.getLogger(__name__)


class FuturesReportGenerator:
    """期货分析报告生成器"""
    
    def generate_report(
        self,
        results: List[FuturesAnalysisResult],
        account: Optional[AccountInfo] = None,
        include_summary: bool = True
    ) -> str:
        """
        生成期货分析报告
        
        Args:
            results: 分析结果列表
            account: 账户信息
            include_summary: 是否包含汇总
            
        Returns:
            Markdown格式的报告
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # 统计
        long_count = sum(1 for r in results if r.direction == 'LONG')
        short_count = sum(1 for r in results if r.direction == 'SHORT')
        wait_count = sum(1 for r in results if r.direction == 'WAIT')
        
        lines = [
            f"# 期货决策仪表盘 - {date_str}",
            "",
            f"> 共分析 **{len(results)}** 个合约 | [多]{long_count} [空]{short_count} [观望]{wait_count}",
            "",
        ]
        
        # 汇总部分
        if include_summary:
            lines.extend(self._generate_summary(results))
        
        # 各合约详细分析
        for result in results:
            lines.extend(self._generate_contract_section(result))
        
        # 账户信息
        if account:
            lines.extend(self._generate_account_section(account))
        
        # 风险提示
        lines.extend(self._generate_risk_disclaimer())
        
        return '\n'.join(lines)
    
    def _generate_summary(self, results: List[FuturesAnalysisResult]) -> List[str]:
        """生成汇总部分"""
        lines = [
            "## 分析结果汇总",
            "",
        ]
        
        # 按评分排序
        sorted_results = sorted(results, key=lambda x: x.sentiment_score, reverse=True)
        
        for r in sorted_results:
            emoji = self._get_direction_emoji(r.direction)
            lines.append(
                f"**{emoji} {r.name}({r.symbol})**: {r.operation_advice} | 评分 {r.sentiment_score} | {r.trend_prediction}"
            )
        
        lines.extend(["", "---", ""])
        return lines
    
    def _get_direction_emoji(self, direction: str) -> str:
        """获取方向emoji"""
        if direction == 'LONG':
            return '[多]'
        elif direction == 'SHORT':
            return '[空]'
        else:
            return '[观望]'
    
    def _generate_contract_section(self, result: FuturesAnalysisResult) -> List[str]:
        """生成单个合约的分析部分"""
        dir_emoji = self._get_direction_emoji(result.direction)
        
        lines = [
            f"## {dir_emoji} {result.name} ({result.symbol})",
            "",
        ]
        
        # 重要信息速览
        lines.extend(self._generate_info_overview(result))
        
        # 核心结论
        lines.extend(self._generate_core_conclusion(result))
        
        # 数据透视
        lines.extend(self._generate_data_perspective(result))
        
        # 作战计划
        if result.direction in ['LONG', 'SHORT']:
            lines.extend(self._generate_trade_plan(result))
        
        # 风险提示
        if result.risk_warning:
            lines.extend([
                "### 风险提示",
                "",
                f"- {result.risk_warning}",
                "",
            ])
        
        lines.extend(["---", ""])
        return lines
    
    def _generate_info_overview(self, result: FuturesAnalysisResult) -> List[str]:
        """生成重要信息速览"""
        lines = [
            "### 重要信息速览",
            "",
        ]
        
        # 趋势情绪
        trend_text = result.trend_prediction if result.trend_prediction else '震荡'
        lines.append(f"**趋势判断**: {trend_text}")
        
        # 置信度
        lines.append(f"**分析置信度**: {result.confidence_level}")
        
        # 风险等级
        if result.risk_level:
            lines.append(f"**风险等级**: {result.risk_level}")
        
        lines.append("")
        return lines
    
    def _generate_core_conclusion(self, result: FuturesAnalysisResult) -> List[str]:
        """生成核心结论"""
        dir_emoji = self._get_direction_emoji(result.direction)
        
        lines = [
            "### 核心结论",
            "",
            f"**{dir_emoji} {result.operation_advice}** | {result.trend_prediction}",
            "",
        ]
        
        if result.analysis_summary:
            # 清理摘要中的JSON代码块
            summary = result.analysis_summary
            if '```json' in summary:
                summary = summary.split('```json')[0].strip()
            lines.append(f"> **一句话决策**: {summary[:150]}")
            lines.append("")
        
        # 时效性
        lines.extend([
            f"**时效性**: 今日内",
            "",
            "| 持仓情况 | 操作建议 |",
            "|---------|---------|",
        ])
        
        if result.direction == 'LONG':
            lines.append(f"| **空仓者** | 可在{result.entry_price:.2f}附近分批做多，止损{result.stop_loss:.2f}。 |")
            lines.append(f"| **持仓者** | 多单持有，若跌破{result.stop_loss:.2f}严格止损。 |")
        elif result.direction == 'SHORT':
            lines.append(f"| **空仓者** | 可在{result.entry_price:.2f}附近分批做空，止损{result.stop_loss:.2f}。 |")
            lines.append(f"| **持仓者** | 空单持有，若突破{result.stop_loss:.2f}严格止损。 |")
        else:
            lines.append("| **空仓者** | 暂不介入，等待明确信号。 |")
            lines.append("| **持仓者** | 建议减仓或离场观望。 |")
        
        lines.append("")
        return lines
    
    def _generate_data_perspective(self, result: FuturesAnalysisResult) -> List[str]:
        """生成数据透视"""
        dashboard = result.dashboard or {}
        trade_plan = dashboard.get('trade_plan', {})
        data_perspective = dashboard.get('data_perspective', {})
        
        lines = [
            "### 数据透视",
            "",
        ]
        
        # 趋势状态
        trend_status = data_perspective.get('trend_status', {})
        if trend_status:
            lines.append(f"**趋势状态**: {trend_status.get('trend', '未知')} | 均线排列: {trend_status.get('ma_alignment', '未知')}")
            lines.append("")
        
        # 价格指标
        lines.extend([
            "| 指标 | 数值 |",
            "|------|------|",
        ])
        
        if trade_plan.get('entry_price'):
            lines.append(f"| 入场价 | {trade_plan.get('entry_price', 0):.2f} |")
        if trade_plan.get('stop_loss'):
            lines.append(f"| 止损价 | {trade_plan.get('stop_loss', 0):.2f} |")
        if trade_plan.get('take_profit'):
            lines.append(f"| 止盈价 | {trade_plan.get('take_profit', 0):.2f} |")
        if trade_plan.get('risk_reward_ratio'):
            lines.append(f"| 风险收益比 | {trade_plan.get('risk_reward_ratio', 0):.2f} |")
        
        if len(lines) > 5:  # 有数据才显示表格
            lines.append("")
        else:
            lines = lines[:4]  # 只保留标题
        
        # 成交量分析
        volume_analysis = data_perspective.get('volume_analysis', {})
        if volume_analysis:
            lines.append(f"**量能分析**: {volume_analysis.get('volume_status', '未知')} | 强度: {volume_analysis.get('volume_strength', '未知')}")
            lines.append("")
        
        return lines
    
    def _generate_trade_plan(self, result: FuturesAnalysisResult) -> List[str]:
        """生成作战计划"""
        lines = [
            "### 作战计划",
            "",
            "**狙击点位**",
            "",
            "| 点位类型 | 价格 |",
            "|---------|------|",
        ]
        
        if result.direction == 'LONG':
            if result.entry_price:
                lines.append(f"| 理想买入点 | {result.entry_price:.2f} |")
            if result.take_profit:
                lines.append(f"| 目标止盈 | {result.take_profit:.2f} |")
            if result.stop_loss:
                lines.append(f"| 止损位 | {result.stop_loss:.2f} |")
        elif result.direction == 'SHORT':
            if result.entry_price:
                lines.append(f"| 理想卖出点 | {result.entry_price:.2f} |")
            if result.take_profit:
                lines.append(f"| 目标止盈 | {result.take_profit:.2f} |")
            if result.stop_loss:
                lines.append(f"| 止损位 | {result.stop_loss:.2f} |")
        
        lines.append("")
        
        # 仓位建议
        lines.extend([
            f"**建议手数**: {result.position_size} 手",
            "",
            "**检查清单**",
            "",
        ])
        
        # 检查项
        checks = [
            (result.direction in ['LONG', 'SHORT'], "方向明确"),
            (result.entry_price > 0, "入场价已设定"),
            (result.stop_loss > 0, "止损价已设定"),
            (result.take_profit > 0, "止盈价已设定"),
        ]
        
        for passed, text in checks:
            mark = "[Y]" if passed else "[N]"
            lines.append(f"- {mark} {text}")
        
        lines.append("")
        return lines
    
    def _generate_account_section(self, account: AccountInfo) -> List[str]:
        """生成账户信息部分"""
        lines = [
            "## 账户信息",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 权益 | {account.balance:,.2f} |",
            f"| 可用资金 | {account.available:,.2f} |",
            f"| 占用保证金 | {account.margin:,.2f} |",
            f"| 浮动盈亏 | {account.float_profit:,.2f} |",
            f"| 平仓盈亏 | {account.close_profit:,.2f} |",
            f"| 风险度 | {account.risk_ratio:.2%} |",
            "",
            "---",
            "",
        ]
        return lines
    
    def _generate_risk_disclaimer(self) -> List[str]:
        """生成风险提示"""
        lines = [
            "## 风险声明",
            "",
            "> **免责声明**: 本报告由AI自动生成，仅供参考，不构成投资建议。",
            "> 期货交易具有高杠杆、高风险特点，请根据自身风险承受能力谨慎决策。",
            "> 历史表现不代表未来收益，投资有风险，入市需谨慎。",
            "",
            "---",
            f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ]
        return lines
    
    def save_report(
        self,
        content: str,
        filename: Optional[str] = None
    ) -> str:
        """
        保存报告到文件
        
        Args:
            content: 报告内容
            filename: 文件名（可选）
            
        Returns:
            文件路径
        """
        if filename is None:
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f"futures_report_{date_str}.md"
        
        # 确保 reports 目录存在
        reports_dir = Path(__file__).parent.parent / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = reports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"期货报告已保存: {filepath}")
        return str(filepath)
    
    def generate_and_save(
        self,
        results: List[FuturesAnalysisResult],
        account: Optional[AccountInfo] = None
    ) -> str:
        """
        生成并保存报告
        
        Args:
            results: 分析结果
            account: 账户信息
            
        Returns:
            报告文件路径
        """
        content = self.generate_report(results, account)
        return self.save_report(content)


def generate_futures_report(
    results: List[FuturesAnalysisResult],
    account: Optional[AccountInfo] = None
) -> str:
    """便捷函数：生成期货报告"""
    generator = FuturesReportGenerator()
    return generator.generate_and_save(results, account)
