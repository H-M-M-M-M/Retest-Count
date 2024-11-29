import pandas as pd
import streamlit as st

# 设置标题
st.title("Retest TrackMetrics with Rework Analysis")

# 添加计数规则说明
st.write("### 使用说明")
st.markdown("""
**计数规则：**
1. **Fail 的计数规则：**
   - 如果某个 SN 的最后一次测试结果为 **fail**，才计为 fail，之前的 fail 不重复计数。
2. **Retest 的计数规则：**
   - 一个 SN 出现多次测试，且最后一次测试结果为 **pass**，即算作 retest pass，且同一个SN不会被重复计数。
3. **Rework 的计数规则：**
   - 如果一个 SN 中的任意 **fail** 和最后一次 **pass** 之间的时间间隔超过 **3 天**，则记为 rework SN。
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

    # 检查是否有未选择的必填选项
    if "未选择" in [sn_column, date_column, time_column, result_column]:
        st.warning("请确保所有必选列已选择！")
        st.stop()

    # 合并日期和时间
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

    # 按SN和测试时间排序
    data = data.sort_values(by=[sn_column, '测试时间']).reset_index(drop=True)

    # 获取每个SN的最新测试结果
    latest_data = data.drop_duplicates(subset=[sn_column], keep='last')

    # 标记最终结果：如果最后一次测试是fail，标记为fail，否则标记为pass
    fail_sns = latest_data[latest_data[result_column].str.lower() == 'fail'][sn_column].values
    data['最终结果'] = data[sn_column].apply(lambda x: 'fail' if x in fail_sns else 'pass')

    # Retest Pass SN 分析
    retest_pass_sns = data.groupby(sn_column).filter(lambda x: len(x) > 1)  # 筛选多次测试的 SN
    retest_pass_sns = retest_pass_sns.groupby(sn_column).filter(
        lambda x: x.iloc[-1][result_column].lower() == 'pass'
    )  # 筛选最后一次是 pass 的 SN

    # Rework SN 分析
    rework_details = []
    for sn, group in retest_pass_sns.groupby(sn_column):
        group = group.sort_values('测试时间')
        first_fail_time = group[group[result_column].str.lower() == 'fail']['测试时间'].min()
        last_pass_time = group[group[result_column].str.lower() == 'pass']['测试时间'].max()
        if first_fail_time and last_pass_time and (last_pass_time - first_fail_time).days > 3:
            test_details = []
            for i, (_, row) in enumerate(group.iterrows(), 1):
                test_details.append(
                    f"@{row['测试时间'].strftime('%Y/%m/%d %H:%M:%S')} {i}st test {row[result_column].lower()}"
                )
            rework_details.append({
                'SN': sn,
                '测试次数': len(group),
                '测试详情': "\n".join(test_details),
            })

    # 统计结果汇总
    rework_sn_count = len(rework_details)
    rework_details_df = pd.DataFrame(rework_details)

    # 统计Retest Pass和Fail
    fail_sns_unique = data[data['最终结果'] == 'fail'][sn_column].drop_duplicates()
    fail_count = len(fail_sns_unique)
    retest_sns_unique = retest_pass_sns[sn_column].drop_duplicates()
    retest_count = len(retest_sns_unique)

    # 获取列名供用户选择
    product_column = st.selectbox("选择产品型号列（可为空）", ["无（不分型号）"] + data.columns.tolist(), index=0)

    # 格式化SN的测试详情
    def format_test_details(sn_group):
        test_details = []
        for i, (_, row) in enumerate(sn_group.iterrows(), 1):
            result = row[result_column].lower()
            test_details.append(f"@{row['测试时间'].strftime('%Y/%m/%d %H:%M:%S')} {i}st test {result}")
        return test_details

    def calculate_stats(group):
        """统计数据并格式化retest_sn和fail_sn"""
        total_tests = len(group)
        unique_sn_count = group[sn_column].nunique()

        # 获取 Fail SN
        fail_sns = group[group['最终结果'] == 'fail'][sn_column].drop_duplicates()
        fails = len(fail_sns)

        # 获取 Retest Pass SN（多次测试，最后一次是pass）
        retest_pass_sns = group.groupby(sn_column).filter(lambda x: len(x) > 1)  # 多次测试的SN
        retest_pass_sns = retest_pass_sns[retest_pass_sns[result_column].str.lower() == 'pass']
        retest_pass_sns = retest_pass_sns.drop_duplicates(subset=[sn_column])  # 去重
        retests = len(retest_pass_sns)

        # 获取复测SN及其详情
        retest_details = []
        retest_group = group[group[sn_column].isin(retest_pass_sns[sn_column])]
        for sn, sn_group in retest_group.groupby(sn_column):
            test_details = format_test_details(sn_group)
            retest_details.append(f"{sn} test {len(test_details)} times\n" + "\n".join(test_details))

        # 获取失败SN及其详情
        fail_details = []
        fail_group = group[group[sn_column].isin(fail_sns)]
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
        stats = data.groupby([date_column]).apply(calculate_stats).reset_index()
    else:
        stats = data.groupby([product_column, date_column]).apply(calculate_stats).reset_index()

    # 显示统计结果
    st.write("### 总体统计结果：")
    st.markdown(f"- **测试总数**: {len(data)}")
    st.markdown(f"- **Fail SN Count**: {fail_count}")
    st.markdown(f"- **Retest Pass SN Count**: {retest_count}")
    st.markdown(f"- **Rework SN Count**: {rework_sn_count}")

    # 显示统计结果
    st.write("### 按日期统计的结果：")
    st.dataframe(stats)
    
    # 显示Rework SN详情表
    st.write("### Rework SN 详情：")
    st.dataframe(rework_details_df) 
