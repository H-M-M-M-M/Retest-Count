import pandas as pd
import streamlit as st

# Title
st.title("Test Data Analysis App")

# Upload Excel file
uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file:
    # Load data
    data = pd.read_excel(uploaded_file)

    # Strip leading/trailing spaces from column names
    data.columns = data.columns.str.strip()

    # Display raw data
    st.write("Uploaded Test Data:")
    st.dataframe(data.head())

    # Select columns
    columns = ["Not Selected"] + data.columns.tolist()
    sn_column = st.selectbox("Select SN Column", columns, index=0)
    date_column = st.selectbox("Select Test Date Column", columns, index=0)
    time_column = st.selectbox("Select Test Time Column", columns, index=0)
    status_column = st.selectbox("Select Test Status Column", columns, index=0)

    if "Not Selected" in [sn_column, date_column, time_column, status_column]:
        st.warning("Please select all required columns!")
        st.stop()

    # Strip spaces from selected columns
    for col in [sn_column, date_column, time_column, status_column]:
        data[col] = data[col].astype(str).str.strip()

    # Combine date and time into a single datetime column
    data["Test Time"] = pd.to_datetime(
        data[date_column].astype(str) + " " + data[time_column].astype(str), errors="coerce"
    )
    if data["Test Time"].isna().any():
        st.error("Invalid date or time detected. Please check your data!")
        st.stop()

    # Sort data by SN and Test Time
    data = data.sort_values(by=[sn_column, "Test Time"]).reset_index(drop=True)

    # Total Tests
    total_tests = len(data)
    unique_sn_count = data[sn_column].nunique()

    # 1st Test Pass
    first_test = data.drop_duplicates(subset=[sn_column], keep="first")
    first_test_pass = first_test[first_test[status_column].str.lower() == "pass"][sn_column].nunique()

    # Retest Pass
    retest_pass_sn = (
        data.groupby(sn_column)
        .filter(lambda x: len(x) > 1 and x.iloc[-1][status_column].lower() == "pass")
        .groupby(sn_column)
        .filter(lambda x: (x["Test Time"].max() - x["Test Time"].min()).days < 3)
    )
    retest_pass_count = retest_pass_sn[sn_column].nunique()

    # True Fail
    latest_test = data.drop_duplicates(subset=[sn_column], keep="last")
    true_fail_sn = latest_test[latest_test[status_column].str.lower() == "fail"]
    true_fail_count = true_fail_sn[sn_column].nunique()

    # Rework
    rework_sn = (
        data.groupby(sn_column)
        .filter(lambda x: len(x) > 1 and (x["Test Time"].max() - x["Test Time"].min()).days > 3)
    )
    rework_count = rework_sn[sn_column].nunique()

    # Display summary statistics
    st.write("### Summary:")
    st.write(f"**Total Tests:** {total_tests}")
    st.write(f"**Unique SN Count:** {unique_sn_count}")
    st.write(f"**1st Test Pass:** {first_test_pass}")
    st.write(f"**Retest Pass:** {retest_pass_count}")
    st.write(f"**True Fail:** {true_fail_count}")
    st.write(f"**Rework:** {rework_count}")

    # Summary of Retest Pass, True Fail, and Rework
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

    # Format summaries for Retest Pass, True Fail, and Rework
    retest_pass_summary = format_summary(retest_pass_sn, status_column)
    true_fail_summary = format_summary(true_fail_sn, status_column)
    rework_summary = format_summary(rework_sn, status_column)

    # Function to render two-column table
    def render_summary(summary, title):
        st.write(f"### {title}")
        table = "<table style='width:100%; border-collapse: collapse;'>"
        table += "<tr><th style='text-align:left;'>SN</th><th style='text-align:left;'>Details</th></tr>"
        for _, row in summary.iterrows():
            table += f"<tr><td style='vertical-align:top;'>{row['SN']}</td><td>{row['Details']}</td></tr>"
        table += "</table>"
        st.markdown(table, unsafe_allow_html=True)

    # Allow user to download summaries and data as Excel
    with pd.ExcelWriter("summaries.xlsx", engine="xlsxwriter") as writer:
        retest_pass_sn.to_excel(writer, sheet_name="Retest Pass", index=False)
        true_fail_sn.to_excel(writer, sheet_name="True Fail", index=False)
        rework_sn.to_excel(writer, sheet_name="Rework", index=False)
        retest_pass_summary.to_excel(writer, sheet_name="Retest Pass Summary", index=False)
        true_fail_summary.to_excel(writer, sheet_name="True Fail Summary", index=False)
        rework_summary.to_excel(writer, sheet_name="Rework Summary", index=False)

    with open("summaries.xlsx", "rb") as file:
        st.download_button(
            label="Download Summaries as Excel",
            data=file,
            file_name="summaries.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    # Display source data for Retest Pass, True Fail, and Rework
    st.write("### Retest Pass SN Raw Data:")
    st.dataframe(retest_pass_sn)

    st.write("### True Fail SN Raw Data:")
    st.dataframe(true_fail_sn)

    st.write("### Rework SN Raw Data:")
    st.dataframe(rework_sn)
    
    # Display summaries
    render_summary(retest_pass_summary, "Retest Pass SN Summary")
    render_summary(true_fail_summary, "True Fail SN Summary")
    render_summary(rework_summary, "Rework SN Summary")
