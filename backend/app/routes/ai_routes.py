from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Set

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/ai", tags=["AI Features"])


# ══════════════════════════════════════════════════════════════════════════════
#  Skill-matching utilities
# ══════════════════════════════════════════════════════════════════════════════
def _parse_skills(skills_str: str | None) -> Set[str]:
    """Return a lower-cased set of skills from a comma-separated string."""
    if not skills_str:
        return set()
    return {s.strip().lower() for s in skills_str.split(",") if s.strip()}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    """Jaccard similarity: |A ∩ B| / |A ∪ B|. Returns 0 if both empty."""
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union)


def _build_reason(user_skills: Set[str], alumni: models.User, score: float) -> str:
    """Build a human-readable recommendation reason string."""
    common = user_skills & _parse_skills(alumni.skills)
    if common:
        sample = sorted(common)[:3]
        return f"Shares skills: {', '.join(sample)}"
    if alumni.college:
        return f"Alumni from {alumni.college}"
    if alumni.bio:
        return "Active mentor with a complete profile"
    return "Recommended from your college network"


# ══════════════════════════════════════════════════════════════════════════════
#  GET /ai/recommendations
# ══════════════════════════════════════════════════════════════════════════════
@router.get(
    "/recommendations",
    response_model=List[schemas.RecommendationOut],
    summary="AI-powered alumni recommendations",
)
def get_recommendations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Return up to **10** recommended alumni ranked by relevance.

    **Scoring logic:**
    1. Jaccard similarity on skill sets (0 – 1)
    2. +0.25 bonus if the alumni is from the same college
    3. +0.05 bonus if the alumni has a non-empty bio (active profile)

    Results are sorted by score descending.
    """
    user_skills = _parse_skills(current_user.skills)

    alumni_list = (
        db.query(models.User)
        .filter(
            models.User.role == "alumni",
            models.User.id   != current_user.id,
        )
        .all()
    )

    scored: List[schemas.RecommendationOut] = []

    for alumni in alumni_list:
        alumni_skills = _parse_skills(alumni.skills)
        score = _jaccard(user_skills, alumni_skills)

        # Same-college bonus
        if (
            current_user.college
            and alumni.college
            and current_user.college.strip().lower() == alumni.college.strip().lower()
        ):
            score += 0.25

        # Active-profile bonus
        if alumni.bio and len(alumni.bio.strip()) > 10:
            score += 0.05

        scored.append(
            schemas.RecommendationOut(
                user=schemas.UserPublic.model_validate(alumni),
                score=round(score, 4),
                reason=_build_reason(user_skills, alumni, score),
            )
        )

    # Sort best first, cap at 10
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:10]


# ══════════════════════════════════════════════════════════════════════════════
#  Rule-based chatbot knowledge base
# ══════════════════════════════════════════════════════════════════════════════
_RESPONSES: dict[str, str] = {
    "resume": (
        "📄 **Resume Tips**\n\n"
        "• Keep it to **1 page** (students) or **2 pages** (experienced alumni).\n"
        "• Lead every bullet with a strong action verb: *Developed, Led, Optimised, Reduced*.\n"
        "• Quantify everything — e.g. 'Reduced API latency by 40%' beats 'improved performance'.\n"
        "• Tailor your resume for each application; mirror keywords from the job description.\n"
        "• Place your most impressive project / achievement first in each section.\n"
        "• Proofread — a single typo can sink an otherwise great resume."
    ),
    "interview": (
        "🎤 **Interview Preparation**\n\n"
        "• Research the company's mission, recent news, and products *before* the call.\n"
        "• Use the **STAR** method (Situation → Task → Action → Result) for behavioural questions.\n"
        "• Prepare 3–5 thoughtful questions to ask the interviewer.\n"
        "• Do a mock interview — record yourself, watch it back.\n"
        "• For technical rounds: explain your thinking aloud as you code.\n"
        "• Send a thank-you email within 24 hours."
    ),
    "networking": (
        "🤝 **Networking Strategies**\n\n"
        "• Quality > quantity. 10 meaningful connections beat 500 cold follows.\n"
        "• Personalise every connection request — mention *why* you want to connect.\n"
        "• Give before you ask: share useful articles, congratulate achievements.\n"
        "• Follow up within 48 hours of meeting someone.\n"
        "• Alumni networks (like this platform!) are your most warm leads — use them.\n"
        "• Attend virtual/local meetups in your target industry."
    ),
    "career": (
        "🚀 **Career Guidance**\n\n"
        "• Define **short-term** (1 yr) and **long-term** (5 yr) goals first.\n"
        "• Build a T-shaped skill set: broad understanding + deep expertise in 1–2 areas.\n"
        "• Seek feedback actively and act on it visibly.\n"
        "• Side projects and open-source contributions speak louder than certifications.\n"
        "• Don't job-hop aimlessly — each move should be deliberate and upward.\n"
        "• A good mentor can compress years of learning into months."
    ),
    "internship": (
        "💼 **Internship Hunting**\n\n"
        "• Start applying **3–4 months** before your intended start date.\n"
        "• Use: LinkedIn, Internshala, Naukri, Indeed, AngelList, company career pages.\n"
        "• Cold-email employees at target companies — most hiring managers respect the initiative.\n"
        "• Build a mini-portfolio (GitHub, personal site, Behance) before applying.\n"
        "• Use this platform to find alumni at companies you're targeting — they can refer you!\n"
        "• Treat every interview as a learning experience, even if you don't land the role."
    ),
    "skills": (
        "🛠️ **Skill Development**\n\n"
        "• Identify in-demand skills via job boards — look at 20+ JDs for your target role.\n"
        "• Free resources: Coursera, edX, freeCodeCamp, CS50, YouTube, official docs.\n"
        "• **Learning by building** beats passive watching. Start a project on Day 1.\n"
        "• Contribute to open source — it builds skill, portfolio, and network simultaneously.\n"
        "• Soft skills (communication, ownership, curiosity) often determine who gets promoted.\n"
        "• Review and update your skills section on your profile regularly."
    ),
    "mentor": (
        "🎓 **Finding & Working With a Mentor**\n\n"
        "• Use the **Mentorship** tab on this platform to send requests to alumni.\n"
        "• Be specific in your ask: 'I want to break into ML at a product company' > 'career advice'.\n"
        "• Respect their time — prepare focused questions, keep sessions to 30 min.\n"
        "• Take notes, share progress updates, close the loop.\n"
        "• Gratitude matters — a short thank-you message goes a long way.\n"
        "• Aim for a long-term relationship, not a one-time favour."
    ),
    "salary": (
        "💰 **Salary & Negotiation**\n\n"
        "• Research benchmarks: Glassdoor, Levels.fyi, LinkedIn Salary, AmbitionBox.\n"
        "• Never give the first number — let the company anchor first.\n"
        "• Negotiate the total package: base, bonus, stock, PTO, remote flexibility.\n"
        "• Always negotiate — at least 60% of offers have room to move.\n"
        "• Be enthusiastic but calm. 'I'm very excited about this role. Based on my research…'\n"
        "• Get the final offer in writing before resigning from your current job."
    ),
    "higher studies": (
        "🏫 **Higher Studies / Masters / PhD**\n\n"
        "• Identify programs aligned with your research interests or career goals.\n"
        "• GRE/GMAT, GPA, SOP, LORs, and research experience are the key pillars.\n"
        "• Start SOP drafts 3 months before deadlines — get multiple rounds of feedback.\n"
        "• Reach out to professors whose work aligns with yours before applying.\n"
        "• Funding: look for RA/TA positions, fellowships, and scholarships.\n"
        "• Connect with alumni from your target universities on this platform."
    ),
    "hi":    "👋 Hello! I'm your AI career assistant. Ask me about **resume, interview, networking, career, internship, skills, mentor, salary**, or **higher studies**!",
    "hello": "👋 Hello! I'm your AI career assistant. Ask me about **resume, interview, networking, career, internship, skills, mentor, salary**, or **higher studies**!",
    "hey":   "👋 Hey there! How can I help your career journey today?",
    "help": (
        "🤖 **I can help you with:**\n\n"
        "• `resume` — Writing and formatting tips\n"
        "• `interview` — Preparation strategies\n"
        "• `networking` — Building meaningful connections\n"
        "• `career` — Goal-setting and growth\n"
        "• `internship` — Finding and landing one\n"
        "• `skills` — What to learn and how\n"
        "• `mentor` — Finding and working with mentors\n"
        "• `salary` — Negotiation tactics\n"
        "• `higher studies` — Masters / PhD guidance\n\n"
        "Just type any topic!"
    ),
}

_DEFAULT_REPLY = (
    "🤔 I'm not sure about that specific topic. Try asking about:\n\n"
    "**resume · interview · networking · career · internship · skills · mentor · salary · higher studies**\n\n"
    "Or browse the Alumni directory and send a Mentorship request directly!"
)

# Keywords that should also attach alumni suggestions
_SUGGESTION_KEYWORDS = {
    "mentor", "alumni", "connect", "suggest", "recommend",
    "who should", "find someone", "speak to",
}


# ══════════════════════════════════════════════════════════════════════════════
#  POST /ai/chatbot
# ══════════════════════════════════════════════════════════════════════════════
@router.post(
    "/chatbot",
    response_model=schemas.ChatbotResponse,
    summary="AI career guidance chatbot",
)
def chatbot(
    payload: schemas.ChatbotRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Rule-based career chatbot.

    Matches the user's message against a keyword dictionary and returns
    domain-specific career advice. When mentorship/alumni keywords are
    detected, up to 3 skill-matched alumni suggestions are also returned.

    **Supported topics:** resume, interview, networking, career, internship,
    skills, mentor, salary, higher studies (and more).
    """
    msg_lower = payload.message.lower()

    # ── Match reply ───────────────────────────────────────────────────────────
    reply = _DEFAULT_REPLY
    for keyword, response in _RESPONSES.items():
        if keyword in msg_lower:
            reply = response
            break

    # ── Attach alumni suggestions if relevant ─────────────────────────────────
    suggestions: List[schemas.UserPublic] = []
    if any(kw in msg_lower for kw in _SUGGESTION_KEYWORDS):
        user_skills = _parse_skills(current_user.skills)
        alumni_list = (
            db.query(models.User)
            .filter(models.User.role == "alumni")
            .limit(30)
            .all()
        )

        scored = sorted(
            alumni_list,
            key=lambda a: _jaccard(user_skills, _parse_skills(a.skills)),
            reverse=True,
        )
        suggestions = [
            schemas.UserPublic.model_validate(a) for a in scored[:3]
        ]

    return schemas.ChatbotResponse(reply=reply, suggestions=suggestions)
