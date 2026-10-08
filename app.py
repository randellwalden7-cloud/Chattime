import os
import json
import streamlit.components.v1 as components
import sqlite3
import time
import streamlit as st
from dotenv import load_dotenv
from core import run_agent
from storage import Storage
import billing

load_dotenv()
st.set_page_config(page_title='Chattime Assistant', page_icon='💬', layout='wide')
st.markdown('''<style>.stApp{background:#0f172a;color:#f8fafc}
section[data-testid="stSidebar"]{background:#172238}
h1{color:#38bdf8}div[data-testid="stChatMessage"]{border:1px solid #334155;border-radius:12px}</style>''',
            unsafe_allow_html=True)
db = Storage(os.getenv('CHATTIME_DB', 'data/chattime.db'))
st.title('Chattime Assistant')
st.markdown('''<a href="https://www.biblegateway.com/passage/?search=Genesis%201&amp;version=KJV" target="_blank" rel="noopener noreferrer" aria-label="Open the King James Bible in a new tab" style="display:inline-flex;align-items:center;gap:12px;max-width:100%;box-sizing:border-box;padding:14px 18px;margin:8px 0 16px;border:1px solid #f5d77a;border-radius:12px;background:#142238;color:#fff4ca;text-decoration:none"><span aria-hidden="true" style="font-size:24px">📖</span><span><strong>King James Bible</strong><br><span style="font-size:13px">Read the KJV · Opens in a new tab ↗</span></span></a>''', unsafe_allow_html=True)


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
if st.sidebar.button('Sign out', key='membership-signout'):
    st.session_state.clear()
    st.rerun()
try:
    paid = billing.allowed(db, username)
except Exception:
    paid = False
    st.warning('Membership verification is temporarily unavailable. Please retry; do not pay again.')
if not paid:
    st.subheader('Chattime membership — $9.99/month')
    st.write('Sign in with this same account after payment. Your membership renews monthly until canceled.')
    if not billing.configured():
        st.info('Payment setup is in progress. Subscriptions and chat are not open yet.')
    else:
        if st.button('Subscribe for $9.99/month'):
            try:
                st.link_button('Continue to secure Stripe Checkout', billing.checkout(db, username))
            except ValueError as error:
                st.info(str(error))
            except Exception:
                st.error('Checkout could not open. Please retry later.')
        if st.button('Refresh membership'):
            st.rerun()
    st.stop()
if st.sidebar.button('Manage subscription'):
    try:
        st.sidebar.link_button('Open Stripe customer portal', billing.portal(db, username))
    except Exception:
        st.sidebar.error('Subscription management is unavailable. Please retry later.')
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

# Playback starts on a user click to satisfy browser audio policies.
answers = [r for r in history if r['role'] == 'assistant']
with st.expander('Voice reader', expanded=True):
    st.caption('Choose a reply and press Read aloud. Voices depend on your device.')
    if answers:
        selected = st.selectbox('Reply to read', list(range(len(answers))),
            index=len(answers)-1, format_func=lambda i: answers[i]['content'][:80])
        speech_text = answers[selected]['content']
    else:
        speech_text = 'Hello! Chattime Assistant voice playback is ready.'
    payload = json.dumps(speech_text).replace('<', '\\u003c')
    components.html(r"""
<style>
body{font:16px sans-serif;color:#f8fafc;background:#0f172a}
button,select{min-height:44px;margin:4px;padding:8px;border-radius:8px}
button{background:#38bdf8;color:#0f172a;border:0}select{max-width:95%}
</style>
<label for="voice">Voice </label><select id="voice"><option value="">Device default</option></select>
<br><label for="speed">Speed </label><input id="speed" type="range" min="0.5" max="1.5" step="0.1" value="1"><output id="rate">1×</output>
<br><button id="read">Read aloud</button><button id="test">Test sound</button>
<button id="pause">Pause</button><button id="resume">Resume</button><button id="stop">Stop</button>
<p id="status" role="status" aria-live="polite">Press Test sound to check your speakers.</p>
<script>
const text = """ + payload + r""";
const status = document.getElementById('status');
const synth = window.speechSynthesis;
const picker = document.getElementById('voice');
let voices = [], active = null, generation = 0;
if (!synth) {
  status.textContent = 'Voice playback is unavailable in this browser. Open Chattime in Chrome or Edge.';
  document.querySelectorAll('button').forEach(b => b.disabled = true);
} else {
  function loadVoices() {
    const previous = picker.value;
    voices = synth.getVoices();
    picker.replaceChildren(new Option('Device default', ''));
    voices.forEach(v => picker.add(new Option(v.name + ' (' + v.lang + ')', v.voiceURI)));
    if (voices.some(v => v.voiceURI === previous)) picker.value = previous;
  }
  loadVoices();
  synth.addEventListener('voiceschanged', loadVoices);
  function stop() { generation++; synth.cancel(); active = null; }
  function read(value) {
    stop();
    const token = generation;
    const chunks = value.match(/[\s\S]{1,220}(?:\s|$)|[\s\S]{1,220}/g) || [];
    let index = 0;
    function next() {
      if (token !== generation) return;
      if (index >= chunks.length) { status.textContent = 'Finished'; active = null; return; }
      active = new SpeechSynthesisUtterance(chunks[index++]);
      active.voice = voices.find(v => v.voiceURI === picker.value) || null;
      active.rate = Number(document.getElementById('speed').value);
      active.volume = 1;
      active.onstart = () => { status.textContent = 'Speaking'; };
      active.onend = next;
      active.onerror = e => {
        if (token === generation) status.textContent = 'Playback failed: ' + e.error + '. Try Test sound or another voice.';
      };
      synth.speak(active);
    }
    status.textContent = 'Starting voice…';
    next();
  }
  document.getElementById('read').onclick = () => read(text);
  document.getElementById('test').onclick = () => read('Hello! This is Chattime Assistant. Your sound is working.');
  document.getElementById('pause').onclick = () => { synth.pause(); status.textContent = 'Paused'; };
  document.getElementById('resume').onclick = () => { synth.resume(); status.textContent = 'Resuming'; };
  document.getElementById('stop').onclick = () => { stop(); status.textContent = 'Stopped'; };
  window.addEventListener('pagehide', stop);
}
document.getElementById('speed').oninput = e => { document.getElementById('rate').textContent = e.target.value + '×'; };
</script>
""", height=245)

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
