"""Global CSS for Oran AI (dark theme, warm red accent)."""


def global_css(tomato_frames):
    TOMATO_FRAMES = tomato_frames
    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800&family=IBM+Plex+Sans+Thai:wght@300;400;500;600&display=swap');

        :root {{
            --bg: #110A0B;
            --bg-soft: #170D0E;
            --surface: #1B0F10;
            --surface-2: #221314;
            --surface-hover: #2A1719;
            --border: #3A1C1E;
            --text: #F2F1ED;
            --text-dim: #A89A9A;
            --text-faint: #786A6A;
            --accent-yellow: #FB3424;
            --accent-orange: #D21B2A;
            --accent-green: #1FBE6B;
            --radius-lg: 20px;
            --radius-md: 14px;
            --radius-sm: 10px;
        }}

        html, body, [class*="css"] {{
            font-family: 'IBM Plex Sans Thai', 'Outfit', sans-serif;
        }}

        .stApp {{
            background: var(--bg);
            color: var(--text);
        }}

        h1, h2, h3, h4 {{
            font-family: 'Outfit', 'IBM Plex Sans Thai', sans-serif !important;
            letter-spacing: -0.01em;
        }}

        /* Hide default Streamlit chrome (menu + footer only — keep header so the sidebar toggle still works) */
        #MainMenu, footer {{visibility: hidden;}}
        [data-testid="stHeader"] {{
            background: transparent;
        }}

        /* ---------- SIDEBAR (Claude-style: dark, collapsible) ---------- */
        [data-testid="stSidebar"] {{
            background: var(--bg-soft);
            border-right: 1px solid var(--border);
        }}
        [data-testid="stSidebarContent"] {{
            scrollbar-width: none;
            height: 100vh;
            max-height: 100vh;
            overflow: hidden !important;
        }}
        [data-testid="stSidebarContent"]::-webkit-scrollbar {{ display: none; }}
        /* Style Streamlit's native collapse control to match the dark theme */
        [data-testid="stSidebarCollapsedControl"] button,
        [data-testid="stBaseButton-headerNoPadding"] {{
            color: var(--text-dim) !important;
        }}
        [data-testid="collapsedControl"] {{
            background: var(--bg-soft);
        }}

        /* ---------- BRAND HEADER (sidebar, top-left) ---------- */
        .brand-row {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 4px 2px 18px 2px;
        }}
        .brand-row img {{
            width: 30px;
            height: 30px;
            object-fit: contain;
            border-radius: 8px;
        }}
        .brand-row .brand-name {{
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 16px;
            color: var(--text);
            letter-spacing: -0.01em;
        }}

        /* ---------- BUTTONS ---------- */
        .stButton > button {{
            background: var(--surface-2);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            font-weight: 500;
            transition: all 0.12s ease;
        }}
        .stButton > button:hover {{
            background: var(--surface-hover);
            color: var(--text);
            border-color: var(--accent-orange);
        }}
        /* Primary buttons (New chat) get the brand gradient */
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, var(--accent-yellow), var(--accent-orange));
            color: #FFFFFF;
            border: none;
            font-weight: 600;
            box-shadow: 0 4px 16px rgba(216, 30, 40, 0.35);
        }}
        .stButton > button[kind="primary"]:hover {{
            color: #FFFFFF;
            filter: brightness(1.08);
            box-shadow: 0 6px 22px rgba(216, 30, 40, 0.5);
        }}

        /* ---------- TEXT INPUTS ---------- */
        .stTextInput > div > div > input {{
            background: var(--surface-2);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
        }}
        .stTextInput > div > div > input:focus {{
            border-color: var(--accent-green);
            box-shadow: 0 0 0 1px var(--accent-green);
        }}

        /* ---------- CHAT AREA (ChatGPT-style centered column) ---------- */
        .block-container {{
            max-width: 820px;
            padding-top: 2.5rem;
        }}
        [data-testid="stChatMessage"] {{
            background: transparent;
            border: none;
            padding: 18px 0;
            border-bottom: 1px solid var(--border);
        }}
        [data-testid="stChatMessage"]:last-child {{
            border-bottom: none;
        }}
        /* No avatars/icons — just the question and answer text */
        [data-testid="stChatMessageAvatarUser"],
        [data-testid="stChatMessageAvatarAssistant"] {{
            display: none !important;
        }}
        /* User messages flip to the right side so question/answer are visually separated.
           We mark each user message with our own <span class="chat-user-marker"> (rendered in
           Python below) and use :has() to target the parent — this is version-independent,
           unlike guessing Streamlit's internal emotion-cache class names or aria-labels. */
        [data-testid="stChatMessage"]:has(.chat-user-marker) {{
            flex-direction: row-reverse;
        }}
        [data-testid="stChatMessage"]:has(.chat-user-marker) [data-testid="stChatMessageContent"] {{
            text-align: right;
        }}
        [data-testid="stChatMessage"]:has(.chat-user-marker) [data-testid="stChatMessageContent"] p {{
            display: inline-block;
            background: var(--surface-2);
            padding: 10px 16px;
            border-radius: var(--radius-md);
            text-align: left;
        }}
        /* Chat input — unify every nested layer to the same background so seams disappear */
        /* The bottom bar Streamlit wraps around chat_input has its own background — neutralize it */
        [data-testid="stBottom"],
        [data-testid="stBottomBlockContainer"],
        .stBottom,
        div[class*="stBottom"] {{
            background: transparent !important;
        }}
        [data-testid="stChatInput"] {{
            background: var(--surface-2) !important;
            border: 1px solid var(--border) !important;
            border-radius: 28px !important;
            box-shadow: 0 4px 18px rgba(0,0,0,0.25);
            overflow: hidden;
        }}
        [data-testid="stChatInput"]:focus-within {{
            border-color: var(--accent-green) !important;
            box-shadow: 0 0 0 1px var(--accent-green);
        }}
        [data-testid="stChatInput"] > div,
        [data-testid="stChatInputContainer"] {{
            background: var(--surface-2) !important;
            border: none !important;
            box-shadow: none !important;
            padding: 10px 6px 10px 18px !important;
        }}
        [data-testid="stChatInput"] textarea {{
            background: var(--surface-2) !important;
            color: var(--text) !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }}
        [data-testid="stChatInput"] textarea::placeholder {{
            color: var(--text-faint) !important;
        }}
        [data-testid="stChatInputSubmitButton"],
        [data-testid="stChatInput"] button {{
            background: linear-gradient(135deg, var(--accent-yellow), var(--accent-orange)) !important;
            border-radius: 50% !important;
            border: none !important;
        }}
        [data-testid="stChatInputSubmitButton"] svg,
        [data-testid="stChatInput"] button svg {{
            fill: #FFFFFF !important;
        }}

        /* ---------- METRICS / DATAFRAME (admin) ---------- */
        [data-testid="stMetric"] {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 14px 16px;
        }}

        /* =========================================================
           LOGIN SCREEN — signature element (unchanged from before)
           ========================================================= */
        .login-wrap {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 6vh;
        }}
        .login-orb-bloom {{
            position: relative;
            width: 132px;
            height: 132px;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .login-orb-bloom::before {{
            content: "";
            position: absolute;
            width: 220px;
            height: 220px;
            background: radial-gradient(circle, rgba(225,36,40,0.4) 0%, rgba(225,36,40,0.0) 70%);
            border-radius: 50%;
            z-index: 0;
            animation: pulse-bloom 3.5s ease-in-out infinite;
        }}
        @keyframes pulse-bloom {{
            0%, 100% {{ opacity: 0.7; transform: scale(1); }}
            50% {{ opacity: 1; transform: scale(1.08); }}
        }}
        .login-orb-bloom img {{
            position: relative;
            z-index: 1;
            width: 112px;
            height: 112px;
            object-fit: contain;
            filter: drop-shadow(0 8px 24px rgba(225,36,40,0.4));
        }}
        .login-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: var(--text);
            margin: 4px 0 2px 0;
            text-align: center;
        }}
        .login-subtitle {{
            color: var(--text-dim);
            font-size: 14px;
            margin-bottom: 28px;
            text-align: center;
        }}

        /* =========================================================
           TOMATO ROLLING LOADER — shown while logging in, before the
           chat page is ready. Loops left-to-right indefinitely until
           this screen is replaced by the real chat page.
           ========================================================= */
        .tomato-roll-track {{
            position: relative;
            width: 100%;
            max-width: 360px;
            height: 90px;
            margin: 18px auto 4px auto;
            overflow: hidden;
        }}
        .tomato-roll-sprite {{
            position: absolute;
            top: 50%;
            left: -90px;
            width: 80px;
            height: 80px;
            margin-top: -40px;
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
            filter: drop-shadow(0 6px 14px rgba(225,36,40,0.4));
            animation:
                tomato-roll-move 2.6s linear infinite,
                tomato-roll-spin 0.5s steps(5) infinite;
        }}
        @keyframes tomato-roll-move {{
            0%   {{ left: -90px; }}
            100% {{ left: 100%; }}
        }}
        @keyframes tomato-roll-spin {{
            0%   {{ background-image: url('{TOMATO_FRAMES[0]}'); }}
            20%  {{ background-image: url('{TOMATO_FRAMES[1]}'); }}
            40%  {{ background-image: url('{TOMATO_FRAMES[2]}'); }}
            60%  {{ background-image: url('{TOMATO_FRAMES[3]}'); }}
            80%  {{ background-image: url('{TOMATO_FRAMES[4]}'); }}
            100% {{ background-image: url('{TOMATO_FRAMES[0]}'); }}
        }}

        /* Admin badge accent */
        .admin-pill {{
            display: inline-block;
            background: linear-gradient(135deg, var(--accent-yellow), var(--accent-orange));
            color: #FFFFFF;
            font-weight: 600;
            font-size: 12px;
            padding: 3px 10px;
            border-radius: 999px;
        }}

        /* Empty-chat hero (shown before the first message) */
        .empty-hero {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding-top: 14vh;
            text-align: center;
        }}
        .empty-hero img {{
            width: 64px;
            height: 64px;
            object-fit: contain;
            margin-bottom: 14px;
            filter: drop-shadow(0 6px 18px rgba(225,36,40,0.35));
        }}
        .empty-hero h2 {{
            font-size: 22px;
            margin: 0 0 4px 0;
        }}
        .empty-hero p {{
            color: var(--text-dim);
            font-size: 14px;
            margin: 0;
        }}
    </style>
    """
