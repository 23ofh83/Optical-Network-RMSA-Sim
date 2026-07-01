import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

import matplotlib
matplotlib.use('Agg') # 牢牢守住无头后端

def generate_automated_reports():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "my_simulation_results.csv")
    
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        print(f"⚠️ 仿真数据源未生成或为空，静默跳过报告编译。")
        return

    df = pd.read_csv(csv_path)
    
    # 🌟 护栏 1：防御无数据或脏数据引发的下游全盘崩溃
    if df.empty or "Network" not in df.columns:
        print("⚠️ 数据集内容不完整，无法渲染高维图表。")
        return

    plots_dir = os.path.join(current_dir, "reports")
    reports_dir = os.path.join(current_dir, "reports")
    os.makedirs(plots_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    # ==========================================
    # 核心精简与呈现策略：只针对真实存在的数据进行自适应分组
    # ==========================================
    for net_name, net_df in df.groupby("Network"):
        
        # ── 1. 阻断率看板 (核心指标：只呈现实际跑出来的流量矩阵) ──
        plt.figure(figsize=(9, 5))
        
        # 🌟 护栏 2：如果某种算法或者矩阵在本次快测中没跑，Seaborn 会自动根据当前网元内存在的实际种类自适应对齐
        sns.barplot(
            data=net_df, 
            x="Matrix", 
            y="BP(%)", 
            hue="Algorithm", 
            palette="Set2"
        )
        plt.title(f"Net {net_name} - Spectrum Blocking Analysis", fontsize=11, fontweight='bold')
        plt.xlabel("Tested Traffic Matrices")
        plt.ylabel("Blocking Probability (%)")
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        
        # 🌟 护栏 3：如果只跑了一个场景，hue_labels 会只有 1 个，强行指定 loc 可能会挡住柱状图，设为 best 自适应避让
        plt.legend(loc="best")
        
        plt.savefig(os.path.join(plots_dir, f"{net_name}_Metrics_Blocking_Comparison.png"), bbox_inches='tight', dpi=150)
        plt.close()

        # ── 2. 时空复杂度看板 (精简呈现：核心关注算法间的时延中位数，剔除洗牌干扰) ──
        plt.figure(figsize=(8, 5))
        
        # 🌟 护栏 4：检查当前网元下的样本量是否大于等于 2。如果只有 1 条数据，画 Boxplot 箱线图会变成一条很难看的单线，此时自动退化为点图 (Stripplot)
        if len(net_df) >= 2:
            sns.boxplot(data=net_df, x="Algorithm", y="Runtime_Sec", color="#e8f4f8", width=0.4)
            sns.stripplot(data=net_df, x="Algorithm", y="Runtime_Sec", hue="Order", palette="Set1", size=6, jitter=0.1)
        else:
            sns.stripplot(data=net_df, x="Algorithm", y="Runtime_Sec", hue="Order", palette="Set1", size=8)
            
        plt.title(f"Net {net_name} - Algorithm Computational Delay Variance", fontsize=10, fontweight='bold')
        plt.ylabel("Execution Time (Seconds)")
        
        plt.savefig(os.path.join(plots_dir, f"{net_name}_Metrics_Runtime_Distribution.png"), bbox_inches='tight', dpi=150)
        plt.close()

    # ── 3. 编译 Markdown 简报 (自适应 Top-N 数据截取) ──
    md_report_path = os.path.join(reports_dir, "automated_experiment_summary.md")
    # === 🌟 工业级智能报表切片逻辑 ===
    with open(md_report_path, "w", encoding="utf-8") as f:
        f.write(f"# 🌙 Automated Optical Network Performance Report\n\n")
        f.write(f"## 1. 业务基准数据矩阵\n\n")
        
        # 1. 动态评估当前跑出来的总场景丰度 (Total Scenarios)
        total_records = len(df)
        
        # 2. 智能化分支拦截：
        if total_records <= 20:
            # 💡 场景 A：如果你在做短路快测（数据量少），全量呈现所有网络和算法，并按【网络、阻塞率】联合规范排序
            # 这样可以100%确保 IT10、G17、G50 的每一种算法都在表格里清晰对齐，绝不遗漏！
            display_df = df.sort_values(by=["Network", "BP(%)"], ascending=[True, False])
            print(f"ℹ️ 检测到当前为快测模式（样本量: {total_records}），已自动切换为【全量全网自适应对齐看板】。")
        else:
            # 💡 场景 B：如果运行的是全量 60+ 组场景，为了防止报告变成臭长垃圾场，自动激活 Top-10 极限压力筛选
            display_df = df.sort_values(by="BP(%)", ascending=False).head(10)
            print(f"ℹ️ 检测到全量压测模式（样本量: {total_records}），已自动激活【Top-10 极限压力淘汰看板】。")
            
        # 3. 绝对安全的写落盘（head防护依然在底层生效）
        f.write(display_df[["Network", "Matrix", "Algorithm", "Order", "BP(%)", "Runtime_Sec"]].to_markdown(index=False))
        f.write("\n")

    print(f"🎉 防御性数据看板编译成功！当前样本丰度：{len(df)} 组场景。")

if __name__ == "__main__":
    generate_automated_reports()