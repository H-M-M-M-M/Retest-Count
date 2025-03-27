import pandas as pd
import streamlit as st
import io

# Title
st.title("⛑Test Data Analysis App复测|不良统计工具🛴🛴🛴")

# Upload Excel file
uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file:
    # Load Excel file
    xls = pd.ExcelFile(uploaded_file)

    # Let the user select a sheet
    sheet_names = xls.sheet_names
    sheet_name = st.selectbox("Select a sheet", sheet_names)

    # Load data from the selected sheet
    data = pd.read_excel(xls, sheet_name=sheet_name)

    # Strip leading/trailing spaces from column names
    data.columns = data.columns.str.strip()

    # Display raw data
    st.write(f"Data from sheet: {sheet_name}")
    st.dataframe(data.head())

    # Select columns
    columns = ["Not Selected"] + data.columns.tolist()
    sn_column = st.selectbox("Select SN Column", columns, index=0)
    date_column = st.selectbox("Select Test Date Column", columns, index=0)
    time_column = st.selectbox("Select Test Time Column", columns, index=0)
    status_column = st.selectbox("Select Test Status Column", columns, index=0)
    probe_column = st.selectbox("Select Probe Type Column (Optional)", columns, index=0)

    if "Not Selected" in [sn_column, date_column, time_column, status_column]:
        st.warning("Please select all required columns!")
        st.stop()

    # Convert relevant columns to strings and strip whitespace
    for col in [sn_column, date_column, time_column, status_column, probe_column]:
        if col != "Not Selected":
            data[col] = data[col].astype(str).str.strip()

    # Standardize status values to lower case
    data[status_column] = data[status_column].str.lower()

    # Handle potential issues with date and time conversion
    try:
        # 将日期和时间列转换为 datetime 类型，如果有无效值会被转换为 NaT
        data[date_column] = pd.to_datetime(data[date_column], errors='coerce').dt.date
        data[time_column] = pd.to_datetime(data[time_column], errors='coerce').dt.time
        # 删除日期或时间无效的行
        data = data.dropna(subset=[date_column, time_column])
        
        # 合并日期和时间为单个 datetime 列
        data["Test Time"] = pd.to_datetime(
            data[date_column].astype(str) + " " + data[time_column].astype(str),
            errors="coerce"
        )
    except Exception as e:
        st.error(f"Error converting date and time: {e}")
        st.stop()

    if data["Test Time"].isna().any():
        st.error("Invalid date or time detected. Please check your data!")
        st.stop()

    # 转换 datetime 为时区无关（naive）的格式，Excel 不支持带时区的 datetime
    data["Test Time"] = data["Test Time"].apply(lambda x: x.replace(tzinfo=None) if pd.notnull(x) else x)

    # Sort data by SN and Test Time
    data = data.sort_values(by=[sn_column, "Test Time"]).reset_index(drop=True)

    # Helper function to calculate summary
    def calculate_summary(group):
        total_tests = len(group)
        unique_sn_count = group[sn_column].nunique()

        # 1st Test Pass
        first_test = group.drop_duplicates(subset=[sn_column], keep="first")
        first_test_pass = first_test[first_test[status_column] == "pass"][sn_column].nunique()

        # Retest Pass
        retest_pass_sn = (
            group.groupby(sn_column)
            .filter(lambda x: len(x) > 1 and x.iloc[-1][status_column] == "pass")
            .groupby(sn_column)
            .filter(lambda x: (x["Test Time"].max() - x["Test Time"].min()).days < 3)
        )
        retest_pass_count = retest_pass_sn[sn_column].nunique()

        # True Fail
        latest_test = group.drop_duplicates(subset=[sn_column], keep="last")
        true_fail_sn = latest_test[latest_test[status_column] == "fail"]
        true_fail_count = true_fail_sn[sn_column].nunique()

        # Rework
        rework_sn = (
            group.groupby(sn_column)
            .filter(lambda x: len(x) > 1 and (x["Test Time"].max() - x["Test Time"].min()).days > 3)
        )
        # Now, get the last record for each SN (the last rework test)
        last_rework = rework_sn.sort_values(by=["Test Time"]).groupby(sn_column).last().reset_index()

        # Separate Rework Pass and Rework Fail
        rework_pass_sn = last_rework[last_rework[status_column] == "pass"]
        rework_fail_sn = last_rework[last_rework[status_column] == "fail"]
        
        rework_pass_count = rework_pass_sn[sn_column].nunique()
        rework_fail_count = rework_fail_sn[sn_column].nunique()

        # Retest Fail
        retest_fail_sn = (
            group.groupby(sn_column)
            .filter(lambda x: len(x) > 1 and x.iloc[-1][status_column] == "fail")
            .groupby(sn_column)
            .filter(lambda x: (x["Test Time"].max() - x["Test Time"].min()).days < 3)
        )
        retest_fail_count = retest_fail_sn[sn_column].nunique()

        return {
            "Total Tests": total_tests,
            "Unique SN Count": unique_sn_count,
            "1st Test Pass": first_test_pass,
            "Retest Pass": retest_pass_count,
            "True Fail": true_fail_count,
            "Rework Pass": rework_pass_count,  # Rework Pass count
            "Rework Fail": rework_fail_count,  # Rework Fail count
            "Retest Fail": retest_fail_count,
            "Retest Pass SN Data": retest_pass_sn,
            "True Fail SN Data": group[group[sn_column].isin(true_fail_sn[sn_column])],
            "Rework Pass SN Data": rework_pass_sn,  # Rework Pass data
            "Rework Fail SN Data": rework_fail_sn,  # Rework Fail data
            "Retest Fail SN Data": retest_fail_sn,
        }

    # Overall summary
    overall_summary = calculate_summary(data)

    # Summary of Retest Pass, True Fail, Rework, and Retest Fail
    def format_summary(group, status_column):
        summary = []
        for sn, sn_group in group.groupby(sn_column):
            details = []
            for i, (_, row) in enumerate(sn_group.iterrows(), 1):
                details.append(
                    f"@{row['Test Time'].strftime('%Y/%m/%d %H:%M:%S')} {i}st test {row[status_column].lower()}"
                )
            summary.append((sn, "<br>".join(details)))
        return pd.DataFrame(summary, columns=["SN", "Details"])

    retest_pass_summary = format_summary(overall_summary["Retest Pass SN Data"], status_column)
    true_fail_summary = format_summary(overall_summary["True Fail SN Data"], status_column)
    rework_summary = format_summary(overall_summary["Rework Pass SN Data"], status_column)  # Rework Pass
    rework_fail_summary = format_summary(overall_summary["Rework Fail SN Data"], status_column)  # Rework Fail
    retest_fail_summary = format_summary(overall_summary["Retest Fail SN Data"], status_column)

    # Display overall summary
    st.write("### Overall Summary:")
    for key, value in overall_summary.items():
        if key.endswith("Data"):
            continue  # Skip detailed data
        st.write(f"**{key}:** {value}")
        
    # Show Rework Pass and Rework Fail counts separately
    st.write(f"**Rework Pass Count:** {overall_summary['Rework Pass']}")
    st.write(f"**Rework Fail Count:** {overall_summary['Rework Fail']}")

    # Probe Type Summary (Optional)
    if probe_column != "Not Selected":
        st.write("### Probe Type Summary:")
        probe_summary = []
        for probe_type, group in data.groupby(probe_column):
            summary = calculate_summary(group)
            summary[probe_column] = probe_type
            probe_summary.append({k: v for k, v in summary.items() if not k.endswith("Data")})
        probe_summary_df = pd.DataFrame(probe_summary).set_index(probe_column)
        st.dataframe(probe_summary_df)

    # Allow user to download summaries and data as Excel
    with pd.ExcelWriter("summaries.xlsx", engine="xlsxwriter") as writer:
        if probe_column != "Not Selected":
            probe_summary_df.to_excel(writer, sheet_name="Probe Type Summary")
        overall_summary["Retest Pass SN Data"].to_excel(writer, sheet_name="Retest Pass SN", index=False)
        overall_summary["True Fail SN Data"].to_excel(writer, sheet_name="True Fail SN", index=False)
        overall_summary["Rework Pass SN Data"].to_excel(writer, sheet_name="Rework Pass SN", index=False)  # Rework Pass Data
        overall_summary["Rework Fail SN Data"].to_excel(writer, sheet_name="Rework Fail SN", index=False)  # Rework Fail Data
        overall_summary["Retest Fail SN Data"].to_excel(writer, sheet_name="Retest Fail SN", index=False)
        retest_pass_summary.to_excel(writer, sheet_name="Retest Pass Summary", index=False)
        true_fail_summary.to_excel(writer, sheet_name="True Fail Summary", index=False)
        rework_summary.to_excel(writer, sheet_name="Rework Pass Summary", index=False)  # Rework Pass Summary
        rework_fail_summary.to_excel(writer, sheet_name="Rework Fail Summary", index=False)  # Rework Fail Summary
        retest_fail_summary.to_excel(writer, sheet_name="Retest Fail Summary", index=False)
    
    with open("summaries.xlsx", "rb") as file:
        st.download_button(
            label="Download Summaries as Excel",
            data=file,
            file_name="summaries.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # Display raw data summaries
    st.write("### Retest Pass SN Raw Data:")
    st.dataframe(overall_summary["Retest Pass SN Data"])
    st.write("### Retest Fail SN Raw Data:")
    st.dataframe(overall_summary["Retest Fail SN Data"])     
    st.write("### True Fail SN Raw Data:")
    st.dataframe(overall_summary["True Fail SN Data"])
    st.write("### Rework Pass SN Raw Data:")
    st.dataframe(overall_summary["Rework Pass SN Data"])  # Display Rework Pass Raw Data
    st.write("### Rework Fail SN Raw Data:")
    st.dataframe(overall_summary["Rework Fail SN Data"])  # Display Rework Fail Raw Data
