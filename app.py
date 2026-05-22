import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- Page Configuration ---
st.set_page_config(page_title="Data Processing Dashboard", layout="wide")
st.title("📊 Automated Data Cleaning & Lookup Dashboard")
st.write("Upload your raw data and lookup sheets to automatically process according to system requirements.")

# --- Sidebar File Uploaders ---
st.sidebar.header("1. Upload Excel Files")
main_file = st.sidebar.file_uploader("Upload Main Sheet (.xls/.xlsx)", type=["xls", "xlsx"])
lookup_file = st.sidebar.file_uploader("Upload Lookup Source Sheet (.xls/.xlsx)", type=["xls", "xlsx"])

if main_file and lookup_file:
    # Read the uploaded Excel data sheets
    df_main = pd.read_excel(main_file)
    df_lookup = pd.read_excel(lookup_file)
    
    st.success("Both files uploaded successfully!")
    
    # --- PIPELINE STEP 1: ID LOOKUP & COLUMN INSERTION ---
    # Automatically grab up to the first 3 matching descriptive data columns from the lookup sheet
    lookup_cols = [col for col in df_lookup.columns if col != 'ID'][:3]
    df_processed = pd.merge(df_main, df_lookup[['ID'] + lookup_cols], on='ID', how='left')
    
    # Reorder columns dynamically to position the lookup branch data right after the ID column
    all_cols = list(df_processed.columns)
    for col in lookup_cols:
        all_cols.remove(col)
    new_order = [all_cols[0]] + lookup_cols + all_cols[1:]
    df_processed = df_processed[new_order]
    
    # --- PIPELINE STEP 2: APPLY FILTERS AND CLEANING RULES ---
    # 1. Strip out records containing any banned operational or compliance tags
    banned_tags = [
        "IBEX BONUS EXCLUSION", "selfexcluded", "Account Closure 25", 
        "Account Closure 26", "Syndicate Roulette", "Scam", "Withdrawal Scam", 
        "Syndicate Match - F", "voucher fraud", "Gambling Board Revocation", 
        "Syndicate Betgames", "Test Accounts", "Self Exclusion Gambling Board", 
        "Employee", "selfclosed", "Gambling Board"
    ]
    df_processed['Tags'] = df_processed['Tags'].astype(str)
    tag_condition = df_processed['Tags'].apply(lambda x: not any(tag in x for tag in banned_tags))
    df_processed = df_processed[tag_condition]
    
    # 2. Parse date strings safely to uniform backend datetimes for filtering calculations
    df_processed['Registered At'] = pd.to_datetime(df_processed['Registered At'], errors='coerce')
    
    # 3. Exclude records with an active exclusion date specified (retaining clean '-' cells)
    df_processed['Excluded Until_dt'] = pd.to_datetime(df_processed['Excluded Until'], errors='coerce')
    df_processed = df_processed[df_processed['Excluded Until_dt'].isna()]
    df_processed = df_processed.drop(columns=['Excluded Until_dt'])
    
    # 4. Enforce structural system validity flags
    df_processed = df_processed[df_processed['Reg. finished'].astype(str).str.lower() != 'no']
    df_processed = df_processed[df_processed['Disabled'].astype(str).str.lower() != 'yes']
    df_processed = df_processed[df_processed['Deleted'].astype(str).str.lower() != 'yes']
    
    # --- INTERACTIVE DASHBOARD FILTERS (SIDEBAR) ---
    st.sidebar.header("2. Interactive Date Filter")
    min_date = df_processed['Registered At'].min() if not df_processed['Registered At'].isna().all() else datetime(2020, 1, 1)
    max_date = df_processed['Registered At'].max() if not df_processed['Registered At'].isna().all() else datetime(2026, 12, 31)
    
    start_date = st.sidebar.date_input("Start Date", min_date)
    end_date = st.sidebar.date_input("End Date", max_date)
    
    # Set the time bounds perfectly (Midnight to final second of the day)
    start_datetime = pd.to_datetime(start_date)
    end_datetime = pd.to_datetime(end_date).replace(hour=23, minute=59, second=59)
    
    # Apply interactive window selection
    df_final = df_processed[
        (df_processed['Registered At'] >= start_datetime) & 
        (df_processed['Registered At'] <= end_datetime)
    ]
    
    # --- METRICS & VISUALS ---
    st.subheader("Data Overview Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Original Rows Loaded", len(df_main))
    col2.metric("Cleaned Rows (After Logic)", len(df_processed))
    col3.metric("Filtered Rows (Selected Date Range)", len(df_final))
    
    st.write("---")
    
    # --- INTERACTIVE DISPLAY DATA ---
    st.subheader("Interactive Preview (Processed & Filtered Data)")
    
    # Create a local copy for preview presentation styling
    df_preview = df_final.copy()
    if 'Registered At' in df_preview.columns:
        df_preview['Registered At'] = df_preview['Registered At'].dt.strftime('%d/%m/%Y %H:%M')
        
    st.dataframe(df_preview, use_container_width=True)
    
    # --- DOWNLOAD FINAL EXCEL PRODUCT WITH EXPLICIT DATE FIX ---
    @st.cache_data
    def convert_df_to_excel(df_input):
        excel_output = io.BytesIO()
        df_excel = df_input.copy()
        
        # FIX: Explicitly enforce standard Day/Month/Year text injection to satisfy Excel f(x) layout rules
        if 'Registered At' in df_excel.columns:
            df_excel['Registered At'] = pd.to_datetime(df_excel['Registered At'], errors='coerce').dt.strftime('%d/%m/%Y')
            
        with pd.ExcelWriter(excel_output, engine='openpyxl') as writer:
            df_excel.to_excel(writer, index=False, sheet_name='Cleaned Operations Data')
            
        return excel_output.getvalue()

    final_excel_bytes = convert_df_to_excel(df_final)
    
    st.write("---")
    st.download_button(
        label="📥 Download Processed Data as Excel (.xlsx)",
        data=final_excel_bytes,
        file_name=f"Cleaned_Branch_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Please upload both the Main Sheet and the Lookup Source Sheet in the sidebar to begin.")