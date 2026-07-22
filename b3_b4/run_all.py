# -*- coding: utf-8 -*-
"""
一键运行 B3 + B4
================
先跑 B3 容量预测，再跑 B4 调优效果自动化验证。
用法（在 b3_b4/ 目录下）：
  python run_all.py
"""
import runpy
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

if __name__ == "__main__":
    print("\n########## 运行 B3 资源容量预测 ##########\n")
    runpy.run_module("b3_forecast.run_b3", run_name="__main__")
    print("\n########## 运行 B4 调优效果自动化验证 ##########\n")
    runpy.run_module("b4_validation.run_b4", run_name="__main__")
    print("\n全部完成，结果见 b3_b4/outputs/\n")
