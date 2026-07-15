# Weekly Deliverables

本目录用于集中存放每周主要产出，方便导师在 GitHub 上按周、按组查看。原始脚本、完整日志和中间文件仍保留在 `scripts/`、`docs/`、`outputs/`、`logs/` 等目录中；这里仅放核心结果文件和汇报材料。

## 目录约定

```text
weekly_deliverables/
├── week2/
│   ├── README.md
│   ├── A_group/        # A 组第二周产出
│   └── B_group/        # B 组第二周产出
└── week3/
    ├── README.md
    ├── A_group/        # A 组第三周产出
    └── B_group/        # B 组第三周产出
```

每个组目录内部可按需要继续划分：

```text
A_group/ or B_group/
├── README.md
├── docs/               # 周报、调研文档、技术方案
├── results/            # 核心 CSV/TSV/XLSX 结果
├── figures/            # 图表/截图
├── html/               # HTML 汇报页
├── slides/             # PPT/PDF 汇报材料
└── interfaces/         # 跨组接口、schema、数据字典
```

## 提交规范

每周新增产出时，建议只放导师需要看的“主要结果文件”：

- 周报或总结：`docs/`
- 核心实验结果：`results/`
- 图表/截图：`figures/`
- 汇报页或展示材料：`html/`、`slides/`
- 跨组接口或 schema：`interfaces/`

不要把大体积原始日志、缓存目录、临时文件、数据库 dump 放进本目录。
