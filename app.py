import streamlit as st
import fitz
import docx2txt
import requests
import json
import io
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

API_KEY = "m2itXoOFEKU5oFVETefDCVLyIWxH5t6B"  
MODEL_NAME = "mistral-small-latest"
API_URL = "https://api.mistral.ai/v1/chat/completions"

ui_lock = threading.Lock()

@st.cache_data
def extract_text_optimized(file_content, file_type):
    """Extract text from PDF or DOCX files with error handling"""
    try:
        text = ""
        if file_type == "application/pdf":
            doc = fitz.open(stream=io.BytesIO(file_content), filetype="pdf")
            text_parts = []
            for page_num in range(min(3, doc.page_count)):
                page_text = doc[page_num].get_text("text")
                if page_text.strip():  
                    text_parts.append(page_text)
            text = "\n".join(text_parts)
            doc.close()
        elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
            text = docx2txt.process(io.BytesIO(file_content))
        else:
            return None, f"Unsupported file type: {file_type}"
        
        if not text or not text.strip():
            return None, "No text content found in file"
        
        text = re.sub(r"[ \t]+", " ", text) 
        text = re.sub(r"\n{3,}", "\n\n", text)  
        cleaned_text = text.strip()[:3000]
        
        if len(cleaned_text) < 50:
            return None, "Insufficient text content (less than 50 characters)"
        
        return cleaned_text, None
        
    except Exception as e:
        return None, f"Text extraction error: {str(e)}"

def parse_jd_fast(jd_text):
    """Parse job description using Mistral AI API"""
    prompt = f"""Extract job description data as JSON using this exact format. Pay special attention to salary extraction - look for patterns like "12-17 LPA", "CTC in INR", salary ranges, and convert appropriately:

{{
    "title": "",
    "Qualifications": {{
        "Preferred": [],
        "Required": []
    }},
    "noOfPositions": "",
    "JobLocation": {{
        "Location": "", 
        "City": "", 
        "State": "", 
        "Country": "", 
        "IsoCountryCode": "", 
        "ZipCode": ""
    }},
    "JobType": "",
    "SalaryOffered": {{
        "MinAmount": "", 
        "MaxAmount": "", 
        "Currency": ""
    }},
    "ContractDuration": "",
    "officeTimings": "",
    "education": [],
    "ContactPhone": "",
    "ContactPersonName": "",
    "InterviewType": "",
    "InterviewDate": "",
    "InterviewTime": "",
    "InterviewLocation": ""
}}

EXTRACTION GUIDELINES:
-LPA = Lakhs Per Annum, CTC = Cost to Company
- For salary: Look for patterns like "12-17 LPA", "CTC in INR", "X-Y Lakhs", salary ranges. Extract MinAmount and MaxAmount as numbers only (e.g., "12 Lakhs", "17 Lakhs"), Currency as "INR", "USD", etc.
- For qualifications: Split "Must have" into Required array, "Good to have" into Preferred array
- For location: Extract city, state, country from work location mentions
- For positions: Look for "No. of Positions", "#10", "10 positions", etc.
- For job type: Full time, Part time, Contract, etc.
- For timings: Look for working hours, office timings
- For education: Extract degree requirements
- For interview details: Extract interview rounds, panel availability, process details
- Use empty string "" for missing text fields, empty array [] for missing array fields

Job Description:
{jd_text}
"""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system", 
                "content": "You are a precise data extraction assistant. Extract job description fields in valid JSON format. Follow the schema exactly. Return only JSON without any additional text or formatting."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.08,
        "max_tokens": 4000,
        "top_p": 0.9
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            
            if "choices" not in response_data or not response_data["choices"]:
                return {"error": "Invalid API response structure"}
            
            content = response_data["choices"][0]["message"]["content"].strip()
            
            content = re.sub(r'^```json\s*', '', content, flags=re.IGNORECASE | re.MULTILINE)
            content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
            content = re.sub(r'^```\s*', '', content, flags=re.MULTILINE)
            
            # Try to parse JSON
            try:
                parsed_json = json.loads(content)
                return parsed_json
            except json.JSONDecodeError as e:
                return {"error": f"Invalid JSON response: {str(e)}", "raw_content": content[:500]}
                
        elif response.status_code == 401:
            return {"error": "Invalid API key"}
        elif response.status_code == 429:
            return {"error": "Rate limit exceeded"}
        else:
            return {"error": f"API Error {response.status_code}: {response.text}"}
            
    except requests.exceptions.Timeout:
        return {"error": "Request timeout - API took too long to respond"}
    except requests.exceptions.ConnectionError:
        return {"error": "Connection error - Unable to reach API"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

def process_single_jd(file_data):
    """Process a single job description file"""
    file_name, file_content, file_type = file_data
    jd_text, extraction_error = extract_text_optimized(file_content, file_type)
    
    if extraction_error:
        return file_name, {"error": extraction_error}, 0
    start_time = time.time()
    parsed_data = parse_jd_fast(jd_text)
    elapsed_time = time.time() - start_time
    
    return file_name, parsed_data, elapsed_time

# Streamlit
st.set_page_config(
    page_title="Fast JD Parser", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("Fast Job Description Parser")
st.markdown("Upload job description files or paste text to extract structured data using AI")

option = st.radio(
    "Choose input method:", 
    ["Upload JD File", "Paste JD Text"],
    horizontal=True
)

results = {}

if option == "Upload JD File":
    uploaded_files = st.file_uploader(
        "Upload JD Files (PDF or DOCX)",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        help="Select one or more PDF/DOCX files containing job descriptions"
    )

    if uploaded_files:
        if st.button("Process Files", type="primary"):
            status_placeholder = st.empty()
            timer_placeholder = st.empty()
            
            start_all = time.time()
            status_placeholder.info(f"🔄 Processing {len(uploaded_files)} file(s)...")

            file_data_list = []
            for f in uploaded_files:
                try:
                    file_content = f.read()
                    file_data_list.append((f.name, file_content, f.type))
                except Exception as e:
                    st.error(f"Error reading file {f.name}: {str(e)}")

            if file_data_list:
                if len(file_data_list) == 1:
                    file_name, parsed_data, elapsed_time = process_single_jd(file_data_list[0])
                    results[file_name] = (parsed_data, elapsed_time)
                else:
                    progress_bar = st.progress(0)
                    progress_text = st.empty()
                    
                    with ThreadPoolExecutor(max_workers=3) as executor:
                        future_to_file = {
                            executor.submit(process_single_jd, data): data[0]
                            for data in file_data_list
                        }
                        
                        completed = 0
                        for future in as_completed(future_to_file):
                            file_name = future_to_file[future]
                            try:
                                result_file_name, parsed_data, elapsed_time = future.result()
                                results[result_file_name] = (parsed_data, elapsed_time)
                            except Exception as e:
                                results[file_name] = ({"error": f"Processing error: {str(e)}"}, 0)
                            
                            completed += 1
                            progress = completed / len(file_data_list)
                            progress_bar.progress(progress)
                            progress_text.text(f"Processed {completed}/{len(file_data_list)} files")

                total_time = time.time() - start_all
                timer_placeholder.success(f"Total processing time: {total_time:.2f} seconds")
                status_placeholder.success("All files processed!")

elif option == "Paste JD Text":
    jd_text_input = st.text_area(
        "Paste Job Description here:", 
        height=300,
        placeholder="Copy and paste the job description text here..."
    )
    
    if st.button("Parse JD", type="primary"):
        if jd_text_input.strip():
            if len(jd_text_input.strip()) < 50:
                st.warning("⚠️ Please provide a longer job description (at least 50 characters)")
            else:
                with st.spinner("🔄 Parsing job description..."):
                    start = time.time()
                    parsed_data = parse_jd_fast(jd_text_input.strip())
                    elapsed = time.time() - start
                    results["pasted_text"] = (parsed_data, elapsed)
        else:
            st.warning("⚠️ Please paste a valid job description.")

if results:
    st.markdown("---")
    st.header("📊 Results")
    
    for file_name, (parsed_data, elapsed_time) in results.items():
        with st.expander(f"📄 {file_name} ({elapsed_time:.2f}s)", expanded=True):
            if "error" in parsed_data:
                st.error(f"Error: {parsed_data['error']}")
                if "raw_content" in parsed_data:
                    st.text("Raw API Response:")
                    st.code(parsed_data["raw_content"])
            else:
                st.success(f"Successfully parsed in {elapsed_time:.2f} seconds")
                
                st.json(parsed_data)
                
                json_str = json.dumps(parsed_data, indent=2)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_str,
                    file_name=f"{file_name.split('.')[0]}_parsed.json",
                    mime="application/json"
                )

    if len(results) > 1:
        st.markdown("---")
        st.subheader("📈 Summary")
        
        success_count = sum(1 for data, _ in results.values() if "error" not in data)
        fail_count = len(results) - success_count
        avg_time = sum(elapsed for _, elapsed in results.values()) / len(results)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📁 Total Files", len(results))
        col2.metric("✅ Successfully Parsed", success_count)
        col3.metric("❌ Failed", fail_count)
        col4.metric("⏱️ Avg Time", f"{avg_time:.2f}s")
