import streamlit as st
import cv2
from PIL import Image
import numpy as np
import io
from supabase import create_client, Client
from streamlit_star_rating import st_star_rating
from streamlit_image_select import image_select
import toml


###
# Image Processing Functions
# ---------------------------
###
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
# Function to overlay text
def overlay_text(img, text):
    h, w = img.shape
    font = cv2.FONT_HERSHEY_SIMPLEX 
    org = (w-108, h-10) 
    fontScale = 0.35
    color = (0, 0, 0) 
    thickness = 1   
    # Using cv2.putText() method 
    image = cv2.putText(img, text, org, font,  
                    fontScale, color, thickness, cv2.LINE_AA) 
    return image
def overlay_image(src_image, overlay_image):
    overlay_image = cv2.resize(overlay_image, (100,100))[None, ...]
    #src_image = cv2.cvtColor(src_image,cv2.COLOR_GRAY2RGB)
    #src_image[10:110,10:110] = overlay_image[0:100,0:100]
    qrCodeImage = np.array(Image.open('images/qr_code.png'))
    qrCodeImage = cv2.resize(qrCodeImage, (75,75))[None, ...]
    src_image = cv2.cvtColor(src_image,cv2.COLOR_GRAY2RGBA)
    r,c,ch = src_image.shape
    src_image[r-95:r-20,c-99:c-24] = qrCodeImage[0:75,0:75]
    return src_image
    #return cv2.addWeighted(src_image,0.7,overlay_image,1-alpha,0.)


###
# Database Functions
# ------------------
###

supabase=create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Insert new row for every sketch generated
def log_new_sketch():
    result, count = supabase.table('artzy_metric').insert({}).execute()
    st.session_state.sketchId = result[1][0]["id"]

# Get Number of sketches, uses "get_num_of_sketches" function created in supabase
def get_number_of_sketches():
    result, count = supabase.rpc('get_num_of_sketches',{}).execute()
    return result[1]

# Update Rating in Supabase
def update_rating(value):
    # logic to update rating in a supabase
    if(value > 0):
        data, count = supabase.table('artzy_metric').update({'rating': value}).eq('id', st.session_state.sketchId).execute()

# Update user provided feedback in supabase
def update_comments(comments):
    data, count = supabase.table('artzy_metric').update({'comments': comments}).eq('id', st.session_state.sketchId).execute()
    st.write("Thanks for your feedback !")


###
# Session Management Functions
###
def reset_current_image_selection(selection_mode):
    # Set current selection mode
    st.session_state.current_selection=selection_mode
    # Clear Current sketch
    if "image_for_sketch" in st.session_state:
        del st.session_state.image_for_sketch
    reset_current_sketch()
    # Rerun
    st.rerun()

# Listen to file change to set session variable appropriately
def file_uploader_file_change():
    st.session_state.file_changed = True

# Generate a new sketch.
def generate_sketch():
    # Generate only once per sketch.. if sketchid is already present in the session, don't regenerate it
    # when reset current sketch happens, setchId gets deleted from session, see reset_current_sketch
    if("sketchId" not in st.session_state):
        # Generarte Sketch from the current image_for_sketch
        sketch = create_sketch(st.session_state.image_for_sketch)
        sketch = overlay_text(sketch, 'Generated by Artzy')
        sketch = overlay_image(sketch, st.session_state.image_for_sketch) 
        st.session_state.current_sketch = sketch #create_sketch(st.session_state.image_for_sketch)
        log_new_sketch()
        st.session_state.file_changed = False

# Reset current sketch - see the places it is being called..
def reset_current_sketch():
    if "current_sketch" in st.session_state:
        del st.session_state["current_sketch"]
        del st.session_state.sketchId


###
#  UI Functions
#  ------------
###
        
# Display Header
def show_header():
    header_col, metric_column = st.columns([7,1])
    with header_col:
        # Artzy Heading with Rainbow divider underneath!
        st.header("Artzy", divider="violet")
    with metric_column: 
        st.metric(label="Generated",value=get_number_of_sketches(), delta="sketches")

    # Write copyright notes
    st.write("Note: We do not store any art that is uploaded and will be used only to generate a sketch for you")


# Show Image Selection Options in UI (Library or File)
def show_image_selection_UI():
    image_select_container = st.container(border=True)
    with image_select_container:
        if(st.session_state.current_selection == "FILE"):
            if ("selected_file" in st.session_state):
                st.session_state.prior_selected_file = st.session_state.selected_file
        
            file_col, presets_col = st.columns(2)
            with file_col:
                # Add File upload widget
                st.session_state.uploaded_file = st.file_uploader(label = "Upload a picture or art to create a sketch", 
                                                                  type=['png','jpeg','jpg'],
                                                                  on_change=file_uploader_file_change)
                if(st.session_state.uploaded_file is not None):
                    st.session_state.selected_file = st.session_state.uploaded_file.name
            with presets_col:
                st.write("Or pick an art from our existing library")
                if st.button("Browse our library", type="primary"):
                    reset_current_image_selection("LIBRARY")
                    
        else:
            if ("selected_image" in st.session_state):
                st.session_state.prior_selected_image = st.session_state.selected_image
            library_col, file_upload_col = st.columns([6,2])
            with library_col:
                st.session_state.selected_image = image_select(label="Pick an art from our library", images=st.session_state.preset_images["images"], 
                            captions= st.session_state.preset_images["captions"],
                            use_container_width=False,
                            index=0)
            with file_upload_col:
                st.write("Or Upload your own art")
                if st.button("Upload your own art", type="primary"):
                    reset_current_image_selection("FILE")

def set_current_image_for_sketch_based_on_selection():
    # Set image for sketch based on current mode of selection.
    if (st.session_state.current_selection=="LIBRARY"):
        # if image selection is changed, clear the current sketch and enable generate sketch button.
        if("prior_selected_image" in st.session_state and st.session_state.selected_image != st.session_state.prior_selected_image):
           reset_current_sketch()
        st.session_state.image_for_sketch =  np.array(Image.open(st.session_state.selected_image)) 
    else:

        if ("prior_selected_file" in st.session_state and st.session_state.selected_file != st.session_state.prior_selected_file):
            reset_current_sketch()
        if ("uploaded_file" in st.session_state and  st.session_state.uploaded_file is not None):
            bytes_data = st.session_state.uploaded_file.getvalue()
            st.session_state.image_for_sketch = np.array(Image.open(io.BytesIO(bytes_data))) 
        else:
            if ("image_for_sketch" in st.session_state):
                del st.session_state.image_for_sketch 

def show_current_selected_image(container):
    with container:
        st.image(st.session_state.image_for_sketch)

def show_generate_sketch_button(container):
    with container:
        st.button('Generate Sketch', on_click=generate_sketch)

def show_current_sketch_feedback(container):
    if("current_sketch" in st.session_state):
        with container:
            st.image(st.session_state.current_sketch)
            st.write('How would you rate the sketch?')
            star =  st_star_rating(label = "", maxValue=5, size=20, defaultValue=0, on_click = update_rating)
            with st.form("my_form"):
                txt = st.text_area(label="Feedback")
                submitted = st.form_submit_button("Submit")
                if submitted:
                    update_comments(txt)
            

def initialize_defaults():
    # Load preset images 
    st.session_state.preset_images = toml.load("images/index.toml")
    # Set default selection UI mode to FILE
    if("current_selection" not in st.session_state):
        st.session_state.current_selection = "LIBRARY"

# Main function.
def main():
    initialize_defaults()
    show_header()
    show_image_selection_UI()
    set_current_image_for_sketch_based_on_selection()    

    # If current image is set to generate sketch, show sketch generation ui
    if("image_for_sketch" in st.session_state):
        col1, col2, col3 = st.columns(3)
        show_current_selected_image(col1)
        show_generate_sketch_button(col2)
        show_current_sketch_feedback(col3)

# Start here..
main()
