import pandas as pd
import streamlit as st

# 设置标题
st.title("Retest TrackMetrics")

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
        data['测试日期'] = data['测试时间'].dt.date
    except Exception as e:
        st.error(f"日期或时间列解析失败: {e}")
        st.stop()

    # 按SN和测试时间排序
    data = data.sort_values(by=[sn_column, '测试时间']).reset_index(drop=True)

    # 获取每个SN的最新测试结果
    latest_data = data.drop_duplicates(subset=[sn_column], keep='last')

    # 标记最终结果
    fail_sns = latest_data[latest_data[result_column].str.lower() == 'fail'][sn_column].values
    data['最终结果'] = data[sn_column].apply(lambda x: 'fail' if x in fail_sns else 'pass')

    # 计算每个SN的首次测试日期
    data['按日期统计'] = data.groupby(sn_column)['测试日期'].transform('min')

    # 按产品型号和按日期统计统计
    def format_test_details(sn_group):
        """格式化SN的测试详情"""
        test_details = []
        for i, (_, row) in enumerate(sn_group.iterrows(), 1):
            result = row[result_column].lower()
            test_details.append(f"@{row['测试时间'].strftime('%Y/%m/%d %H:%M:%S')} {i}st test {result}")
        return test_details

    def calculate_stats(group):
        """统计数据并格式化retest_sn和fail_sn"""
        total_tests = len(group)
        retests = group.duplicated(subset=[sn_column]).sum()
        fails = group[group['最终结果'] == 'fail'].shape[0]
        unique_sn_count = group[sn_column].nunique()

        # 获取复测SN及其详情
        retest_details = []
        retest_group = group[group.duplicated(subset=[sn_column], keep=False)]
        for sn, sn_group in retest_group.groupby(sn_column):
            test_details = format_test_details(sn_group)
            retest_details.append(f"{sn} test {len(test_details)} times\n" + "\n".join(test_details))

        # 获取失败SN及其详情
        fail_details = []
        fail_group = group[group['最终结果'] == 'fail']
        for sn, sn_group in fail_group.groupby(sn_column):
            test_details = format_test_details(sn_group)
            fail_details.append(f"{sn} test {len(test_details)} times\n" + "\n".join(test_details))

        return pd.Series({
            '测试总数': total_tests,
            '唯一SN计数': unique_sn_count,
            'Retest Pass SN 计数': retests,
            'Fail SN 计数': fails,
            'Retest Pass SN Details': "\n".join(retest_details),
            'Fail SN Details': "\n".join(fail_details)
        })

    # 判断是否按产品型号分组
    if product_column == "无（不分型号）":
        stats = data.groupby(['按日期统计']).apply(calculate_stats).reset_index()
    else:
        stats = data.groupby([product_column, '按日期统计']).apply(calculate_stats).reset_index()

    # 显示统计结果
    st.write("统计结果：")
    st.dataframe(stats)
