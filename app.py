import streamlit as st

from analyzer import analyse, read_resume

st.set_page_config(page_title="Resume Analyzer", layout="centered")
st.title("Resume Analyzer")
st.write("Compare the skills in a resume with the requirements for one role.")
with st.form("comparison"):
    file = st.file_uploader("Resume PDF", type="pdf")
    job = st.text_area("Job description", placeholder="Paste the role and its required skills.")
    submit = st.form_submit_button("Compare skills", type="primary")
if submit:
    try:
        if file is None:
            raise ValueError("Choose a resume PDF first.")
        with st.spinner("Reading the resume and comparing skills…"):
            result = analyse(read_resume(file.getvalue()), job)
        score = result["match_score"]
        st.subheader(f"Skill coverage · {score}%")
        st.progress(score)
        st.caption("Share of identified job skills explicitly mentioned in the resume.")
        left, right = st.columns(2)
        for col, label, key in [(left, "Matched skills", "matched_skills"),
                                (right, "Missing skills", "missing_skills")]:
            col.markdown(f"**{label}**")
            col.text("\n".join(result[key]) or "None identified")
        st.subheader("Three improvement tips")
        for i, tip in enumerate(result["tips"], 1):
            st.write(f"{i}. {tip}")
    except ValueError as exc:
        st.error(str(exc))
