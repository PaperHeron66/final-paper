# -*- coding: utf-8 -*-
"""一键复现入口：依次执行 01→06，任一环节失败即中断。

用法：
    python run_all.py            # 全流程
    python run_all.py 1 2 3      # 只跑指定步骤
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"

STEPS = [
    ("01", "01_load.py", "加载官方数据并缓存"),
    ("02", "02_clean.py", "清洗治理 + 星型模型 + 三种格式导出"),
    ("03", "03_analysis.py", "六类商业分析模型与结果表"),
    ("04", "04_visuals.py", "14 张模板复现图 + 8 张业务模型图"),
    ("05", "05_dashboard.py", "交互式大屏（HTML + 版式图）"),
    ("06", "06_report.py", "按模板生成期末大论文 DOCX"),
]


def main():
    wanted = set(sys.argv[1:]) if len(sys.argv) > 1 else {s[0] for s in STEPS}
    for key, script, desc in STEPS:
        if key not in wanted:
            continue
        print(f"\n{'='*72}\n[{key}] {desc}  ({script})\n{'='*72}")
        t0 = time.time()
        r = subprocess.run([sys.executable, str(SCRIPTS / script)], cwd=str(SCRIPTS))
        if r.returncode != 0:
            print(f"[{key}] 失败，退出码 {r.returncode}，流程终止")
            sys.exit(r.returncode)
        print(f"[{key}] 完成，用时 {time.time()-t0:.1f}s")
    print("\n全部完成。图表见 outputs/figures/，论文见 docs/")


if __name__ == "__main__":
    main()
