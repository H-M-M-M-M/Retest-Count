import pandas as pd
import streamlit as st

# Title
st.title("Test Data Analysis App")

# Upload Excel file
uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file:
    # Load data
    data = pd.read_excel(uploaded_file)

    # Display raw data
    st.write("Uploaded Test Data:")
    st.dataframe(data.head())

    # Select columns for analysis
    columns = ["Not Selected"] + data.columns.tolist()
    sn_column = st.selectbox("Select SN Column", columns, index=0)
    date_column = st.selectbox("Select Test Date Column", columns, index=0)
    time_column = st.selectbox("Select Test Time Column", columns, index=0)
    status_column = st.selectbox("Select Test Status Column", columns, index=0)

    # If not all columns are selected, prompt the user
    if "Not Selected" in [sn_column, date_column, time_column, status_column]:
        st.warning("Please select all required columns!")
        st.stop()

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

    # Retest Pass: Test if the last record is a pass, and the time difference between tests is < 3 days
    retest_pass_sn = (
        data.groupby(sn_column)
        .filter(lambda x: len(x) > 1 and x.iloc[-1][status_column].lower() == "pass")
        .groupby(sn_column)
        .filter(lambda x: (x["Test Time"].max() - x["Test Time"].min()).days < 3)
    )
    retest_pass_count = retest_pass_sn[sn_column].nunique()

    # True Fail: Filter out last tests that are fail and count them based on their first test date
    latest_test = data.drop_duplicates(subset=[sn_column], keep="last")
    true_fail_sn = latest_test[latest_test[status_column].str.lower() == "fail"]
    true_fail_count = true_fail_sn[sn_column].nunique()

    # Rework: Filter out SNs that have more than one test with a time gap > 3 days
    rework_sn = (
        data.groupby(sn_column)
        .filter(lambda x: len(x) > 1 and (x["Test Time"].max() - x["Test Time"].min()).days > 3)
    )
    rework_count = rework_sn[sn_column].nunique()

    # Function to format SN test details
    def format_summary(group, status_column):
        summary = []
        for sn, sn_group in group.groupby(sn_column):
            details = []
            for i, (_, row) in enumerate(sn_group.iterrows(), 1):
                details.append(
                    f"@{row['Test Time'].strftime('%Y/%m/%d %H:%M:%S')} {i}st test {row[status_column].lower()}"
                )
            summary.append(f"{sn} test {len(details)} times\n" + "\n".join(details))
        return "\n".join(summary)

    # Format summaries for Retest Pass, True Fail, and Rework
    retest_pass_summary = format_summary(retest_pass_sn, status_column)
    true_fail_summary = format_summary(true_fail_sn, status_column)
    rework_summary = format_summary(rework_sn, status_column)

    # Display summary
    st.write("### Summary:")
    st.write(f"**Total Tests:** {total_tests}")
    st.write(f"**Unique SN Count:** {unique_sn_count}")
    st.write(f"**1st Test Pass:** {first_test_pass}")
    st.write(f"**Retest Pass:** {retest_pass_count}")
    st.write(f"**True Fail:** {true_fail_count}")
    st.write(f"**Rework:** {rework_count}")

    # Display detailed summaries for Retest Pass, True Fail, and Rework
    st.write("### Retest Pass SN Summary:")
    st.text(retest_pass_summary)

    st.write("### True Fail SN Summary:")
    st.text(true_fail_summary)

    st.write("### Rework SN Summary:")
    st.text(rework_summary)

    # Display source data for Retest Pass, True Fail, and Rework
    st.write("### Retest Pass SN Data:")
    st.dataframe(retest_pass_sn)

    st.write("### True Fail SN Data:")
    st.dataframe(true_fail_sn)

    st.write("### Rework SN Data:")
    st.dataframe(rework_sn)
