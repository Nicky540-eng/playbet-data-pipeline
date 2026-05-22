import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Data Processing Dashboard", layout="wide")
st.title("📊 Automated Data Cleaning & Lookup Dashboard")
st.write("Upload your raw data and lookup sheets to automatically process according to system requirements.")

# --- FILE UPLOADAERS ---
st.sidebar.header("1. Upload Excel Files")
main_file = st.sidebar.file_uploader("Upload Main Sheet (.xls/.xlsx)", type=["xls", "xlsx"])
lookup_file = st.sidebar.file_uploader("Upload Lookup Source Sheet (.xls/.xlsx)", type=["xls", "xlsx"])

if main_file and lookup_file:
    # Load data into dataframes
    df_main = pd.read_excel(main_file)
    df_lookup = pd.read_excel(lookup_file)
    
    st.success("Both files uploaded successfully!")
    
    # --- PIPELINE STEP 1: ID LOOKUP & COLUMN INSERTION ---
    # Assuming lookup sheet has 'ID' as the key and 3 other columns to bring over
    # We find columns that are in lookup but not 'ID' to merge safely
    lookup_cols = [col for col in df_lookup.columns if col != 'ID'][:3]
    
    # Perform the lookup (Left join on ID)
    df_processed = pd.merge(df_main, df_lookup[['ID'] + lookup_cols], on='ID', how='left')
    
    # Reorder columns to insert the 3 new lookup columns right after 'ID' (Column A)
    all_cols = list(df_processed.columns)
    # Remove the lookup columns from their default end-position
    for col in lookup_cols:
        all_cols.remove(col)
    # Insert them right after 'ID' (index 1)
    new_order = [all_cols[0]] + lookup_cols + all_cols[1:]
    df_processed = df_processed[new_order]
    
    # --- PIPELINE STEP 2: APPLY FILTERS AND CLEANING RULES ---
    
    # 1. Tags cleaning rule
    banned_tags = [
        "IBEX BONUS EXCLUSION", "selfexcluded", "Account Closure 25", 
        "Account Closure 26", "Syndicate Roulette", "Scam", "Withdrawal Scam", 
        "Syndicate Match - F", "voucher fraud", "Gambling Board Revocation", 
        "Syndicate Betgames", "Test Accounts", "Self Exclusion Gambling Board", 
        "Employee", "selfclosed", "Gambling Board"
    ]
    # Ensure tags are string data type before filtering
    df_processed['Tags'] = df_processed['Tags'].astype(str)
    # Keep rows where 'Tags' DO NOT contain any of the banned phrases
    tag_condition = df_processed['Tags'].apply(lambda x: not any(tag in x for tag in banned_tags))
    df_processed = df_processed[tag_condition]
    
    # 2. Ensure Registered At is an actual datetime object
    df_processed['Registered At'] = pd.to_datetime(df_processed['Registered At'], errors='coerce')
    
    # 3. Remove if 'Excluded Until' has a date (Keep only NaT/blank or text markers like '-')
    df_processed['Excluded Until_dt'] = pd.to_datetime(df_processed['Excluded Until'], errors='coerce')
    df_processed = df_processed[df_processed['Excluded Until_dt'].isna()]
    df_processed = df_processed.drop(columns=['Excluded Until_dt']) # drop temporary helper column
    
    # 4. Remove 'No' from Reg. finished
    df_processed = df_processed[df_processed['Reg. finished'].astype(str).str.lower() != 'no']
    
    # 5. Remove 'Yes' from Disabled
    df_processed = df_processed[df_processed['Disabled'].astype(str).str.lower() != 'yes']
    
    # 6. Remove 'Yes' from Deleted
    df_processed = df_processed[df_processed['Deleted'].astype(str).str.lower() != 'yes']
    
    
    # --- INTERACTIVE DASHBOARD FILTERS (SIDEBAR) ---
    st.sidebar.header("2. Interactive Date Filter")
    
    # Fallbacks for minimum and maximum dates in the dataset
    min_date = df_processed['Registered At'].min() if not df_processed['Registered At'].isna().all() else datetime(2020, 1, 1)
    max_date = df_processed['Registered At'].max() if not df_processed['Registered At'].isna().all() else datetime(2026, 12, 31)
    
    # Date Pickers
    start_date = st.sidebar.date_input("Start Date", min_date)
    end_date = st.sidebar.date_input("End Date", max_date)
    
    # Convert date inputs to datetime for matching dataframe column
    start_datetime = pd.to_datetime(start_date)
    end_datetime = pd.to_datetime(end_date).replace(hour=23, minute=59, second=59)
    
    # Apply user interactive date range filtering
    df_final = df_processed[
        (df_processed['Registered At'] >= start_datetime) & 
        (df_processed['Registered At'] <= end_datetime)
    ]
    
    # --- METRICS & VISUALS ---
    st.subheader("Data Overview Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Original Rows", len(df_main))
    col2.metric("Cleaned Rows (After Logic)", len(df_processed))
    col3.metric("Filtered Rows (Selected Date Range)", len(df_final))
    
    st.write("---")
    
    # Display preview table
    st.subheader("Interactive Preview (Processed & Filtered Data)")
    st.dataframe(df_final.head(100), use_container_width=True)
    
    # --- DOWNLOAD BUTTON ---
    # Convert filtered DataFrame back to an Excel file format in-memory
    @st.cache_data
    def convert_df_to_excel(df):
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cleaned Data')
        return output.getvalue()
    
    excel_data = convert_df_to_excel(df_final)
    
    st.download_button(
        label="📥 Download Processed Data as Excel (.xlsx)",
        data=excel_data,
        file_name=f"Cleaned_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Please upload both the Main Sheet and the Lookup Source Sheet in the sidebar to begin.")