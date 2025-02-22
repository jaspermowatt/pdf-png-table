import streamlit as st
from streamlit_cropper import st_cropper
from streamlit_image_coordinates import streamlit_image_coordinates
from pdf_processor import PDFProcessor
import tempfile
import os
import numpy as np
from PIL import Image
from table_extractor import TableExtractor
from ExtractTable import ExtractTable
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def show_review_page(processor, gridlines):
    st.title("Review All Pages")
    
    # Initialize ExtractTable
    if not hasattr(st.session_state, 'extractor'):
        st.session_state.extractor = initialize_extractor()
    
    # Display all processed pages with their gridlines
    for page_num in range(len(st.session_state.pages)):
        st.subheader(f"Page {page_num + 1}")
        
        page_key = f"page_{page_num}"
        page_gridlines = gridlines.get(page_key, [])
        
        if page_key in st.session_state.processed_pages:
            processor.current_image = st.session_state.processed_pages[page_key]
            
            # Show image and table side by side
            col1, col2 = st.columns(2)
            with col1:
                image = processor.get_display_image(gridlines=page_gridlines)
                st.image(Image.fromarray(image), use_container_width=True)
                
                # Gridline controls
                st.write("Edit Gridlines:")
                if page_gridlines:
                    for i, x in enumerate(sorted(page_gridlines)):
                        col_a, col_b = st.columns([4, 1])
                        with col_a:
                            st.write(f"Line at x={int(x)}")
                        with col_b:
                            if st.button("❌", key=f"del_{page_num}_{i}", help="Delete gridline"):
                                page_gridlines.remove(x)
                                st.rerun()
            
            with col2:
                if hasattr(st.session_state, 'extractor'):
                    # Extract and display table
                    temp_path = f"temp_page_{page_num}.png"
                    Image.fromarray(image).save(temp_path)
                    
                    try:
                        table_data = st.session_state.extractor.process_file(
                            filepath=temp_path,
                            output_format="df"
                        )
                        if isinstance(table_data, list):
                            for idx, df in enumerate(table_data):
                                st.write(f"Table {idx + 1}")
                                st.dataframe(df)
                        else:
                            st.dataframe(table_data)
                    except Exception as e:
                        st.error(f"Error extracting table: {str(e)}")
                    finally:
                        os.remove(temp_path)

    # Save buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save All Images"):
            for page_num in range(len(st.session_state.pages)):
                page_key = f"page_{page_num}"
                if page_key in st.session_state.processed_pages:
                    processor.current_image = st.session_state.processed_pages[page_key]
                    processor.save_image(
                        gridlines=gridlines.get(page_key, []),
                        filename=f'output_page_{page_num + 1}.png'
                    )
            st.success("All images saved successfully!")
    
    with col2:
        if hasattr(st.session_state, 'extractor'):
            if st.button("Export All Tables"):
                all_tables = []
                for page_num in range(len(st.session_state.pages)):
                    temp_path = f"temp_page_{page_num}.png"
                    page_key = f"page_{page_num}"
                    if page_key in st.session_state.processed_pages:
                        processor.current_image = st.session_state.processed_pages[page_key]
                        image = processor.get_display_image(gridlines=gridlines.get(page_key, []))
                        Image.fromarray(image).save(temp_path)
                        try:
                            tables = st.session_state.extractor.process_file(
                                filepath=temp_path,
                                output_format="df"
                            )
                            if isinstance(tables, list):
                                all_tables.extend(tables)
                            else:
                                all_tables.append(tables)
                        finally:
                            os.remove(temp_path)
                
                # Save all tables to Excel
                with pd.ExcelWriter('extracted_tables.xlsx') as writer:
                    for idx, df in enumerate(all_tables):
                        df.to_excel(writer, sheet_name=f'Table_{idx + 1}', index=False)
                st.success("All tables exported to 'extracted_tables.xlsx'!")

def show_table_editor(processor, gridlines):
    st.title("Step 5: Review and Edit Tables")
    
    # Initialize ExtractTable if not already done
    if not hasattr(st.session_state, 'extractor'):
        st.session_state.extractor = initialize_extractor()
    
    # Initialize tables dict if not exists
    if 'extracted_tables' not in st.session_state:
        st.session_state.extracted_tables = {}
    
    # Add view toggle in sidebar
    show_full_table = st.sidebar.checkbox("Show Full Table View", value=False)
    
    # Process all pages
    for page_num in range(len(st.session_state.pages)):
        st.subheader(f"Page {page_num + 1}")
        page_key = f"page_{page_num}"
        
        # Extract tables first (outside of view logic)
        if page_key in st.session_state.processed_pages and page_key not in st.session_state.extracted_tables:
            processor.current_image = st.session_state.processed_pages[page_key]
            image = processor.get_display_image(gridlines=gridlines.get(page_key, []))
            temp_path = f"temp_page_{page_num}.png"
            Image.fromarray(image).save(temp_path)
            
            try:
                table_data = st.session_state.extractor.process_file(
                    filepath=temp_path,
                    output_format="df"
                )
                if isinstance(table_data, list):
                    st.session_state.extracted_tables[page_key] = table_data
                else:
                    st.session_state.extracted_tables[page_key] = [table_data]
            except Exception as e:
                st.error(f"Error extracting table: {str(e)}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        # Display logic based on view toggle
        if show_full_table:
            # Show only tables in full width
            if page_key in st.session_state.processed_pages:
                # Small thumbnail of the image
                processor.current_image = st.session_state.processed_pages[page_key]
                image = processor.get_display_image(gridlines=gridlines.get(page_key, []))
                st.image(Image.fromarray(image), width=200)
                
                # Show tables full width
                if page_key in st.session_state.extracted_tables:
                    for idx, df in enumerate(st.session_state.extracted_tables[page_key]):
                        st.write(f"Table {idx + 1}")
                        
                        # Header editor
                        st.write("Edit Column Headers:")
                        header_df = pd.DataFrame([df.columns.tolist()], columns=df.columns)
                        edited_headers = st.data_editor(
                            header_df,
                            key=f"header_editor_{page_num}_{idx}",
                            hide_index=True
                        )
                        
                        # Update DataFrame with new headers
                        new_headers = edited_headers.iloc[0].tolist()
                        df.columns = new_headers
                        
                        # Show the table with updated headers
                        edited_df = st.data_editor(
                            df,
                            key=f"table_{page_num}_{idx}",
                            num_rows="dynamic"
                        )
                        st.session_state.extracted_tables[page_key][idx] = edited_df
        else:
            # Original split view
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if page_key in st.session_state.processed_pages:
                    processor.current_image = st.session_state.processed_pages[page_key]
                    image = processor.get_display_image(gridlines=gridlines.get(page_key, []))
                    st.image(Image.fromarray(image), use_container_width=True)
            
            with col2:
                if page_key in st.session_state.extracted_tables:
                    for idx, df in enumerate(st.session_state.extracted_tables[page_key]):
                        st.write(f"Table {idx + 1}")
                        
                        # Header editor
                        st.write("Edit Column Headers:")
                        header_df = pd.DataFrame([df.columns.tolist()], columns=df.columns)
                        edited_headers = st.data_editor(
                            header_df,
                            key=f"header_editor_{page_num}_{idx}",
                            hide_index=True
                        )
                        
                        # Update DataFrame with new headers
                        new_headers = edited_headers.iloc[0].tolist()
                        df.columns = new_headers
                        
                        # Show the table with updated headers
                        edited_df = st.data_editor(
                            df,
                            key=f"table_{page_num}_{idx}",
                            num_rows="dynamic"
                        )
                        st.session_state.extracted_tables[page_key][idx] = edited_df
    
    # Export button at the bottom
    st.markdown("---")
    if st.button("Export All Tables to Excel"):
        with pd.ExcelWriter('extracted_tables.xlsx') as writer:
            table_count = 0
            for page_num in range(len(st.session_state.pages)):
                page_key = f"page_{page_num}"
                if page_key in st.session_state.extracted_tables:
                    for idx, df in enumerate(st.session_state.extracted_tables[page_key]):
                        sheet_name = f'Page{page_num+1}_Table{idx+1}'
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        table_count += 1
        st.success(f"Successfully exported {table_count} tables to 'extracted_tables.xlsx'!")

def initialize_extractor():
    """Initialize ExtractTable with API key from user input"""
    if 'api_key' not in st.session_state:
        with st.form("api_key_form"):
            api_key = st.text_input(
                "Enter your ExtractTable API key to continue",
                type="password",
                help="Get your API key from https://extracttable.com"
            )
            if st.form_submit_button("Submit"):
                if not api_key:
                    st.error("Please enter an API key")
                    st.stop()
                try:
                    # Try to initialize and validate the API key before saving it
                    extractor = ExtractTable(api_key=api_key)
                    usage = extractor.check_usage()
                    st.session_state.api_key = api_key
                    st.sidebar.success("✅ API connected successfully")
                    st.sidebar.info(f"API Credits remaining: {usage['remaining_credits']}")
                    return extractor
                except Exception as e:
                    st.error(f"Invalid API key: {str(e)}")
                    st.stop()
        
        if 'api_key' not in st.session_state:
            st.stop()
    
    try:
        extractor = ExtractTable(api_key=st.session_state.api_key)
        usage = extractor.check_usage()
        st.sidebar.success("✅ API connected successfully")
        st.sidebar.info(f"API Credits remaining: {usage['remaining_credits']}")
        return extractor
    except Exception as e:
        # If API key becomes invalid, remove it from session state
        if 'api_key' in st.session_state:
            del st.session_state.api_key
        st.error(f"Invalid API key: {str(e)}")
        st.stop()

def main():
    st.set_page_config(layout="wide")
    
    # Initialize state
    if 'step' not in st.session_state:
        st.session_state.step = 1  # Start at step 1
        st.session_state.processor = PDFProcessor()
        st.session_state.current_page = 0
        st.session_state.pages = []
        st.session_state.processed_pages = {}
        st.session_state.show_cropper = False
        st.session_state.zoom_level = 1.0

    # Step 1: Load PDF
    if st.session_state.step == 1:
        st.title("Step 1: Load PDF")
        uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])
        
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                pdf_path = tmp_file.name
                
            if not st.session_state.pages:
                st.session_state.pages = st.session_state.processor.convert_pdf(pdf_path)
                st.session_state.processor.current_image = st.session_state.pages[0]
            
            if st.button("Proceed to Cropping"):
                st.session_state.step = 2
                st.rerun()

    # Step 2: Crop Pages
    elif st.session_state.step == 2:
        st.title("Step 2: Crop Pages")
        
        # Navigation
        nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 2])
        with nav_col1:
            if st.button("⬅️ Previous") and st.session_state.current_page > 0:
                st.session_state.current_page -= 1
                st.session_state.processor.current_image = st.session_state.pages[st.session_state.current_page]
                st.session_state.show_cropper = False
                st.rerun()
        with nav_col2:
            if st.button("➡️ Next") and st.session_state.current_page < len(st.session_state.pages) - 1:
                st.session_state.current_page += 1
                st.session_state.processor.current_image = st.session_state.pages[st.session_state.current_page]
                st.session_state.show_cropper = False
                st.rerun()
        with nav_col3:
            st.write(f"Page {st.session_state.current_page + 1} of {len(st.session_state.pages)}")

        # Cropping interface
        main_col1, main_col2 = st.columns([4, 1])
        with main_col1:
            # Always set the current image to the correct page
            st.session_state.processor.current_image = st.session_state.pages[st.session_state.current_page]
            
            if not st.session_state.show_cropper:
                if st.button("Start Crop"):
                    st.session_state.show_cropper = True
                    st.rerun()
            
            if st.session_state.show_cropper:
                # Convert numpy array to PIL Image for the cropper
                pil_image = Image.fromarray(st.session_state.processor.current_image)
                cropped_img = st_cropper(
                    pil_image,
                    realtime_update=True,
                    box_color='#FF0000',
                    aspect_ratio=None,
                    return_type='box'
                )
                if isinstance(cropped_img, dict):
                    st.session_state.crop_box = cropped_img

        with main_col2:
            if st.session_state.show_cropper:
                if st.button("Apply Crop"):
                    if hasattr(st.session_state, 'crop_box'):
                        box = st.session_state.crop_box
                        adjusted_box = (
                            int(box['left']),
                            int(box['top']),
                            int(box['width']),
                            int(box['height'])
                        )
                        # Make sure we're using the correct page
                        st.session_state.processor.current_image = st.session_state.pages[st.session_state.current_page]
                        st.session_state.processor.crop_to_box(adjusted_box)
                        current_page_key = f"page_{st.session_state.current_page}"
                        st.session_state.processed_pages[current_page_key] = np.array(st.session_state.processor.current_image)
                        st.session_state.show_cropper = False
                        delattr(st.session_state, 'crop_box')
                        st.rerun()

        # Proceed button
        if len(st.session_state.processed_pages) == len(st.session_state.pages):
            if st.button("All Pages Cropped - Proceed to Rotation/Deskew"):
                st.session_state.step = 3
                st.rerun()

    # Step 3: Rotate and Deskew
    elif st.session_state.step == 3:
        st.title("Step 3: Rotate and Deskew")
        
        # Store original cropped state if not already stored
        if 'original_cropped_pages' not in st.session_state:
            st.session_state.original_cropped_pages = {
                key: np.array(img) for key, img in st.session_state.processed_pages.items()
            }
        
        # Navigation
        nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 2])
        with nav_col1:
            if st.button("⬅️ Previous") and st.session_state.current_page > 0:
                st.session_state.current_page -= 1
                current_page_key = f"page_{st.session_state.current_page}"
                st.session_state.processor.current_image = st.session_state.processed_pages[current_page_key]
                st.rerun()
        with nav_col2:
            if st.button("➡️ Next") and st.session_state.current_page < len(st.session_state.pages) - 1:
                st.session_state.current_page += 1
                current_page_key = f"page_{st.session_state.current_page}"
                st.session_state.processor.current_image = st.session_state.processed_pages[current_page_key]
                st.rerun()
        with nav_col3:
            st.write(f"Page {st.session_state.current_page + 1} of {len(st.session_state.pages)}")

        main_col1, main_col2 = st.columns([4, 1])
        with main_col1:
            current_page_key = f"page_{st.session_state.current_page}"
            # Always use the processed (cropped) image
            st.session_state.processor.current_image = st.session_state.processed_pages[current_page_key]
            st.image(st.session_state.processor.current_image)

        with main_col2:
            # Rotation controls
            st.subheader("Rotation")
            rot_col1, rot_col2 = st.columns(2)
            with rot_col1:
                if st.button("Rotate -90°"):
                    st.session_state.processor.rotate_image(-90)
                    st.session_state.processed_pages[current_page_key] = np.array(st.session_state.processor.current_image)
                    st.rerun()
            with rot_col2:
                if st.button("Rotate +90°"):
                    st.session_state.processor.rotate_image(90)
                    st.session_state.processed_pages[current_page_key] = np.array(st.session_state.processor.current_image)
                    st.rerun()

            fine_rot_col1, fine_rot_col2 = st.columns(2)
            with fine_rot_col1:
                if st.button("Rotate -0.25°"):
                    st.session_state.processor.rotate_image(-0.25)
                    st.session_state.processed_pages[current_page_key] = np.array(st.session_state.processor.current_image)
                    st.rerun()
            with fine_rot_col2:
                if st.button("Rotate +0.25°"):
                    st.session_state.processor.rotate_image(0.25)
                    st.session_state.processed_pages[current_page_key] = np.array(st.session_state.processor.current_image)
                    st.rerun()

            # Deskew controls with reset
            st.subheader("Deskew")
            deskew_col1, deskew_col2 = st.columns(2)
            with deskew_col1:
                if st.button("Auto-Deskew"):
                    st.session_state.processor.auto_deskew()
                    st.session_state.processed_pages[current_page_key] = np.array(st.session_state.processor.current_image)
                    st.rerun()
            with deskew_col2:
                if st.button("Reset"):
                    # Reset to original cropped state
                    st.session_state.processed_pages[current_page_key] = np.array(st.session_state.original_cropped_pages[current_page_key])
                    st.session_state.processor.current_image = st.session_state.processed_pages[current_page_key]
                    st.rerun()

        # Save and proceed button
        if st.button("Save Processed Images and Proceed to Gridlines"):
            # Save all processed images
            for page_num in range(len(st.session_state.pages)):
                page_key = f"page_{page_num}"
                if page_key in st.session_state.processed_pages:
                    Image.fromarray(st.session_state.processed_pages[page_key]).save(f'processed_page_{page_num + 1}.png')
            
            st.session_state.step = 4
            st.rerun()

    # Step 4: Add Gridlines
    elif st.session_state.step == 4:
        st.title("Step 4: Add Gridlines")
        
        if 'gridlines' not in st.session_state:
            st.session_state.gridlines = {}
        
        # Use full width of the page
        st.markdown("""
            <style>
                .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 1rem;
                    padding-right: 1rem;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Load and display all processed images
        for page_num in range(len(st.session_state.processed_pages)):
            st.subheader(f"Page {page_num + 1}")
            
            page_key = f"page_{page_num}"
            if page_key not in st.session_state.gridlines:
                st.session_state.gridlines[page_key] = []
            
            with st.container():
                col1, col2 = st.columns([6, 1])
                
                with col1:
                    # Ensure we're using the correct processed page
                    current_image = np.array(st.session_state.processed_pages[page_key])
                    st.session_state.processor.current_image = current_image
                    
                    image_with_lines = st.session_state.processor.get_display_image(
                        gridlines=st.session_state.gridlines[page_key]
                    )
                    
                    # Get the actual image dimensions
                    actual_width = image_with_lines.shape[1]
                    
                    # Display image and get click coordinates
                    value = streamlit_image_coordinates(
                        Image.fromarray(image_with_lines),
                        key=f"image_{page_num}",
                        use_column_width=True
                    )
                    
                    if value is not None:
                        # Get the displayed image width from the click data
                        displayed_width = value["width"]
                        
                        # Scale the click coordinate to match the actual image dimensions
                        scale_factor = actual_width / displayed_width
                        actual_x = int(value["x"] * scale_factor)
                        
                        if actual_x not in st.session_state.gridlines[page_key]:
                            st.session_state.gridlines[page_key].append(actual_x)
                            st.session_state.gridlines[page_key].sort()
                            st.rerun()
                
                with col2:
                    st.write("Edit Gridlines:")
                    if st.session_state.gridlines[page_key]:
                        for i, x in enumerate(sorted(st.session_state.gridlines[page_key])):
                            col_a, col_b = st.columns([4, 1])
                            with col_a:
                                st.write(f"Line at x={int(x)}")
                            with col_b:
                                if st.button("❌", key=f"del_{page_num}_{i}", help="Delete gridline"):
                                    st.session_state.gridlines[page_key].remove(x)
                                    st.rerun()
                    else:
                        st.write("No gridlines yet")
                    
                    st.write("---")
                    st.write("Click on image to add gridlines")
            
            # Add more space between pages
            st.markdown("<br>", unsafe_allow_html=True)
            st.divider()
            st.markdown("<br>", unsafe_allow_html=True)
        
        # Add proceed button at the bottom
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save All Pages with Gridlines"):
                for page_num in range(len(st.session_state.pages)):
                    page_key = f"page_{page_num}"
                    if page_key in st.session_state.processed_pages:
                        st.session_state.processor.current_image = st.session_state.processed_pages[page_key]
                        st.session_state.processor.save_image(
                            gridlines=st.session_state.gridlines.get(page_key, []),
                            filename=f'final_page_{page_num + 1}.png'
                        )
                st.success("All pages saved with gridlines!")
        
        with col2:
            if st.button("Proceed to Table Extraction"):
                st.session_state.step = 5
                st.rerun()

    # Step 5: Extract Tables
    elif st.session_state.step == 5:
        show_table_editor(st.session_state.processor, st.session_state.gridlines)

if __name__ == "__main__":
    main() 