import streamlit as st
import cv2
from PIL import Image
import numpy as np
import io
from supabase import create_client, Client
from streamlit_star_rating import st_star_rating

supabase=create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


# Function to create a sketch from an image, 
def create_sketch(img):
    kernel = np.array([
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        ], np.uint8)
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_dilated = cv2.dilate(img_gray, kernel, iterations=1)
    img_diff = cv2.absdiff(img_dilated, img_gray)
    contour = 255 - img_diff
    return contour

def log_new_sketch():
    result, count = supabase.table('artzy_metric').insert({}).execute()
    st.session_state.sketchId = result[1][0]["id"]

def get_number_of_sketches():
    result, count = supabase.rpc('get_num_of_sketches',{}).execute()
    return result[1]

def update_rating(value):
    # logic to update rating in a supabase
    if(value > 0):
        data, count = supabase.table('artzy_metric').update({'rating': value}).eq('id', st.session_state.sketchId).execute()

def update_comments(comments):
    data, count = supabase.table('artzy_metric').update({'comments': comments}).eq('id', st.session_state.sketchId).execute()
    st.write("Thanks for your feedback !")

def set_current_sketch(bytes_data):
    # Generarte Sketch from an input image.
    input_image = np.array(Image.open(io.BytesIO(bytes_data))) 
    output_sketch = create_sketch(input_image)
    st.session_state.current_sketch = output_sketch
    log_new_sketch()

def clear_current_sketch():
    if "current_sketch" in st.session_state:
        del st.session_state["current_sketch"]
        del st.session_state.sketchId


# Main function.
def main():

    header_col, metric_column = st.columns([7,1])
    with header_col:
        # Artzy Heading with Rainbow divider underneath!
        st.header("Welcome to Artzy")
        st.subheader("-where Art meet Innovation & Collaboration")
        st.header(divider = "rainbow")
    with metric_column: 
        st.metric(label="Generated",value=get_number_of_sketches(), delta="sketches")

    # Add File upload widget
    uploaded_file = st.file_uploader(label = "Upload a picture or art to create a sketch (Note: We do not store any art that is uploaded and will be used only to generate a sketch for you)", type=['png','jpeg','jpg','gif'])
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.image(bytes_data)
        with col2:
            st.button('Generate Sketch', on_click=set_current_sketch, args=(bytes_data,))
    else:
        clear_current_sketch()

    if "current_sketch" in  st.session_state:
        with col3:
            st.image(st.session_state.current_sketch)
            st.write('How would you rate the sketch?')
            star =  st_star_rating(label = "", maxValue=5, size=20, defaultValue=0, on_click = update_rating)
            with st.form("my_form"):
                txt = st.text_area(label="Feedback")
                submitted = st.form_submit_button("Submit")
                if submitted:
                    update_comments(txt)

main()
