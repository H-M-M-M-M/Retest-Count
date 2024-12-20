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
    probe_column = st.selectbox("Select Probe Type Column (Optional)", columns, index=0)

    if "Not Selected" in [sn_column, date_column, time_column, status_column]:
        st.warning("Please select all required columns!")
        st.stop()

    # Strip spaces from selected columns
    for col in [sn_column, date_column, time_column, status_column, probe_column]:
        if col != "Not Selected":
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

    # Helper function to calculate summary
    def calculate_summary(group):
        total_tests = len(group)
        unique_sn_count = group[sn_column].nunique()

        # 1st Test Pass
        first_test = group.drop_duplicates(subset=[sn_column], keep="first")
        first_test_pass = first_test[first_test[status_column].str.lower() == "pass"][sn_column].nunique()

        # Retest Pass
        retest_pass_sn = (
            group.groupby(sn_column)
            .filter(lambda x: len(x) > 1 and x.iloc[-1][status_column].lower() == "pass")
            .groupby(sn_column)
            .filter(lambda x: (x["Test Time"].max() - x["Test Time"].min()).days < 3)
        )
        retest_pass_count = retest_pass_sn[sn_column].nunique()

        # True Fail
        latest_test = group.drop_duplicates(subset=[sn_column], keep="last")
        true_fail_sn = latest_test[latest_test[status_column].str.lower() == "fail"]
        true_fail_count = true_fail_sn[sn_column].nunique()

        # Rework
        rework_sn = (
            group.groupby(sn_column)
            .filter(lambda x: len(x) > 1 and (x["Test Time"].max() - x["Test Time"].min()).days > 3)
        )
        rework_count = rework_sn[sn_column].nunique()

        return {
            "Total Tests": total_tests,
            "Unique SN Count": unique_sn_count,
            "1st Test Pass": first_test_pass,
            "Retest Pass": retest_pass_count,
            "True Fail": true_fail_count,
            "Rework": rework_count,
            "Retest Pass SN Data": retest_pass_sn,
            "True Fail SN Data": group[group[sn_column].isin(true_fail_sn[sn_column])],
            "Rework SN Data": rework_sn,
        }

    # Overall summary
    overall_summary = calculate_summary(data)

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

    retest_pass_summary = format_summary(overall_summary["Retest Pass SN Data"], status_column)
    true_fail_summary = format_summary(overall_summary["True Fail SN Data"], status_column)
    rework_summary = format_summary(overall_summary["Rework SN Data"], status_column)

    # Display overall summary
    st.write("### Overall Summary:")
    for key, value in overall_summary.items():
        if key.endswith("Data"):
            continue  # Skip detailed data
        st.write(f"**{key}:** {value}")
        
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
        #data.to_excel(writer, sheet_name="Full Data", index=False)
        overall_summary["Retest Pass SN Data"].to_excel(writer, sheet_name="Retest Pass SN", index=False)
        overall_summary["True Fail SN Data"].to_excel(writer, sheet_name="True Fail SN", index=False)
        overall_summary["Rework SN Data"].to_excel(writer, sheet_name="Rework SN", index=False)
        retest_pass_summary.to_excel(writer, sheet_name="Retest Pass Summary", index=False)
        true_fail_summary.to_excel(writer, sheet_name="True Fail Summary", index=False)
        rework_summary.to_excel(writer, sheet_name="Rework Summary", index=False)
        writer.save()

    with open("summaries.xlsx", "rb") as file:
        st.download_button(
            label="Download Summaries as Excel",
            data=file,
            file_name="summaries.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # Display Retest Pass, True Fail, and Rework raw data
    st.write("### Retest Pass SN Raw Data:")
    st.dataframe(overall_summary["Retest Pass SN Data"])

    st.write("### True Fail SN Raw Data:")
    st.dataframe(overall_summary["True Fail SN Data"])

    st.write("### Rework SN Raw Data:")
    st.dataframe(overall_summary["Rework SN Data"])

    # Display summaries
    def render_summary(summary, title):
        st.write(f"### {title}")
        table = "<table style='width:100%; border-collapse: collapse;'>"
        table += "<tr><th style='text-align:left;'>SN</th><th style='text-align:left;'>Details</th></tr>"
        for _, row in summary.iterrows():
            table += f"<tr><td style='vertical-align:top;'>{row['SN']}</td><td>{row['Details']}</td></tr>"
        table += "</table>"
        st.markdown(table, unsafe_allow_html=True)

    render_summary(retest_pass_summary, "Retest Pass SN Summary")
    render_summary(true_fail_summary, "True Fail SN Summary")
    render_summary(rework_summary, "Rework SN Summary")

