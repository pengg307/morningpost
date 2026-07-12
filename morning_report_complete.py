#!/usr/bin/env python3
"""
晨报系统 - 完整整合版（零 Token 模板模式）
=============================================
整合所有数据源和报告生成器，实现完整的晨报系统

使用方法:
    python morning_report_complete.py --type crewai   # 生成 CrewAI 版晨报
    python morning_report_complete.py --type langgraph  # 生成 LangGraph 版晨报
    python morning_report_complete.py --type both       # 生成双框架晨报
"""
import os
import sys
import json
import time
from datetime import datetime


def run_crewai_morning():
    """运行 CrewAI 版晨报"""
    print("=" * 60)
    print("📊 【CrewAI 版晨报】开始生成...")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        from crewai_team_v2 import main as crewai_main
        crewai_main()
        
        elapsed = time.time() - start_time
        print(f"\n✅ CrewAI 版晨报生成完成，耗时: {elapsed:.2f}s")
        return "success"
    except Exception as e:
        print(f"\n❌ CrewAI 版晨报生成失败: {e}")
        return "error"


def run_langgraph_morning():
    """运行 LangGraph 版晨报"""
    print("\n" + "=" * 60)
    print("📊 【LangGraph 版晨报】开始生成...")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        from langgraph_team_v2 import main as lg_main
        lg_main()
        
        elapsed = time.time() - start_time
        print(f"\n✅ LangGraph 版晨报生成完成，耗时: {elapsed:.2f}s")
        return "success"
    except Exception as e:
        print(f"\n❌ LangGraph 版晨报生成失败: {e}")
        return "error"


if __name__ == '__main__':
    report_type = 'both'
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == '--type' and i + 1 < len(sys.argv):
                report_type = sys.argv[i + 1]
                break
    
    print(f"\n🚀 开始生成【{report_type}】晨报...")
    
    if report_type == 'crewai':
        run_crewai_morning()
    elif report_type == 'langgraph':
        run_langgraph_morning()
    elif report_type == 'both':
        run_crewai_morning()
        run_langgraph_morning()
    else:
        print(f"❌ 未知的报告类型: {report_type}")
        print("可用类型：crewai, langgraph, both")
        sys.exit(1)
    
    print("\n✅ 所有报告生成完成！")
