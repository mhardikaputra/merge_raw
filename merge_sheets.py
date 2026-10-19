import os
import json
import re
import time
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# Helper function: Automatically convert US formatted text numbers to float
def clean_us_number(val):
    if not isinstance(val, str):
        return val
    val_str = val.strip().replace('\xa0', '')
    if not val_str:
        return ''
    
    # US format with thousands commas e.g. 1,234,567.89
    if re.match(r'^-?\s*\$?\s*\d{1,3}(,\d{3})+(\.\d+)?$', val_str):
        clean_val = re.sub(r'[\$\s,]', '', val_str)
        try:
            return float(clean_val)
        except ValueError:
            return val
            
    # Standard dot-decimal e.g. 1234567.89
    if re.match(r'^-?\s*\$?\s*\d+(\.\d+)?$', val_str):
        clean_val = re.sub(r'[\$\s]', '', val_str)
        try:
            return float(clean_val)
        except ValueError:
            return val
            
    return val

# Helper function: Automatically convert Indonesian formatted text numbers to float
def clean_id_number(val):
    if not isinstance(val, str):
        return val
    val_str = val.strip().replace('\xa0', '')
    if not val_str:
        return ''
    
    # Indonesian format with dots as thousands and comma as decimal (e.g. 239.443.200,00)
    if re.match(r'^-?\s*(Rp)?\s*\d{1,3}(\.\d{3})+,\d+$', val_str, re.IGNORECASE):
        clean_val = re.sub(r'[Rp\s]', '', val_str, flags=re.IGNORECASE).replace('.', '').replace(',', '.')
        try:
            return float(clean_val)
        except ValueError:
            return val
            
    # Indonesian format with dots as thousands, no decimal (e.g. 239.443.200)
    if re.match(r'^-?\s*(Rp)?\s*\d{1,3}(\.\d{3})+$', val_str, re.IGNORECASE):
        clean_val = re.sub(r'[Rp\s]', '', val_str, flags=re.IGNORECASE).replace('.', '')
        try:
            return float(clean_val)
        except ValueError:
            return val
            
    # Indonesian format with comma as decimal, no thousands dots (e.g. 239443200,00)
    if re.match(r'^-?\s*(Rp)?\s*\d+,\d+$', val_str, re.IGNORECASE):
        clean_val = re.sub(r'[Rp\s]', '', val_str, flags=re.IGNORECASE).replace(',', '.')
        try:
            return float(clean_val)
        except ValueError:
            return val
            
    return val

# 1. Load credentials securely from GitHub Secret
creds_json = os.environ.get('GCP_CREDENTIALS')
creds_dict = json.loads(creds_json)

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

# 2. Connect to the sheets
sheet1 = client.open_by_url("https://docs.google.com/spreadsheets/d/1a6gdPuWWeIqcdw5YnUQBHppHt_OkZ2yNw_Fi5iPhSvg/edit?gid=0#gid=0").worksheet("Raw Data")
sheet2 = client.open_by_url("https://docs.google.com/spreadsheets/d/1s8Xzfr3OdD1Ty3HScdVUB9bNHQxXtwGf0N7HnztNFfM/edit?gid=1179090678#gid=1179090678").worksheet("RAW DATA")
dest_sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1VfbKcNo8In9poUbsKKnZ-xjD3WZ3u0iXV6fKiR8OU6o/edit?gid=0#gid=0").worksheet("Merged Raw")

# 3. Pull data
print("Downloading data...")
data1 = sheet1.get_all_values()
data2 = sheet2.get_all_values()

# Create DataFrames
df1 = pd.DataFrame(data1[8808:], columns=data1[0])
df2 = pd.DataFrame(data2[1:], columns=data2[0])

# --- AUTOMATIC NUMBER FORMAT CLEANING ---
print("Automatically detecting and converting number formats across all columns...")
for col in df1.columns:
    df1[col] = df1[col].apply(clean_us_number)

for col in df2.columns:
    df2[col] = df2[col].apply(clean_id_number)
# ----------------------------------------

merged_df = pd.concat([df1, df2], ignore_index=True)

# --- STRICT CLEANUP BASED ON COLUMN B ---
print("Cleaning out blank rows...")
col_b_name = merged_df.columns[1]

merged_df = merged_df[
    (merged_df[col_b_name].astype(str).str.strip() != '') & 
    (merged_df[col_b_name].astype(str).str.lower() != 'nan') &
    (merged_df[col_b_name].astype(str).str.lower() != 'none')
]

merged_df.reset_index(drop=True, inplace=True)
merged_df.fillna('', inplace=True)
# ----------------------------------------

# 4. Resize destination sheet to fit total rows
total_rows_needed = len(merged_df) + 1
print(f"Resizing destination sheet to {total_rows_needed} rows...")

current_rows = dest_sheet.row_count
if total_rows_needed > current_rows:
    dest_sheet.add_rows(total_rows_needed - current_rows)

# 5. Upload to destination in chunks
print(f"Preparing to upload {len(merged_df)} rows...")
upload_data = [merged_df.columns.values.tolist()] + merged_df.values.tolist()
dest_sheet.clear()

chunk_size = 10000
for i in range(0, len(upload_data), chunk_size):
    chunk = upload_data[i:i + chunk_size]
    start_row = i + 1
    
    dest_sheet.update(range_name=f'A{start_row}', values=chunk)
    print(f"Uploaded rows {start_row} to {start_row + len(chunk) - 1}")
    time.sleep(2)

print("Success! Sheets merged and uploaded with standardized numbers.")
