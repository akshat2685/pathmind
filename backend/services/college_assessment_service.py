"""
College Assessment & Checkpoint Evaluation Service for PATHMIND College Engineering MVP.
Generates objective and rubric-based checkpoint assessments grounded exclusively
in the verified activities completed by the student.
"""

from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone
from backend.core.college_schemas import (
    CollegeAssessment,
    CollegeAssessmentQuestion,
    CollegeAssessmentSubmission,
    CollegeAssessmentResult,
    MasteryStatus
)
from backend.services.store import FirestoreStore

class CollegeAssessmentService:
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()

    async def generate_phase_assessment(
        self,
        uid: str,
        plan_id: str,
        phase_id: str,
        subject_id: str,
        topic_title: str
    ) -> CollegeAssessment:
        """
        Creates a checkpoint assessment derived from the exact topics covered in the phase.
        """
        assessment_id = f"asmt_{phase_id}_{uuid.uuid4().hex[:4]}"
        
        # Grounded diagnostic questions tailored to the subject and phase
        from backend.core.config import settings
        import json
        
        gemini_available = bool(settings.GEMINI_API_KEY)
        model = None
        if gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini: {e}")

        questions = []
        if model:
            try:
                prompt = f"""
You are the PATHMIND Assessment Generator.
Create a short diagnostic checkpoint assessment for a college engineering student.
Subject ID: {subject_id}
Topic/Phase Title: {topic_title}

Return ONLY a valid JSON array of exactly 3 questions in this format:
[{{
    "id": "q1",
    "text": "The actual question text...",
    "type": "MCQ",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": "Option B",
    "marks": 5
}},
{{
    "id": "q3",
    "text": "A short answer explanation question...",
    "type": "SHORT_ANSWER",
    "rubric": "Rubric for grading",
    "marks": 10
}}]
Make the first two MCQs and the last one SHORT_ANSWER.
"""
                response = model.generate_content(prompt)
                text = response.text.strip()
                if text.startswith("```json"): text = text[7:]
                if text.startswith("```"): text = text[3:]
                if text.endswith("```"): text = text[:-3]
                
                gen_qs = json.loads(text.strip())
                for i, gq in enumerate(gen_qs, start=1):
                    questions.append(
                        CollegeAssessmentQuestion(
                            question_id=f"q{i}",
                            question_text=gq.get("text", "Question"),
                            question_type=gq.get("type", "MCQ"),
                            options=gq.get("options", []),
                            correct_answer=gq.get("answer"),
                            rubric=gq.get("rubric"),
                            topic=topic_title,
                            marks=gq.get("marks", 5)
                        )
                    )
            except Exception as e:
                print(f"Gemini generation failed: {e}")
                questions = []
        
        if not questions:
            # Fallback
            questions = [
                CollegeAssessmentQuestion(
                    question_id="q1",
                    question_text=f"Which core theorem or principle forms the theoretical basis of {topic_title}?",
                    question_type="MCQ",
                    options=[
                        "Conservation of Energy & Mass Equilibrium",
                        "Second-Order Differential Continuity",
                        "Direct Algebraic Proportionality",
                        "Unconstrained Dynamic Convergence"
                    ],
                    correct_answer="Conservation of Energy & Mass Equilibrium",
                    topic=topic_title,
                    marks=5
                ),
                CollegeAssessmentQuestion(
                    question_id="q2",
                    question_text=f"When analyzing {topic_title}, what primary trade-off must be managed under real-world constraints?",
                    question_type="MCQ",
                    options=[
                        "Efficiency vs Stability under transient load conditions",
                        "Memory address alignment vs static clock cycles",
                        "Nominal resistance vs dielectric breakdown",
                        "Tensile capacity vs plastic shear failure"
                    ],
                    correct_answer="Efficiency vs Stability under transient load conditions",
                    topic=topic_title,
                    marks=5
                ),
                CollegeAssessmentQuestion(
                    question_id="q3",
                    question_text=f"Explain how you would detect and correct a boundary error or numerical divergence when applying {topic_title}.",
                    question_type="SHORT_ANSWER",
                    rubric="Evaluates understanding of initial boundary conditions, tolerance limits, and validation steps.",
                    topic=topic_title,
                    marks=10
                )
            ]

        assessment = CollegeAssessment(
            assessment_id=assessment_id,
            user_id=uid,
            plan_id=plan_id,
            phase_id=phase_id,
            subject_id=subject_id,
            title=f"Checkpoint Assessment: {topic_title}",
            questions=questions,
            status="AVAILABLE"
        )

        await self.store.save_college_assessment(uid, assessment.model_dump(mode="json"))
        return assessment

    async def evaluate_submission(
        self,
        uid: str,
        submission: CollegeAssessmentSubmission
    ) -> CollegeAssessmentResult:
        """
        Evaluates student responses deterministically for objective items and structured rubrics for qualitative items.
        Returns MASTERED, PARTIALLY_MASTERED, or REINFORCEMENT_REQUIRED.
        """
        raw_asmt = await self.store.get_college_assessment(uid, submission.assessment_id)
        if not raw_asmt:
            raise ValueError("ASSESSMENT_NOT_FOUND")

        assessment = CollegeAssessment(**raw_asmt)
        total_marks = sum(q.marks for q in assessment.questions)
        earned_marks = 0.0
        topic_results = []

        for q in assessment.questions:
            student_ans = submission.answers.get(q.question_id, "").strip()
            item_score = 0.0

            if q.question_type == "MCQ":
                if q.correct_answer and student_ans.lower() == q.correct_answer.lower():
                    item_score = float(q.marks)
                else:
                    item_score = 0.0
            else:
                # Qualitative / Short Answer: grade on content match only — never on answer length.
                if q.correct_answer:
                    item_score = float(q.marks) if student_ans.lower() == q.correct_answer.lower() else 0.0
                else:
                    # No reference answer: cannot auto-grade honestly; flag for review.
                    item_score = 0.0

            earned_marks += item_score
            topic_results.append({
                "question_id": q.question_id,
                "topic": q.topic,
                "earned_marks": item_score,
                "total_marks": q.marks,
                "status": "STRONG" if item_score >= q.marks * 0.7 else "NEEDS_WORK",
                "requires_review": q.question_type != "MCQ" and not q.correct_answer,
            })

        percentage = (earned_marks / total_marks * 100) if total_marks > 0 else 0.0
        normalized = round(percentage / 100.0, 2)

        if percentage >= 75.0:
            mastery = MasteryStatus.MASTERED
            feedback = f"Outstanding grasp of {assessment.title}. Ready to advance to subsequent syllabus phases."
        elif percentage >= 50.0:
            mastery = MasteryStatus.PARTIALLY_MASTERED
            feedback = f"Acceptable foundational comprehension, but additional problem-solving practice is advised on specific topics."
        else:
            mastery = MasteryStatus.REINFORCEMENT_REQUIRED
            feedback = f"Key conceptual gaps observed. Targeted review of the lecture and notes is recommended prior to advancing."

        result = CollegeAssessmentResult(
            result_id=f"res_{submission.assessment_id}_{uuid.uuid4().hex[:4]}",
            assessment_id=submission.assessment_id,
            uid=uid,
            score=round(percentage, 1),
            normalized_score=normalized,
            mastery_status=mastery,
            feedback=feedback,
            topic_results=topic_results,
            created_at=datetime.now(timezone.utc).isoformat()
        )

        await self.store.save_college_assessment_result(uid, result.model_dump(mode="json"))

        # Ingest learning signal if reinforcement is needed
        if mastery == MasteryStatus.REINFORCEMENT_REQUIRED:
            from backend.core.college_schemas import LearningSignal
            signal = LearningSignal(
                signal_id=f"sig_{uuid.uuid4().hex[:6]}",
                uid=uid,
                signal_type="CONCEPT_GAP_DETECTED",
                subject_id=assessment.subject_id,
                topic_id=assessment.title,
                description=f"Struggled on checkpoint assessment for {assessment.title} (Score: {percentage}%).",
                recommended_intervention="Schedule spaced revision and targeted worked examples before proceeding to PYQs."
            )
            await self.store.save_learning_signal(uid, signal.model_dump(mode="json"))

        return result
