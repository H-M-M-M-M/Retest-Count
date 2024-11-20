import pandas as pd
import streamlit as st

# 设置标题
st.title("上传并选择列作为测试数据的输入")

# 让用户上传文件
uploaded_file = st.file_uploader("选择一个Excel文件", type=["xlsx"])

if uploaded_file is not None:
    # 读取上传的Excel文件
    data = pd.read_excel(uploaded_file)

    # 显示文件内容（可选）
    st.write("上传的测试数据：")
    st.dataframe(data)

    # 获取数据的列名
    columns = data.columns.tolist()

    # 用户选择列名
    sn_column = st.selectbox("选择SN列", columns)
    date_column = st.selectbox("选择Date列", columns)
    time_column = st.selectbox("选择Time列", columns)
    result_column = st.selectbox("选择测试结果列", columns)

    # 显示用户选择的列
    st.write(f"您选择的列：SN列 - {sn_column}, Date列 - {date_column}, Time列 - {time_column}, 测试结果列 - {result_column}")

    # 处理并合并Date和Time列为完整的测试时间
    data['测试时间'] = pd.to_datetime(data[date_column].astype(str) + ' ' + data[time_column].astype(str), errors='coerce')
    data['测试日期'] = data['测试时间'].dt.date  # 提取日期部分

    # 按SN和测试时间排序
    data = data.sort_values(by=[sn_column, '测试时间']).reset_index(drop=True)

    # 找出每个SN的最后一次结果
    latest_data = data.drop_duplicates(subset=[sn_column], keep='last')

    # 判断 fail 结果（只有最后一次测试为 fail 才计数）
    data['最终结果'] = data.apply(
        lambda row: 'fail' if row[sn_column] in latest_data[latest_data[result_column].str.lower() == 'fail'][sn_column].values else 'pass',
        axis=1
    )

    # 将复测成功的 SN 汇总到首次测试日期
    data['汇总日期'] = data.apply(
        lambda row: row['测试日期'] if row[sn_column] not in latest_data[latest_data[result_column].str.lower() == 'pass'][sn_column].values
        else data[data[sn_column] == row[sn_column]]['测试日期'].min(),
        axis=1
    )

    # 按汇总日期统计
    def calculate_stats(group):
        total_tests = len(group)  # 测试总数
        retests = group.duplicated(subset=[sn_column]).sum()  # 复测数
        fails = group[group['最终结果'] == 'fail'].shape[0]  # fail数
        unique_sn_count = group[sn_column].nunique()  # 去重的SN数量

        # 获取Retest的SN及其复测详细信息
        retest_sn_details = []
        retest_group = group[group.duplicated(subset=[sn_column], keep=False)]
        for sn, sn_group in retest_group.groupby(sn_column):
            test_details = []
            sn_tests = sn_group.sort_values(by='测试时间')
            for i, (idx, row) in enumerate(sn_tests.iterrows(), 1):  # 使用enumerate替代index
                test_result = row[result_column].lower()
                test_details.append(
                    f"@{row['测试时间'].strftime('%Y/%m/%d %H:%M:%S')} {i}st test {test_result}"
                )
            retest_sn_details.append(f"{sn} test {len(sn_tests)} times\n" + "\n".join(test_details))

        # 获取Fail的SN及其失败详细信息
        fail_sn_details = []
        fail_group = group[group['最终结果'] == 'fail']
        for sn, sn_group in fail_group.groupby(sn_column):
            test_details = []
            sn_tests = sn_group.sort_values(by='测试时间')
            for i, (idx, row) in enumerate(sn_tests.iterrows(), 1):  # 使用enumerate替代index
                test_details.append(
                    f"@{row['测试时间'].strftime('%Y/%m/%d %H:%M:%S')} {i}st test {row[result_column].lower()}"
                )
            fail_sn_details.append(f"{sn} test {len(sn_tests)} times\n" + "\n".join(test_details))

        return pd.Series({
            'total_test': total_tests,
            'retest': retests,
            'fail': fails,
            'unique_samples': unique_sn_count,
            'retest_sn': "\n".join(retest_sn_details),  # 复测的详细信息
            'fail_sn': "\n".join(fail_sn_details)  # 失败的详细信息
        })

    stats_by_date = data.groupby('汇总日期').apply(calculate_stats).reset_index()

    # 显示统计结果
    st.write("按日期统计结果：")
    st.dataframe(stats_by_date)

    # 保存结果到Excel
    output_path = r"C:\Users\320026234\Desktop\2024\APP\MM\按日期统计结果.xlsx"
    stats_by_date.to_excel(output_path, index=False)
    st.write(f"按日期统计结果已保存到 {output_path}")
