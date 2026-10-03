import os
import sqlite3
import time
import streamlit as st
from dotenv import load_dotenv
from core import run_agent
from storage import Storage

load_dotenv()
st.set_page_config(page_title='Chattime Assistant', page_icon='💬', layout='wide')
st.markdown('''<style>.stApp{background:#0f172a;color:#f8fafc}
section[data-testid="stSidebar"]{background:#172238}
h1{color:#38bdf8}div[data-testid="stChatMessage"]{border:1px solid #334155;border-radius:12px}</style>''',
            unsafe_allow_html=True)
db = Storage(os.getenv('CHATTIME_DB', 'data/chattime.db'))
st.title('Chattime Assistant')

if 'username' not in st.session_state:
    login, register = st.tabs(['Sign in', 'Create account'])
    with login:
        with st.form('login'):
            username = st.text_input('Username').strip().lower()
            password = st.text_input('Password', type='password')
            if st.form_submit_button('Sign in'):
                next_try = st.session_state.get('next_try', 0)
                if time.time() < next_try:
                    st.error('Please wait before trying again.')
                elif db.verify(username, password):
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.session_state.next_try = time.time() + 3
                    st.error('Username or password is incorrect.')
    with register:
        with st.form('register'):
            new_user = st.text_input('Choose a username')
            new_pass = st.text_input('Choose a password', type='password')
            repeat = st.text_input('Repeat password', type='password')
            if st.form_submit_button('Create account'):
                try:
                    if new_pass != repeat:
                        raise ValueError('Passwords do not match.')
                    db.register(new_user, new_pass)
                    st.success('Account created. Sign in to continue.')
                except sqlite3.IntegrityError:
                    st.error('Username is already taken.')
                except ValueError as error:
                    st.error(str(error))
    st.stop()

username = st.session_state.username
with st.sidebar:
    st.subheader(username)
    engine = st.radio('Engine', ['cloud', 'local'], format_func=lambda x: {'cloud':'OpenAI Cloud', 'local':'Ollama Local'}[x])
    search = st.toggle('Enable web search', value=False)
    if engine == 'local':
        st.caption('Ollama must run on the app server. Web search sends queries to Tavily when enabled.')
    else:
        st.caption('Cloud messages are sent to OpenAI and incur API usage charges.')
    if st.button('Sign out'):
        st.session_state.clear()
        st.rerun()
    confirm = st.checkbox('Confirm deleting this engine’s saved chat')
    if st.button('Reset chat', disabled=not confirm):
        db.clear(username, engine)
        st.rerun()

history = db.load(username, engine)
transcript = '\n\n'.join(f"{r['role'].upper()}: {r['content']}" for r in history)
st.sidebar.download_button('Export transcript', transcript, 'chattime-chat.txt', 'text/plain')
st.sidebar.caption(f"Recorded tokens: {sum(r['input_tokens'] + r['output_tokens'] for r in history):,}")
for message in history:
    with st.chat_message(message['role']):
        st.markdown(message['content'])
        if message['role'] == 'assistant':
            a, b, _ = st.columns([1,1,8])
            if a.button('👍', key=f"up-{message['id']}"):
                db.feedback(username, message['id'], 1)
                st.toast('Feedback saved')
            if b.button('👎', key=f"down-{message['id']}"):
                db.feedback(username, message['id'], 0)
                st.toast('Feedback saved')
if not history:
    st.info('Ask a question, write a draft, or calculate a room’s square footage.')
if prompt := st.chat_input('Message Chattime Assistant', max_chars=8000):
    with st.chat_message('user'):
        st.write(prompt)
    with st.chat_message('assistant'):
        status = st.empty()
        try:
            current = [{'role': r['role'], 'content': r['content']} for r in history]
            current.append({'role':'user', 'content':prompt})
            answer, usage = run_agent(engine, current, search, status.info)
            db.save(username, engine, 'user', prompt)
            db.save(username, engine, 'assistant', answer, usage)
            st.rerun()
        except ValueError as error:
            status.error(str(error))
        except Exception:
            status.error('The AI service could not answer. Check the server credentials, model, and connection. Your saved chat is intact.')
