import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import google.generativeai as genai
from google.cloud import storage
from streamlit_feedback import streamlit_feedback
import io
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv
import ast
from deep_translator import GoogleTranslator
from langdetect import detect

# Load environment variables
load_dotenv()
json_key_path = 'service-account-key.json'  # Update with your service account key path
credentials = service_account.Credentials.from_service_account_file(json_key_path)

# Create a BigQuery client using the service account credentials
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_KEY"))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account-key.json"

# Create the model
generation_config = {
    "temperature": 0,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 50,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

# Set page config
st.set_page_config(
    page_title="Model Matrimony",
    page_icon="❤️",
    layout="wide"
)

# Initialize session state
if 'feedback_key' not in st.session_state:
    st.session_state.feedback_key = 'feedback_widget'

if 'session_id' not in st.session_state:
    st.session_state.session_id = str(int(time.time()))
    st.session_state.session_start_time = datetime.now()
    st.session_state.welcome_shown = False
elif (datetime.now() - st.session_state.session_start_time) > timedelta(minutes=10):
    # Create new session after 10 minutes
    st.session_state.session_id = str(int(time.time()))
    st.session_state.session_start_time = datetime.now()
    st.session_state.welcome_shown = False

if 'copy_button_clicked' not in st.session_state:
    st.session_state.copy_button_clicked = False

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stProgress > div > div > div > div {
        background-color: #DA70D6;
    }
    .element-container:has(div.stSuccessMessage) div[data-testid="stMarkdownContainer"] p {
        color: #953553 !important;
    }
    .element-container:has(div.stSuccessMessage) {
        background-color: rgba(149, 53, 83, 0.1) !important;
    }
    .element-container:has(div.stSuccessMessage) svg {
        fill: #953553 !important;
    }
    .model-table {
        margin-top: 1rem;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

@st.dialog("Welcome to Model Matrimony 💍")
def welcome_message():
    st.balloons()
    st.write(f"""
🔍 **Find Your Perfect Open Source LLM Match in 2 Simple Steps!**

✨ **Features:**
1. **Global Language Support**: Compatible with 100+ languages for worldwide accessibility
2. **Comprehensive Benchmarking**: Leverages 6 different LLM benchmarks for accurate matching
3. **Real-time Updates**: Benchmark data refreshes every 2 hours for up-to-date recommendations
4. **Quality Assured**: Only suggests official, non-flagged models you can trust

Just describe your task and set your size preference - we'll handle the rest! 

Ready to meet your perfect model match? Let's begin! 🚀

###### Collects feedback to improve — no personal data 🔒
###### Powered by Google Cloud 🌥️
""")

@st.dialog("Share Your Model Matrimony Experience 🕵️‍♂️")
def share_app():
    if 'copy_button_clicked' not in st.session_state:
        st.session_state.copy_button_clicked = False
        
    def copy_to_clipboard():
        st.session_state.copy_button_clicked = True
        st.write('<script>navigator.clipboard.writeText("google.com");</script>', unsafe_allow_html=True)
        
    app_url = 'https://model-matrimony.app'
    text = f'''Looking for the perfect open source LLM? 🤔
Check out Model Matrimony - it matches you with the ideal LLM for your needs!

Try this free tool and find your perfect model match now 🚀
Link to the app: {app_url}
    '''
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        url = 'https://www.linkedin.com/sharing/share-offsite/?url={app_url}'
        st.link_button('💼 LinkedIn', url)
    with col2:
        url = f'https://x.com/intent/post?original_referer=http%3A%2F%2Flocalhost%3A8502%2F&ref_src=twsrc%5Etfw%7Ctwcamp%5Ebuttonembed%7Ctwterm%5Eshare%7Ctwgr%5E&text={text}+%F0%9F%8E%88&url=%7B{app_url}%7D'
        st.link_button('𝕏 Twitter', url)
    with col3:
        placeholder = st.empty()
        if st.session_state.copy_button_clicked:
            placeholder.button("Copied!", disabled=True)
            st.toast('Link copied to clipboard! 📋')
        else:
            placeholder.button('📄 Copy Link', on_click=copy_to_clipboard)
    st.text_area("Sample Text", text, height=350)

def translate_to_english(text):
    """Detect language and translate to English if not already in English"""
    try:
        detected_language = detect(text)
        if detected_language != 'en':
            translated_text = GoogleTranslator(source=detected_language, target='en').translate(text)
            return translated_text, detected_language
        return text, 'en'
    except Exception as e:
        st.warning(f"Translation error: {str(e)}. Proceeding with original text.")
        return text, 'en'

@st.cache_data
def load_data():
    """Load data from Google Cloud Storage"""
    try:
        # Initialize GCS client
        storage_client = storage.Client()
        
        # Get bucket and blob
        bucket = storage_client.get_bucket(os.getenv("BUCKET_NAME"))
        blob = bucket.blob("llm_leaderboard.csv")
        
        # Download the content to a string buffer
        content = blob.download_as_string()
        
        # Convert to pandas DataFrame
        df = pd.read_csv(io.BytesIO(content))
        return df
    except Exception as e:
        st.error(f"Error loading data from GCS: {str(e)}")
        return None

def read_file(filename):
    with open(filename, 'r') as file:
        return file.read()

def create_model_dataframe(model_data, benchmarks):
    """Create a DataFrame for model display"""
    # Extract model name without path
    model_name = model_data['fullname'].split('/')[-1] if '/' in model_data['fullname'] else model_data['fullname']
    
    # Create base data
    base_data = {
        'Metric': ['Model Name', 'Size (B)', 'Average Score', 'Architecture', 'License'],
        'Value': [
            model_name,
            f"{model_data['#Params (B)']:.2f}",
            f"{model_data['Average ⬆️']:.2f}",
            model_data['Architecture'],
            model_data['Hub License']
        ]
    }
    
    # Add benchmark scores
    for benchmark in benchmarks:
        if benchmark in model_data and benchmark != "Average ⬆️":
            base_data['Metric'].append(f"{benchmark} Score")
            base_data['Value'].append(f"{model_data[benchmark]:.2f}")
    
    return pd.DataFrame(base_data)

def process_task(task, model_size):
    # Initialize progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Step 1: Language Detection (15%)
    status_text.text("Detecting language...")
    progress_bar.progress(15)
    time.sleep(0.5)
    
    # Step 2: Load data (30%)
    status_text.text("Loading benchmark data...")
    data = load_data()
    data = data[(data['Official Providers'])&(data['Available on the hub'])&(~data['Flagged'])]
    data = data.sort_values("Average ⬆️", ascending=False)
    progress_bar.progress(30)
    time.sleep(0.5)
    
    # Step 3: Initialize Gemini (45%)
    status_text.text("Initializing Gemini...")
    progress_bar.progress(45)
    time.sleep(0.5)
    
    # Step 4: Get benchmark selection prompt (60%)
    status_text.text("Processing your task requirements...")
    benchmark_select = read_file("prompts/benchmark_select.txt")
    benchmark_list = read_file("prompts/benchmark_list.txt")
    benchmark_select = benchmark_select.format(benchmarks=benchmark_list, input=task)
    
    # Get benchmark recommendations
    response = model.generate_content(benchmark_select).text.replace("\n", "")
    print(response)
    
    # Parse the response and extract benchmarks
    try:
        recommended_benchmarks = ast.literal_eval(response)
        recommended_benchmarks = [b.strip() for b in recommended_benchmarks if b.strip()]
        if not recommended_benchmarks:
            recommended_benchmarks = ["Average ⬆️"]
    except Exception as e:
        recommended_benchmarks = ["Average ⬆️"]

    progress_bar.progress(60)
    time.sleep(0.5)
    
    # Step 5: Filter models (80%)
    status_text.text("Finding your perfect model matches...")
    available_models = data.sort_values(by=recommended_benchmarks, ascending=False).reset_index(drop=True)
    overall_best_model = available_models.iloc[0]
    
    # Get best model within size constraint
    size_filtered_models = available_models[available_models['#Params (B)'] <= model_size]
    best_sized_model = size_filtered_models.iloc[0]
    
    progress_bar.progress(80)
    time.sleep(0.5)
    
    # Step 6: Prepare results (100%)
    status_text.text("Preparing your matches...")
    progress_bar.progress(100)
    time.sleep(0.5)
    
    return overall_best_model, best_sized_model, recommended_benchmarks

def upload_to_bq(df, table_name):
    """Upload data to BigQuery"""
    destination_table = client.dataset("model_matrimony").table(f'{table_name}')
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    load_job = client.load_table_from_dataframe(df, destination_table, job_config=job_config)
    load_job.result()

def _submit_feedback(user_response, emoji=None):
    session_id = st.session_state.get("session_id")
    feedback_value = 1 if user_response['score'] == '👍' else 0
    user_feedback = user_response['text']
    new_feedback = pd.DataFrame([[session_id, feedback_value, user_feedback]], columns=["session_id", "vote", "comment"])
    upload_to_bq(new_feedback, 'feedback_data')
    st.success("Your feedback has been submitted!")

# Create header with title and share button
header_col1, header_col2 = st.columns([10, 1])
with header_col1:
    st.title("Model Matrimony 💍")
with header_col2:
    if st.button("Share App 📢", type="secondary"):
        share_app()

# Show welcome message only once per session
if not st.session_state.welcome_shown:
    welcome_message()
    st.session_state.welcome_shown = True

# Main app interface
with st.container():
    # User input section
    st.markdown("#### Step 1: Describe Your Task")
    user_task = st.text_area(
        "",
        height=100,
        placeholder="E.g., Chatbot that answers medical questions...",
        label_visibility='hidden'
    )
    
    # Model size slider
    st.markdown("#### Step 2: Small Model Preference")
    model_size = st.slider(
        "Maximum model size (in billion parameters)",
        min_value=1,
        max_value=50,
        value=15,
        help="Larger models are more capable but require more computational resources"
    )
    
    # Process button
    if st.button("Find My Perfect Match! 💘", type="primary"):
        if user_task:
            try:
                # Translate user task if not in English
                translated_task, detected_lang = translate_to_english(user_task)
                
                # Show translation info if task was translated
                if detected_lang != 'en':
                    st.info(f"Original language detected: {detected_lang}. Task has been translated to English for processing.")
                
                overall_best_model, best_sized_model, recommended_benchmarks = process_task(translated_task, model_size)
                
                # Display results in table format
                st.success("Found your perfect matches! 🎉")
                with st.expander("Results"):
                    # Overall Best Model
                    st.markdown("### 🏆 Overall Best Model")
                    overall_df = create_model_dataframe(overall_best_model, recommended_benchmarks)
                    st.table(overall_df)
                    
                    st.markdown("---")
                    
                    # Best Model Within Size Constraint
                    st.markdown(f"### 🎯 Best Model Under {model_size}B Parameters")
                    sized_df = create_model_dataframe(best_sized_model, recommended_benchmarks)
                    st.table(sized_df)
                    
                    # Display Relevant Benchmarks
                    st.markdown("### 📊 Relevant Benchmarks")
                    benchmark_df = pd.DataFrame({
                        'Benchmark': [bench.strip() for bench in recommended_benchmarks if bench.strip()]
                    })
                    st.table(benchmark_df)
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.warning("Please describe your task first! 🙏")

streamlit_feedback(
    feedback_type="thumbs",
    optional_text_label="Please provide extra information",
    on_submit=_submit_feedback,
    key=st.session_state.feedback_key,
)

# Footer
st.markdown(
    "<div style='text-align: center;'>"
    "Built with ❤️ using Streamlit | Don't marry blindly!"
    "</div>",
    unsafe_allow_html=True
)
