
import streamlit as st
from sentence_transformers import SentenceTransformer, util
import pdfplumber
import sqlite3
import hashlib
import os
import re
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="AI Job Portal", layout="wide")







st.markdown(
    """
    <style>
    html, body {
        font-family: 'Segoe UI', 'Roboto', sans-serif;
        background-color: #0e1117;
        color: #ffffff;
        transition: all 0.5s ease;
    }
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stButton>button {
        background-color: #2a2a40;
        color: #ffffff;
        font-weight: bold;
        border-radius: 6px;
        padding: 0.5em 1.2em;
        transition: all 0.3s ease;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    .stButton>button:hover {
        background-color: #44475a;
        transform: scale(1.05);
        box-shadow: 2px 4px 8px rgba(0,0,0,0.4);
    }
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea {
        background-color: #1c1c2a;
        color: #ffffff;
        transition: background-color 0.3s ease;
        border: 1px solid #555;
    }
    .stDataFrame {
        background-color: #1c1c2a;
        color: #ffffff;
    }
    .block-container {
        animation: fadeIn 1s ease-in-out;
        padding: 2rem;
    }
    .stHeader, .stSubheader {
        animation: slideDown 1s ease-in-out;
    }
    .stMarkdown {
        animation: slideLeft 0.8s ease-in-out;
    }
    @keyframes fadeIn {
        from {opacity: 0;}
        to {opacity: 1;}
    }
    @keyframes slideDown {
        from {transform: translateY(-10px); opacity: 0;}
        to {transform: translateY(0); opacity: 1;}
    }
    @keyframes slideLeft {
        from {transform: translateX(-10px); opacity: 0;}
        to {transform: translateX(0); opacity: 1;}
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        margin-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)





model = SentenceTransformer('all-MiniLM-L6-v2')
DB_PATH = 'jobs.db'

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

def preprocess(text):
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def compare_resume_with_jd(resume_text, jd_text):
    resume_embed = model.encode(preprocess(resume_text), convert_to_tensor=True)
    jd_embed = model.encode(preprocess(jd_text), convert_to_tensor=True)
    similarity = util.cos_sim(resume_embed, jd_embed).item()
    return round(similarity * 100, 2)

def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT,
        resume TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        skills TEXT,
        posted_by TEXT
    )''')
    conn.commit()
    conn.close()

def add_job(title, description, skills, posted_by):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO jobs (title, description, skills, posted_by) VALUES (?, ?, ?, ?)",
                   (title, description, skills, posted_by))
    conn.commit()
    conn.close()

def get_jobs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, skills, posted_by FROM jobs")
    jobs = cursor.fetchall()
    conn.close()
    return jobs

def delete_job(job_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

def save_resume(username, resume_text):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET resume = ? WHERE username = ?", (resume_text, username))
    conn.commit()
    conn.close()

def get_user_resume(username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT resume FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# UI Logic
create_tables()
if 'applications' not in st.session_state:
    st.session_state.applications = []

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

st.title("🧠 Smart AI-Powered Job Portal")

if not st.session_state.logged_in:
    menu = ["Login", "Sign Up"]
    choice = st.sidebar.radio("Menu", menu)
    if choice == "Sign Up":
        st.subheader("Create Account")
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["applicant", "recruiter"])
        if st.button("Sign Up"):
            if not new_user or not new_pass:
                st.error("❌ Username and password cannot be empty.")
            else:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                                (new_user, hash_password(new_pass), role))
                    conn.commit()
                    st.success("✅ Account created!")
                except:
                    st.error("Username already exists.")
                conn.close()

    elif choice == "Login":
        st.subheader("Login")
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if not user or not pwd:
                st.error("❌ Please enter both username and password.")
            else:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT role FROM users WHERE username = ? AND password = ?", (user, hash_password(pwd)))
                data = cursor.fetchone()
                conn.close()
                if data:
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.session_state.role = data[0]
                    st.rerun()
                else:
                    st.error("Invalid credentials")

else:
    st.sidebar.success(f"Logged in as: {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.rerun()

    if st.session_state.role == "recruiter":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.header("📢 Recruiter Dashboard")
        with st.form("job_post_form"):
            title = st.text_input("Job Title")
            desc = st.text_area("Job Description")
            skills = st.text_input("Required Skills (comma separated)")
            submitted = st.form_submit_button("Post Job")
            if submitted:
                add_job(title, desc, skills, st.session_state.username)
                st.success("✅ Job posted")

        st.markdown("</div>", unsafe_allow_html=True)

        
        st.subheader("📑 User Applications")
        my_apps = [app for app in st.session_state.applications if app["recruiter"] == st.session_state.username]
        for app in my_apps:
            st.markdown(f"👤 **Applicant:** `{app['applicant']}`")
            st.markdown(f"📌 **Job Applied:** `{app['job_title']}`")
            st.markdown(f"🧠 **Skills Summary:** {', '.join(app['skills'])}")
            st.download_button("⬇️ Download Resume", app['resume'], file_name=app['resume_name'])
            st.markdown("---")

        st.subheader("🗑 Your Jobs")
        all_jobs = get_jobs()
        for job in all_jobs:
            if job[4] == st.session_state.username:
                with st.expander(f"{job[1]}"):
                    st.write(job[2])
                    if st.button("Remove", key=f"delete_{job[0]}"):
                        delete_job(job[0])
                        st.rerun()

    elif st.session_state.role == "applicant":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.header("📄 Applicant Dashboard")
        resume = st.file_uploader("Upload Resume (PDF)", type="pdf")
        if st.button("Upload") and resume:
            with st.spinner("Extracting resume..."):
                text = extract_text_from_pdf(resume)
            save_resume(st.session_state.username, text)
            st.success("✅ Resume saved")

        st.markdown("</div>", unsafe_allow_html=True)

      

        
        
        stored_resume = get_user_resume(st.session_state.username)
        if stored_resume:
            import json
            with open("simulated_jobs.json") as f:
                json_jobs = json.load(f)
                simulated_tuples = [(j["id"], j["title"], j["description"], j["skills"], j["posted_by"]) for j in json_jobs]
                job_data = get_jobs() + simulated_tuples

            # Injected simulated LinkedIn jobs
            linkedin_jobs = [
                (9991, "Backend Developer", "Work with Python and Django to build scalable backend APIs for enterprise applications.", "Python, Django, REST, SQL", "LinkedIn"),
                (9992, "Frontend Engineer", "ReactJS developer needed to create interactive UI components and maintain frontend infrastructure.", "React, JavaScript, HTML, CSS", "LinkedIn"),
                (9993, "Data Analyst", "Analyze large datasets using SQL and Python. Build dashboards and support data-driven decision making.", "SQL, Python, Data Visualization", "LinkedIn"),
                (9994, "Machine Learning Intern", "Support machine learning experiments and data preprocessing tasks using Scikit-learn and Pandas.", "Python, Scikit-learn, Pandas, Jupyter", "LinkedIn")
            ]

            job_data += linkedin_jobs

            search_query = st.text_input("🔍 Search for jobs", placeholder="e.g., Python developer, SQL analyst")

            if search_query:
                categories = ["Python", "Java", "React", "SQL", "Flask", "Machine Learning", "Frontend", "Backend"]
                category_counts = {cat: 0 for cat in categories}

                for job in job_data:
                    for cat in categories:
                        if cat.lower() in job[2].lower():
                            category_counts[cat] += 1

                selected_filters = st.multiselect(
                    "📂 Filter by Job Tags",
                    options=[f"{cat} ({category_counts[cat]})" for cat in categories if category_counts[cat] > 0]
                )

                filtered_jobs = []
                for job in job_data:
                    job_text = job[2].lower()
                    if (not selected_filters or any(cat.lower() in job_text for cat in categories if f"{cat} ({category_counts[cat]})" in selected_filters)) and                (search_query.lower() in job[2].lower() or search_query.lower() in job[1].lower()):
                        filtered_jobs.append(job)

                jobs = filtered_jobs
            else:
                jobs = []

            if jobs:
                st.subheader("📈 Resume Match Scores")
                scores = []
                course_table = []

                parsed_skills = [s for s in ["Python", "SQL", "Flask", "Java", "JavaScript", "HTML", "CSS", "React"] if s.lower() in stored_resume.lower()]
                st.markdown("**🧠 Parsed Skills:** `" + ", ".join(parsed_skills) + "`")

                for job in jobs:
                    required_skills = [s.strip() for s in job[3].split(",")]
                    matched_skills = [s for s in required_skills if s.lower() in stored_resume.lower()]
                    missing_skills = [s for s in required_skills if s not in matched_skills]
                    score = int(len(matched_skills) / len(required_skills) * 100) if required_skills else 0
                    scores.append({"Job": job[1], "Score": score})

                    with st.container():
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.markdown(f"### 🏢 {job[1]}")
                            st.markdown(f"📄 **Description:** {job[2]}")
                            st.markdown(f"🏢 **Posted By:** {job[4]}")
                            st.markdown(f"✅ **Matched Skills:** `{', '.join(matched_skills)}`")
                            st.markdown(f"❌ **Missing Skills:** `{', '.join(missing_skills)}`")
                            for skill in missing_skills:
                                st.markdown(f"🔗 [Recommended Course for {skill}](https://www.coursera.org/search?query={skill.replace(' ', '%20')})")
                            st.markdown(f"📊 **Skill Match Score:** `{score}%`")
                        with col2:
                            applied_jobs = [a["job_id"] for a in st.session_state.applications if a["applicant"] == st.session_state.username]
                            if job[0] in applied_jobs:
                                st.markdown("✅ **Applied to this job**")
                            else:
                                uploaded_file = st.file_uploader(f"Upload Resume for {job[1]}", type="pdf", key=f"resume_{job[0]}")
                                if uploaded_file and st.button(f"Apply to {job[1]}", key=f"apply_{job[0]}"):
                                    st.session_state.applications.append({
                                        "job_id": job[0],
                                        "job_title": job[1],
                                        "recruiter": job[4],
                                        "applicant": st.session_state.username,
                                        "skills": parsed_skills,
                                        "resume": uploaded_file.getvalue(),
                                        "resume_name": uploaded_file.name
                                    })
                                    st.success(f"✅ Applied to {job[1]}")

                    for skill in missing_skills:
                        course_table.append({
                            "Job": job[1],
                            "Skill": skill,
                            "Course": f"https://www.coursera.org/search?query={skill.replace(' ', '%20')}"
                        })

                    st.markdown("---")

                df = pd.DataFrame(scores)
                st.subheader("📊 Match Score Comparison")
                st.bar_chart(df.set_index("Job"))
            else:
                st.info("No jobs available.")
        else:
            st.warning("Please upload your resume to get match scores.")
