import pandas as pd
import streamlit as st
import io

# 设置标题
st.title("Retest TrackMetrics")

# 添加计数规则说明
st.write("### 统计规则")
st.markdown("""
1. **Fail 的计数规则：**
   - 如果某个 SN 的最后一次测试结果为 **fail**，才计为 fail，之前的 fail 不重复计数。
   - 如果某个 SN 的最后一次测试结果为 **pass**，即使之前有 fail，也不计入 fail 数。
2. **Retest 的计数规则：**
   - 一个 SN 出现多次测试，且最后一次测试结果为 **pass**，即算作 retest pass。
3. **Invalid Test 的计数规则：**
   - 如果测试结果不是 **pass** 或 **fail**（忽略大小写和空格），计为无效测试。
""")

# 上传文件
uploaded_file = st.file_uploader("选择一个Excel文件", type=["xlsx"])

if uploaded_file:
    # 读取文件
    data = pd.read_excel(uploaded_file)

    # 显示数据预览
    st.write("上传的测试数据：")
    st.dataframe(data.head())

    # 获取列名供用户选择
    columns = ["未选择"] + data.columns.tolist()  # 添加“未选择”作为默认选项
    sn_column = st.selectbox("选择SN列", columns, index=0)
    date_column = st.selectbox("选择Date列", columns, index=0)
    time_column = st.selectbox("选择Time列", columns, index=0)
    result_column = st.selectbox("选择测试结果列", columns, index=0)
    product_column = st.selectbox("选择产品型号列（可为空）", ["无（不分型号）"] + data.columns.tolist(), index=0)

    # 检查是否有未选择的必填选项
    if "未选择" in [sn_column, date_column, time_column, result_column]:
        st.warning("请确保所有必选列已选择！")
        st.stop()

    # 确保日期和时间列合并正确
    try:
        data['测试时间'] = pd.to_datetime(
            data[date_column].astype(str) + ' ' + data[time_column].astype(str), errors='coerce'
        )
        if data['测试时间'].isna().any():
            st.error("部分日期或时间无效，请检查数据格式！")
            st.stop()
    except Exception as e:
        st.error(f"日期或时间列解析失败: {e}")
        st.stop()

    # 预处理测试结果列，统一格式
    data[result_column] = data[result_column].astype(str).str.strip().str.lower()

    # 标记无效测试
    data['测试状态'] = data[result_column].apply(
        lambda x: 'pass' if x == 'pass' else 'fail' if x == 'fail' else 'invalid'
    )

    # 显示预处理后的数据
    st.write("处理后的测试数据：")
    st.dataframe(data.head())

    # 按SN和测试时间排序
    data = data.sort_values(by=[sn_column, '测试时间']).reset_index(drop=True)

    # 获取每个SN的最新测试结果
    latest_data = data.drop_duplicates(subset=[sn_column], keep='last')

    # 标记最终结果
    fail_sns = latest_data[latest_data['测试状态'] == 'fail'][sn_column].values
    data['最终结果'] = data[sn_column].apply(lambda x: 'fail' if x in fail_sns else 'pass')

    # 统计每个SN的测试详情
    def format_test_details(sn_group):
        """格式化SN的测试详情"""
        test_details = []
        for _, row in sn_group.iterrows():
            result = row['测试状态']
            timestamp = row['测试时间'].strftime('%Y-%m-%d %H:%M:%S')
            test_details.append(f"{timestamp}: {result}")
        return "\n".join(test_details)

    # 统计函数
    def calculate_stats(group):
        total_tests = group.shape[0]
        unique_sn_count = group[sn_column].nunique()
        retest_sns = group[group.duplicated(subset=[sn_column], keep=False)]
        fail_sns_group = group[group['最终结果'] == 'fail']
        invalid_tests = group[group['测试状态'] == 'invalid'].shape[0]

        # 获取复测通过SN及其详情
        retest_details = []
        for sn, sn_group in retest_sns.groupby(sn_column):
            details = format_test_details(sn_group)
            retest_details.append(f"{sn}:\n{details}")

        # 获取失败SN及其详情
        fail_details = []
        for sn, sn_group in fail_sns_group.groupby(sn_column):
            details = format_test_details(sn_group)
            fail_details.append(f"{sn}:\n{details}")

        return pd.Series({
            '测试总数': total_tests,
            '唯一SN计数': unique_sn_count,
            'Invalid Test Count': invalid_tests,
            'Retest Pass SN 计数': len(retest_sns[sn_column].unique()),
            'Fail SN 计数': fail_sns_group[sn_column].nunique(),
            'Retest Pass SN Details': "\n".join(retest_details),
            'Fail SN Details': "\n".join(fail_details),
        })

    # 判断是否按产品型号分组
    if product_column == "无（不分型号）":
        # 不分型号时，直接调用统计函数
        stats = calculate_stats(data)  # 返回Series
        stats = pd.DataFrame([stats])  # 转换为DataFrame格式
    else:
        # 按型号分组统计
        stats = data.groupby([product_column]).apply(calculate_stats).reset_index()

    # 显示统计结果
    st.write("统计结果：")
    st.dataframe(stats)

    # 导出统计结果
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        stats.to_excel(writer, index=False, sheet_name='统计结果')
        output.seek(0)

    st.download_button(
        label="下载统计结果",
        data=output,
        file_name="统计结果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
