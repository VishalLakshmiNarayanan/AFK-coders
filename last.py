
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
    html, body, [class*="css"] {
        font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
        background-color: #0e0e10;
        color: #ffffff;
    }
    .stApp {
        background-color: #0e0e10;
    }
    .stButton>button {
        background-color: #2a2a40;
        color: #ffffff;
        font-weight: bold;
        border-radius: 6px;
        padding: 0.5em 1.2em;
    }
    .stTextInput>div>div>input {
        background-color: #1c1c2a;
        color: #ffffff;
    }
    .stDataFrame {
        background-color: #1c1c2a;
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True
)




theme_color = {
    "light": {
        "bg": "#ffffffcc",
        "img": {
            "home": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d",
            "recruiter": "https://images.unsplash.com/photo-1551836022-d5d88e9218df",
            "applicant": "https://images.unsplash.com/photo-1605902711622-cfb43c4437d2"
        }
    },
    "dark": {
        "bg": "#1e1e2fcc",
        "img": {
            "home": "https://images.unsplash.com/photo-1557682224-5b8590cd9ec5",
            "recruiter": "https://images.unsplash.com/photo-1521737604893-d14cc237f11d",
            "applicant": "https://images.unsplash.com/photo-1549924231-f129b911e442"
        }
    }
}


def set_background(page):
    bg_url = theme_color[st.session_state['theme']]['img'][page]
    bg_overlay = theme_color[st.session_state['theme']]['bg']
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient({bg_overlay}, {bg_overlay}), url('{bg_url}');
            background-size: cover;
            background-attachment: fixed;
            background-repeat: no-repeat;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )


st.markdown(
    """
    <style>
    .stApp {
        background-image: url('https://images.unsplash.com/photo-1504384308090-c894fdcc538d');
        background-size: cover;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }
    </style>
    """,
    unsafe_allow_html=True
)


if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'

mode = st.sidebar.radio("Theme", ['light', 'dark'])
st.session_state['theme'] = mode

if mode == 'dark':
    st.markdown("""
        <style>
        body { background-color: #0e1117; color: white; }
        .stApp { background-color: #0e1117; }
        </style>
    """, unsafe_allow_html=True)
""


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
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE username = ? AND password = ?", (user, hash_password(pwd)))
            data = cursor.fetchone()
            conn.close()
            if data:
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.role = data[0]
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

else:
    st.sidebar.success(f"Logged in as: {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.experimental_rerun()

    if st.session_state.role == "recruiter":
        st.header("📢 Recruiter Dashboard")
        with st.form("job_post_form"):
            title = st.text_input("Job Title")
            desc = st.text_area("Job Description")
            skills = st.text_input("Required Skills (comma separated)")
            submitted = st.form_submit_button("Post Job")
            if submitted:
                add_job(title, desc, skills, st.session_state.username)
                st.success("✅ Job posted")

        st.subheader("🗑 Your Jobs")
        all_jobs = get_jobs()
        for job in all_jobs:
            if job[4] == st.session_state.username:
                with st.expander(f"{job[1]}"):
                    st.write(job[2])
                    if st.button("Remove", key=f"delete_{job[0]}"):
                        delete_job(job[0])
                        st.experimental_rerun()

    elif st.session_state.role == "applicant":
        st.header("📄 Applicant Dashboard")
        resume = st.file_uploader("Upload Resume (PDF)", type="pdf")
        if st.button("Upload") and resume:
            text = extract_text_from_pdf(resume)
            save_resume(st.session_state.username, text)
            st.success("✅ Resume saved")

        stored_resume = get_user_resume(st.session_state.username)
        if stored_resume:
            jobs = get_jobs()
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

                    st.markdown(f"### 🏢 {job[1]}")
                    st.markdown(f"📄 **Description:** {job[2]}")
                    st.markdown(f"✅ **Matched Skills:** `{', '.join(matched_skills)}`")
                    st.markdown(f"❌ **Missing Skills:** `{', '.join(missing_skills)}`")
                    st.markdown(f"📊 **Skill Match Score:** `{score}%`")

                    for skill in missing_skills:
                        course_table.append({
                            "Job": job[1],
                            "Skill": skill,
                            "Course": "https://www.coursera.org/search?query={skill.replace('%20',%20'+')}"
                        })

                    st.markdown("---")

                df = pd.DataFrame(scores)
                st.subheader("📊 Match Score Comparison")
                st.bar_chart(df.set_index("Job"))

                st.subheader("📚 Recommended Courses")
                if course_table:
                    st.dataframe(pd.DataFrame(course_table))
                else:
                    st.info("No missing skills found.")
            else:
                st.info("No jobs available.")
        else:
            st.warning("Please upload your resume to get match scores.")
