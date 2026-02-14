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
from typing import List, Optional

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
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        
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
            dir_mark = "[多]" if r.direction == "LONG" else "[空]" if r.direction == "SHORT" else "[观望]"
            lines.append(
                f"**{dir_mark} {r.name}({r.symbol})**: {r.operation_advice} | 评分 {r.sentiment_score} | {r.trend_prediction}"
            )
        
        lines.extend(["", "---", ""])
        return lines
    
    def _generate_contract_section(self, result: FuturesAnalysisResult) -> List[str]:
        """生成单个合约的分析部分"""
        dir_mark = "[多]" if result.direction == "LONG" else "[空]" if result.direction == "SHORT" else "[观望]"
        
        lines = [
            f"## {dir_mark} {result.name} ({result.symbol})",
            "",
        ]
        
        # 核心结论
        lines.extend([
            "### 核心结论",
            "",
            f"**{result.operation_advice}** | {result.trend_prediction} | 置信度: {result.confidence_level}",
            "",
        ])
        
        if result.analysis_summary:
            lines.extend([
                f"> {result.analysis_summary[:200]}",
                "",
            ])
        
        # 交易计划
        if result.direction in ['LONG', 'SHORT'] and result.entry_price > 0:
            lines.extend([
                "### 交易计划",
                "",
                "| 指标 | 数值 |",
                "|------|------|",
                f"| 方向 | {'做多' if result.direction == 'LONG' else '做空'} |",
                f"| 入场价 | {result.entry_price:.2f} |",
                f"| 止损价 | {result.stop_loss:.2f} |",
                f"| 止盈价 | {result.take_profit:.2f} |",
                f"| 建议手数 | {result.position_size} |",
                f"| 风险等级 | {result.risk_level} |",
                "",
            ])
        
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
