# 📚 EduQuest AI – Book Quiz Generator

An AI-powered Streamlit app that generates quizzes from PDF books using **Google Gemini AI**.

---

## 🚀 Features
- Upload any PDF book.
- Generate AI-powered quizzes (Easy / Medium / Hard).
- Interactive multiple-choice quiz.
- Download results as **JSON, CSV, and PDF summary**.
- Built with Streamlit.

---

## ▶️ Run Locally

1. Clone this repo:
   ```bash
   git clone https://github.com/your-username/BookQuizApp.git
   cd BookQuizApp
   ```

2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:
   ```bash
   streamlit run app.py
   ```

---

## 🌐 Deploy on Streamlit Cloud

1. Push this repo to your GitHub.
2. Go to [Streamlit Cloud](https://share.streamlit.io).
3. Click **New App** → select this repo → `main` branch → `app.py`.
4. Set your **Google Gemini API Key** in Streamlit Cloud:
   - Settings → Secrets → add  
     ```
     GOOGLE_API_KEY="your_api_key_here"
     ```
5. Done! Your app is live 🎉
