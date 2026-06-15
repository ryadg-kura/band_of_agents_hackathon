import streamlit as st
import time
from dotenv import load_dotenv

load_dotenv()

from band.client import BandClient

st.set_page_config(page_title="Quorum — Compliance Dashboard", page_icon="🏦", layout="wide")

band = BandClient()


def get_pending_cases() -> list[dict]:
    room = band.join_room("escalations")
    messages = room.get_messages()
    return [m for m in messages if m.get("type") != "human_decision"]


def get_case_thread(case_id: str) -> list[dict]:
    room = band.join_room(f"case-{case_id}")
    return room.get_messages()


def post_human_decision(case_id: str, decision: str, note: str) -> None:
    band.join_room(f"case-{case_id}").post_message({
        "type": "human_decision", "decision": decision, "note": note, "officer": "Compliance Officer"
    })
    band.join_room("escalations").post_message({
        "type": "human_decision", "case_id": case_id, "decision": decision,
    })


def risk_badge(level: str) -> str:
    return {"HIGH": "🔴", "WARN": "🟡", "CLEAR": "🟢"}.get(level, "⚪")


def page_pending_cases():
    st.title("🏦 Quorum — Compliance Dashboard")
    cases = [c for c in get_pending_cases() if "decision" not in c]
    st.metric("Cases en attente", len(cases))
    st.divider()

    if not cases:
        st.success("Aucun case en attente. ✅")
        time.sleep(5)
        st.rerun()
        return

    for case in cases:
        case_id = case.get("case_id", "N/A")
        verdict = case.get("verdict", "N/A")
        badge = "🔴" if verdict == "ESCALATE_SAR" else "🟠"
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 4, 1])
            col1.write(f"**{badge} {case_id}**")
            col1.caption(verdict)
            col2.write(case.get("summary", "")[:120])
            if col3.button("Review →", key=f"btn_{case_id}"):
                st.session_state["selected_case"] = case_id
                st.rerun()

    st.caption("Actualisation toutes les 5 secondes")
    time.sleep(5)
    st.rerun()


def page_case_detail(case_id: str):
    st.title(f"🔍 Case {case_id}")
    if st.button("← Retour"):
        del st.session_state["selected_case"]
        st.rerun()

    thread = get_case_thread(case_id)
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Votes des agents")
        for a in [m for m in thread if m.get("type") == "analysis"]:
            st.write(f"{risk_badge(a.get('risk_level', ''))} **{a['agent']}** — {a['risk_level']} ({a.get('confidence', 0):.0%})")
            st.caption(a.get("reasoning", ""))

        verdicts = [m for m in thread if m.get("type") == "final_verdict"]
        if verdicts:
            v = verdicts[-1]
            st.divider()
            st.subheader("Recommandation Synthesis")
            st.error(f"⚠️ {v.get('vote', '')}")
            st.write(v.get("reasoning", ""))

    with col_right:
        st.subheader(f"Fil Band — room case-{case_id}")
        for msg in thread:
            agent = msg.get("agent", msg.get("type", "system"))
            text = msg.get("reasoning") or msg.get("question") or msg.get("summary") or str(msg)
            with st.chat_message("assistant"):
                st.caption(f"**{agent}**")
                st.write(str(text)[:300])

    st.divider()
    already_decided = any(m.get("type") == "human_decision" for m in thread)

    if already_decided:
        d = next(m for m in thread if m.get("type") == "human_decision")
        st.success(f"✅ Décision : {d['decision']} — {d.get('note', '')}")
    else:
        st.subheader("Votre décision")
        note = st.text_area("Note (obligatoire si Override)")
        col1, col2, col3 = st.columns(3)
        if col1.button("✅ CONFIRM SAR", type="primary"):
            post_human_decision(case_id, "CONFIRM_SAR", note)
            st.rerun()
        if col2.button("❌ OVERRIDE — Clear"):
            if not note:
                st.error("Note obligatoire.")
            else:
                post_human_decision(case_id, "OVERRIDE_CLEAR", note)
                st.rerun()
        if col3.button("💬 Ask More"):
            post_human_decision(case_id, "REQUEST_MORE_INFO", note)
            st.rerun()


def page_audit_log():
    st.title("📁 Audit Log")
    decisions = [m for m in band.join_room("escalations").get_messages() if m.get("type") == "human_decision"]
    if not decisions:
        st.info("Aucune décision enregistrée.")
        return
    for d in decisions:
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 3, 2])
            col1.write(f"**{d.get('case_id', 'N/A')}**")
            col2.write(d.get("decision", ""))
            col2.caption(d.get("note", ""))
            if col3.button("Voir détail", key=f"audit_{d.get('case_id')}"):
                st.session_state["selected_case"] = d.get("case_id")
                st.rerun()


page = st.sidebar.radio("Navigation", ["📋 Pending Cases", "📁 Audit Log"])

if "selected_case" in st.session_state:
    page_case_detail(st.session_state["selected_case"])
elif page == "📋 Pending Cases":
    page_pending_cases()
else:
    page_audit_log()
