from ExtractTable import ExtractTable
import pandas as pd
import streamlit as st

class TableExtractor:
    def __init__(self, api_key):
        self.et_sess = ExtractTable(api_key=api_key)
        self.extracted_tables = {}
        
    def extract_from_image(self, image_path, page_num):
        """Extract table from a single image"""
        try:
            # Process the file and get output
            table_data = self.et_sess.process_file(
                filepath=image_path,
                output_format="df"
            )
            
            # Convert to DataFrame if it's a list
            if isinstance(table_data, list):
                if len(table_data) > 0:
                    # Take the first table if multiple tables are detected
                    if isinstance(table_data[0], pd.DataFrame):
                        table_data = table_data[0]
                    else:
                        # Convert list of lists to DataFrame
                        table_data = pd.DataFrame(table_data)
                else:
                    # Create empty DataFrame if no tables found
                    table_data = pd.DataFrame()
            
            # Store the extracted table
            self.extracted_tables[f"page_{page_num}"] = table_data
            return table_data
            
        except Exception as e:
            st.error(f"Error extracting table from page {page_num}: {str(e)}")
            return pd.DataFrame()  # Return empty DataFrame on error

    def display_table_editor(self, page_num):
        """Display and allow editing of extracted table"""
        table_key = f"page_{page_num}"
        if table_key in self.extracted_tables:
            df = self.extracted_tables[table_key]
            
            # Ensure we have a DataFrame
            if not isinstance(df, pd.DataFrame):
                df = pd.DataFrame(df)
            
            # Create an editable dataframe
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                key=f"table_editor_{page_num}"
            )
            
            # Update stored table with edits
            self.extracted_tables[table_key] = edited_df
            
            # Add export button
            if st.button(f"Export Page {page_num} to CSV"):
                edited_df.to_csv(f"table_page_{page_num}.csv", index=False)
                st.success(f"Table from page {page_num} exported to CSV!")
                
    def export_all_tables(self):
        """Export all tables to CSV files"""
        for page_key, df in self.extracted_tables.items():
            page_num = page_key.split('_')[1]
            if isinstance(df, pd.DataFrame):
                df.to_csv(f"table_page_{page_num}.csv", index=False)
        st.success("All tables exported to CSV!") 