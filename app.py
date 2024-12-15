import hashlib
import pandas as pd
import streamlit as st
from collections import Counter
import chardet  # Library for encoding detection

# --- Base Functions ---
def generate_hash(value):
    """Generate a unique hash for a given value."""
    return hashlib.md5(value.encode('utf-8')).hexdigest()

def detect_encoding(file_content):
    """Detects the encoding of a file content."""
    result = chardet.detect(file_content)
    return result['encoding']

def import_data(uploaded_files):
    """Import data from uploaded files (XLSX, XLS, or CSV)."""
    data = []
    for uploaded_file in uploaded_files:
        try:
            if uploaded_file.name.endswith(('.xls', '.xlsx')):
                # Read Excel file using pandas (handles multi-language data well)
                df = pd.read_excel(uploaded_file)
                data.extend(df.values.tolist())  # Convert data to list
            elif uploaded_file.name.endswith('.csv'):
                # Read CSV file with automatic encoding detection
                raw_content = uploaded_file.read()
                encoding = detect_encoding(raw_content)
                
                # Decode the raw content with the detected encoding
                decoded_content = raw_content.decode(encoding)

                # Read CSV
                from io import StringIO
                csv_data = StringIO(decoded_content)
                reader = pd.read_csv(csv_data)
                data.extend(reader.values.tolist())
            else:
                st.error(f"Unsupported file format: {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error importing {uploaded_file.name}: {e}")
    return data

def detect_duplicates(data, column_index):
    """Detect duplicates in a specific column of the data."""
    column_data = [row[column_index] for row in data if len(row) > column_index]
    hashed_data = [generate_hash(str(item)) for item in column_data]
    occurrences = Counter(hashed_data)
    duplicates = {hash_value: count for hash_value, count in occurrences.items() if count > 1}
    return duplicates

def remove_duplicates(data, column_index):
    """Remove duplicates from a specific column, keeping only the last occurrence."""
    seen_hashes = set()
    unique_data = []
    data_reversed = reversed(data)  # Iterate from the last row to the first

    for row in data_reversed:
        if len(row) > column_index:
            item_hash = generate_hash(str(row[column_index]))
            if item_hash not in seen_hashes:
                seen_hashes.add(item_hash)
                unique_data.append(row)

    # Reverse the result back to original order
    unique_data.reverse()
    return unique_data

def generate_report(duplicates, data, column_index):
    """Generate a detailed report of duplicates with line numbers."""
    reverse_lookup = {}
    line_numbers = {}
    
    for idx, row in enumerate(data):
        if len(row) > column_index:
            item_hash = generate_hash(str(row[column_index]))
            value = row[column_index]
            if item_hash in duplicates:
                reverse_lookup[item_hash] = value
                if item_hash not in line_numbers:
                    line_numbers[item_hash] = []
                line_numbers[item_hash].append(idx + 1)  # Line number starts at 1
                
    report_data = []
    for hash_value, count in duplicates.items():
        report_data.append({
            "Value": reverse_lookup[hash_value],
            "Count": count,
            "Line Numbers": ", ".join(map(str, line_numbers[hash_value]))
        })
        
    return pd.DataFrame(report_data)

def save_data(data, file_name):
    """Save data in either CSV or Excel format based on the file extension."""
    df = pd.DataFrame(data)
    if file_name.endswith('.xlsx'):
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        return output.getvalue()
    elif file_name.endswith('.csv'):
        return df.to_csv(index=False).encode("utf-8")

# --- Streamlit Interface ---
st.title("Duplicate Detection and Removal System")
st.write("This application detects and removes duplicates from XLS, XLSX, or CSV files.")

# File upload (Only accept XLS, XLSX, and CSV)
uploaded_files = st.file_uploader("Upload your files (XLS, XLSX, or CSV)", accept_multiple_files=True, type=["xls", "xlsx", "csv"])

if uploaded_files:
    file_names = [file.name for file in uploaded_files]
    st.write(f"Selected files: {', '.join(file_names)}")

    # Import data from uploaded files
    data = import_data(uploaded_files)

    # Display a sample of the data
    if data:
        st.write("Preview of imported data:")
        st.dataframe(data[:10])  # Display the first 10 rows

        # Column selection
        column_index = st.number_input("Column number to process (1 for the first column)", min_value=1, step=1) - 1

        if st.button("Detect and Remove Duplicates"):
            if column_index < 0 or column_index >= len(data[0]):
                st.error("The selected column does not exist.")
            else:
                # Detect duplicates
                duplicates = detect_duplicates(data, column_index)

                if duplicates:
                    report_df = generate_report(duplicates, data, column_index)
                    st.subheader("Duplicate Detection Report")
                    st.table(report_df)  # Display the report as a table

                    # Remove duplicates
                    unique_data = remove_duplicates(data, column_index)

                    # Save data without duplicates
                    file_name = f"data_without_duplicates.xlsx"
                    processed_data = save_data(unique_data, file_name)
                    st.download_button(f"Download data without duplicates", data=processed_data, file_name=file_name, mime="application/octet-stream")
                else:
                    st.info("No duplicates detected.")
