import streamlit as st
import PyPDF2
import google.generativeai as genai
import json
import re
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

# --- Function to extract text from PDF ---
def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + " "
    return text

# --- Function to generate quiz using Gemini ---
def generate_quiz_gemini(text, num_questions=5, difficulty="Medium"):
    try:
        prompt = f"""
        Create exactly {num_questions} multiple-choice quiz questions from the following text.

        Difficulty Level: {difficulty}
        - Easy: Focus on direct facts and simple recall.
        - Medium: Mix of factual and conceptual questions.
        - Hard: Analytical or higher-order thinking, may require inference.

        Each question must have:
        - "question": the full question text.
        - "options": an array of 4 full answer choices (not just letters).
        - "answer": the correct answer, copied exactly from one of the options.

        Rules:
        - Options must be complete meaningful answers, not just "A, B, C, D".
        - The correct answer must match exactly one of the options.
        - Return ONLY valid JSON (array of objects with "question", "options", "answer").

        Text:
        {text[:2000]}
        """
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)

        json_string = response.text.strip()
        json_string = re.sub(r"^```(?:json)?|```$", "", json_string, flags=re.MULTILINE).strip()
        raw_data = json.loads(json_string)

        quiz = []
        if isinstance(raw_data, list):
            quiz = raw_data
        elif isinstance(raw_data, dict):
            for value in raw_data.values():
                if isinstance(value, list) and value and "question" in value[0]:
                    quiz = value
                    break

        # Post-processing: clean options
        for item in quiz:
            cleaned_options = []
            for opt in item.get("options", []):
                if re.fullmatch(r"[A-D]", opt.strip(), re.IGNORECASE):
                    cleaned_options.append("⚠️ Option missing – please regenerate quiz")
                else:
                    cleaned_options.append(opt.strip())
            item["options"] = cleaned_options

        if not quiz:
            st.error("⚠️ The generated data did not match the expected quiz format. Please try again.")
            return []

        return quiz

    except json.JSONDecodeError as e:
        st.error(f"⚠️ Failed to parse quiz data. Malformed JSON. Details: {e}")
        return []
    except Exception as e:
        st.error(f"⚠️ Could not generate quiz: {e}")
        return []

# --- Function to generate PDF summary report ---
def generate_summary_pdf(quiz, user_answers, final_score, filename="summary_report.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Quiz Summary Report")
    y -= 30

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Final Score: {final_score}/{len(quiz)}")
    y -= 30

    for i, q in enumerate(quiz):
        user_answer = user_answers.get(f"user_answer_{i}", "Not answered")
        correct_answer = q["answer"]

        # Question
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, f"Q{i+1}. {q['question']}")
        y -= 20

        # Options with A, B, C, D
        c.setFont("Helvetica", 12)
        option_labels = ["A", "B", "C", "D"]
        for label, opt in zip(option_labels, q["options"]):
            c.drawString(70, y, f"{label}. {opt}")
            y -= 15

        # User Answer & Status
        if str(user_answer).strip().lower() == str(correct_answer).strip().lower():
            status = "✅ Correct"
        else:
            status = "❌ Wrong"

        c.drawString(70, y, f"Your Answer: {user_answer} ({status})")
        y -= 15
        c.drawString(70, y, f"Correct Answer: {correct_answer}")
        y -= 25

        # New page if space is low
        if y < 50:
            c.showPage()
            y = height - 50

    c.save()

# --- Streamlit App ---
st.set_page_config(page_title="Hafsa AI Quiz Generator", layout="centered")
st.title("📚 EduQuest AI-Powered Book Quiz Generator")

# --- Session state ---
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
    st.session_state.quiz_generated = False
    st.session_state.current_question_index = 0
    st.session_state.score = 0
    st.session_state.answered = []
    st.session_state.book_text = None
    st.session_state.num_questions = 5
    st.session_state.difficulty = "Medium"

# --- Input API Key ---
api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    try:
        genai.configure(api_key=api_key)

        # --- Upload + Generate Quiz ---
        if not st.session_state.quiz_generated:
            uploaded_file = st.file_uploader("Upload a book (PDF)", type=["pdf"])

            if uploaded_file:
                st.session_state.num_questions = st.selectbox(
                    "How many questions do you want?",
                    [5, 10, 15, 20],
                    index=0
                )

                st.session_state.difficulty = st.radio(
                    "Select Difficulty Level:",
                    ["Easy", "Medium", "Hard"],
                    index=1
                )

                if st.button("Generate Quiz"):
                    with st.spinner("Generating quiz... Please wait."):
                        text = extract_text_from_pdf(uploaded_file)
                        st.session_state.book_text = text
                        quiz = generate_quiz_gemini(
                            text,
                            num_questions=st.session_state.num_questions,
                            difficulty=st.session_state.difficulty
                        )
                        if quiz:
                            st.session_state.quiz_data = quiz
                            st.session_state.quiz_generated = True
                            st.session_state.current_question_index = 0
                            st.session_state.score = 0
                            st.session_state.answered = [False] * len(quiz)
                            st.rerun()

        # --- Display Quiz ---
        if st.session_state.quiz_generated and st.session_state.quiz_data:
            quiz = st.session_state.quiz_data
            num_questions = len(quiz)

            if st.session_state.current_question_index < num_questions:
                q_index = st.session_state.current_question_index
                q = quiz[q_index]

                st.markdown("---")
                st.subheader(f"Question {q_index + 1} of {num_questions}")
                st.write(f"**Question**: {q['question']}")

                choice = st.radio("Options:", q["options"], key=f"q{q_index}")

                if not st.session_state.answered[q_index]:
                    if st.button("Submit Answer", key=f"submit_{q_index}"):
                        st.session_state.answered[q_index] = True
                        st.session_state[f"user_answer_{q_index}"] = choice

                        if choice.strip().lower() == q["answer"].strip().lower():
                            st.success("✅ Correct!")
                            st.session_state.score += 1
                        else:
                            st.error(f"❌ Wrong! The correct answer was: {q['answer']}")

                if st.session_state.answered[q_index]:
                    if st.button("Next Question"):
                        st.session_state.current_question_index += 1
                        st.rerun()

            else:
                # --- Quiz Complete ---
                st.markdown("---")
                st.balloons()
                st.header("Quiz Complete!")

                # --- Final Score + Buttons Row ---
                st.info(f"### Your Final Score: {st.session_state.score}/{num_questions}")
                col1, col2 = st.columns([1,1])
                with col1:
                    if st.button("Regenerate Quiz For Same PDF"):
                        with st.spinner("Regenerating new quiz... Please wait."):
                            text = st.session_state.book_text
                            quiz = generate_quiz_gemini(
                                text,
                                num_questions=st.session_state.num_questions,
                                difficulty=st.session_state.difficulty
                            )
                            if quiz:
                                st.session_state.quiz_data = quiz
                                st.session_state.quiz_generated = True
                                st.session_state.current_question_index = 0
                                st.session_state.score = 0
                                st.session_state.answered = [False] * len(quiz)
                                for i in range(len(quiz)):
                                    if f"user_answer_{i}" in st.session_state:
                                        del st.session_state[f"user_answer_{i}"]
                                st.rerun()
                with col2:
                    if st.button("Restart Quiz App"):
                        st.session_state.quiz_generated = False
                        st.rerun()

                # --- Summary Report ---
                st.subheader("📊 Summary Report")
                for i, q in enumerate(quiz):
                    user_answer = st.session_state.get(f"user_answer_{i}", "Not answered")
                    correct_answer = q["answer"]

                    if str(user_answer).strip().lower() == str(correct_answer).strip().lower():
                        st.markdown(
                            f"**Q{i+1}. {q['question']}**  \n"
                            f"Your Answer: ✅ {user_answer}  \n"
                            f"Correct Answer: {correct_answer}"
                        )
                    else:
                        st.markdown(
                            f"**Q{i+1}. {q['question']}**  \n"
                            f"Your Answer: ❌ {user_answer}  \n"
                            f"Correct Answer: ✅ {correct_answer}"
                        )

                # --- Download Quiz JSON & CSV ---
                quiz_json = json.dumps(quiz, indent=2)
                st.download_button(
                    label="⬇️ Download Quiz (JSON)",
                    data=quiz_json,
                    file_name="quiz.json",
                    mime="application/json"
                )

                quiz_df = pd.DataFrame([
                    {
                        "Question": q["question"],
                        "Option A": q["options"][0],
                        "Option B": q["options"][1],
                        "Option C": q["options"][2],
                        "Option D": q["options"][3],
                        "Answer": q["answer"]
                    }
                    for q in quiz
                ])
                csv_data = quiz_df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download Quiz (CSV)",
                    data=csv_data,
                    file_name="quiz.csv",
                    mime="text/csv"
                )

                # --- Download Summary PDF ---
                user_answers = {f"user_answer_{i}": st.session_state.get(f"user_answer_{i}", "Not answered")
                                for i in range(len(quiz))}
                pdf_filename = "summary_report.pdf"
                generate_summary_pdf(quiz, user_answers, st.session_state.score, filename=pdf_filename)
                with open(pdf_filename, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Summary Report (PDF)",
                        data=f,
                        file_name="summary_report.pdf",
                        mime="application/pdf"
                    )

        # --- Copyright Footer ---
        st.markdown(
            """
            <hr>
            <p style='text-align: center; color: gray; font-size:12px;'>
            © 2025 Hafsa Nameerah 8C MMEIS. All rights reserved.
            </p>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ Failed to configure Gemini API. Please check your API key: {e}")
