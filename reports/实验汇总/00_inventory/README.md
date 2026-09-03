# 00_inventory

- `all_files_inventory.csv`: 递归扫描 /home/xqin5/llmlanguage 下所有相关文件(csv/json/jsonl/py/md/log/pdf...),标注实验家族、角色、是否含原始 episode/汇总统计/分析代码/图/攻击结果。
- `experiment_inventory.csv`: 每行一个实验批次(R9v2/R9v1/R8/MISROUTE/R6/R7-D/R7-C),含模型/基准/条件/N/任务数/主指标/原始数据路径/报告路径/攻击相关度。

N 为自动读取的 jsonl 行数(episode-level 批次)或报告实测值。
