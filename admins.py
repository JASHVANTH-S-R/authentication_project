import pandas as pd
import streamlit as st

# Load data
users_df = pd.read_csv("users.csv")
question_dfs = {
    "Preference": pd.read_csv("preference_questions.csv"),
    "Knowledge": pd.read_csv("knowledge_questions.csv"),
    "Identity": pd.read_csv("identity_questions.csv"),
    "Experience": pd.read_csv("experience_questions.csv")
}

# Define app
def main():
    st.title("User Questionnaire Data (Admin Access Only)")

    # Authentication
    username = st.text_input("Enter your email:")
    password = st.text_input("Enter your password:", type="password")

    if authenticate(username, password):
        user_role = get_user_role(username)
        if user_role == "Admin":
            display_admin_view()
        else:
            st.error("You do not have permission to access this page.")
    else:
        st.error("Authentication failed. Please enter valid credentials.")


# Function to authenticate user
def authenticate(username, password):
    user = users_df[(users_df['emailID'] == username) & (users_df['Password'] == password)]
    return not user.empty


# Function to get user role
def get_user_role(username):
    user = users_df[users_df['emailID'] == username]
    if not user.empty:
        return user.iloc[0]['Role']
    return None


# Function to display questions and answers for Admin
def display_admin_view():
    st.header("Admin View")
    question_type = st.selectbox("Select question type:", list(question_dfs.keys()))
    selected_user = st.selectbox("Select user:", users_df['emailID'])
    user_row = users_df[users_df['emailID'] == selected_user]
    if not user_row.empty:
        user_index = user_row.index[0]
        questions = question_dfs[question_type].iloc[:, 0]
        answers = question_dfs[question_type].iloc[:, user_index + 1]
        data = pd.DataFrame({"Questions": questions, "Answers": answers})
        st.table(data)


if __name__ == "__main__":
    main()
