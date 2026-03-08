# CometAdvisor

CometAdvisor is an intelligent academic planning assistant for UTD students. It provides personalized course recommendations and semester schedules by integrating hardcoded UTD degree flowcharts, unofficial transcript uploads, and real-time course data from Nebula Labs APIs. The system uses Gemini 2.5 Flash for natural language explanations and ElevenLabs TTS with Web Speech API for voice interaction.

The backend recommendation engine scores courses based on student interests, professor quality, and availability, then generates friendly explanations for each recommendation. Students can upload their transcripts, specify career interests, and receive tailored course schedules that fit their goals and constraints.

## How We Built It

- **Frontend:** Next.js (React) + TailwindCSS
- **Backend:** FastAPI (Python)
- **Voice:** ElevenLabs TTS + Web Speech API
- **Data:** Hardcoded UTD flowcharts + Nebula Labs APIs
- **Visualization:** React Flow / D3.js
- **Deployment:** Vercel (frontend) + Railway/Render (backend)

<img width="881" height="779" alt="SCR-20260308-klje" src="https://github.com/user-attachments/assets/915bb475-687b-4cbc-9f59-4659d95a9ef8" />

## Challenges We Ran Into

Our biggest challenge was making the voice conversation feel natural. The Web Speech API has built-in timeouts and would cut off mid-sentence or activate while Cali was still speaking,  we had to build a custom silence detection system and strict turn-based guards to prevent the mic from bleeding into Cali's responses. We also ran into merge conflicts coordinating between three separate branches, frontend, backend, and transcript parser all being built simultaneously under time pressure. Finally, bridging Cali's natural language responses to structured course data was tricky — we had to build a regex parser that extracts course codes from conversational text and maps them to the right semester columns in real time.


## Accomplishments We're Proud Of

We're proud that we shipped a fully functional voice-first AI advisor in under 48 hours. The integration between ElevenLabs, Gemini, and the Nebula Labs API creates something that genuinely feels like talking to a knowledgeable advisor, not a chatbot. We're also proud of the real-time course plan that builds as Cali speaks watching courses animate into the board during a live conversation is a genuinely magical demo moment. And the UI built to match the Nebula Labs design language, looks like a real product, not a hackathon project.


## What We Learned

We learned that voice UX is significantly harder than text UX, the margin for error is much smaller and latency issues that would be invisible in a text app become obvious and jarring in a voice conversation. We also learned the value of locking down a shared architecture early, our biggest time losses came from parallel frontend and backend development that diverged before we had agreed on API contracts. On the technical side, we got deep experience with the Web Speech API, ElevenLabs streaming, and Next.js API routes proxying to a Python FastAPI backend.


## What's Next for Comet Advisor

The immediate next step is expanding our degree flowchart database to cover every UTD major and minor, right now we have CS and SE hardcoded, but the architecture supports any major. We also want to integrate the Nebula Labs professor rating data so Cali can recommend not just the right courses but the right sections with the best professors. Longer term, we want to add a scheduling layer that cross-references the Nebula Rooms API so Cali can recommend courses that actually fit together in a student's weekly schedule. The dream is a single conversation that takes a student from confused freshman to fully planned four-year roadmap in under five minutes.

### Scoring Formula

```
score = 0.5 * student_priority + 0.3 * professor_rating + 0.2 * availability_score
```

- **student_priority**: 1.0 (exact interest match), 0.5 (partial match), 0.0 (no match)
- **professor_rating**: Combined score from avg_grade and grade_consistency
- **availability_score**: Based on number of open sections



## License

MIT
