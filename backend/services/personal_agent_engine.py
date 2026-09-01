from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.core.roadmap_schemas import (
    LearningEvent,
    PersonalAgentModel,
    LongitudinalMemory,
    EvaluationResult
)
from backend.services.store import FirestoreStore

class PersonalAgentEngine:
    def __init__(self):
        self.store = FirestoreStore()

    async def get_or_create_agent_model(self, person_id: str) -> PersonalAgentModel:
        model_dict = await self.store.get_personal_agent_model(person_id)
        if model_dict:
            return PersonalAgentModel(**model_dict)
        
        # Initialize baseline PersonalAgentModel
        new_model = PersonalAgentModel(
            person_id=person_id,
            version=1,
            learning_preferences={
                "preferred_format": "project-based",
                "weekly_hours": 10,
                "explanation_style": "practical-code-first"
            },
            strengths=["Logical Reasoning", "Python Scripting"],
            weaknesses=["Multivariate Calculus", "Memory Management"],
            recurring_misconceptions=[],
            successful_interventions=["Interactive Call Stack Visualizations", "Step-by-step Unit Tests"],
            unsuccessful_interventions=["Passive Video Lectures > 45 mins"],
            pace="NORMAL",
            skill_evidence={"Python Fundamentals": "Verified via Class 12 CS & Hackathon Classifier"},
            longitudinal_memories=[
                LongitudinalMemory(
                    person_id=person_id,
                    concept="Recursion & Call Stack Frames",
                    context="Mastered recursive base cases through visual frame tracing during foundational coding.",
                    stage_learned="Stage 1: Python Foundations",
                    confidence="HIGH"
                )
            ],
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        await self.store.save_personal_agent_model(person_id, new_model.model_dump(mode="json"))
        return new_model

    async def process_learning_event_and_evolve(
        self,
        person_id: str,
        stage_id: str,
        evaluation: EvaluationResult,
        concept: str
    ) -> PersonalAgentModel:
        """
        The Personal Agent Learning Loop:
        1. Emits a structured LearningEvent based on evaluation.
        2. Updates PersonalAgentModel (strengths, recurring misconceptions, pacing, longitudinal memory).
        3. Persists versioned state.
        """
        current_model = await self.get_or_create_agent_model(person_id)
        
        # 1. Create LearningEvent
        event_type = "MASTERY_DEMONSTRATED" if evaluation.status == "PASS" else "RECURRING_MISCONCEPTION"
        learning_signal = (
            f"Demonstrated solid mastery in {concept} with high accuracy and practical transfer."
            if evaluation.status == "PASS" else
            f"Encountered difficulty with {concept}. Requires targeted reinforcement before proceeding."
        )

        event = LearningEvent(
            person_id=person_id,
            stage_id=stage_id,
            topic=concept,
            event_type=event_type,
            observation=evaluation.feedback,
            intervention=evaluation.recommended_next_action,
            result="Satisfied stage threshold" if evaluation.status == "PASS" else "Triggered reinforcement mission",
            learning_signal=learning_signal,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        await self.store.save_learning_event(person_id, event.model_dump(mode="json"))

        # 2. Update Model State
        updated_model = current_model.model_copy(deep=True)
        if evaluation.status == "PASS":
            if concept not in updated_model.strengths:
                updated_model.strengths.append(concept)
            updated_model.skill_evidence[concept] = f"Demonstrated in {stage_id} with score {evaluation.mastery_dimensions.accuracy}%"
            # Add longitudinal memory
            updated_model.longitudinal_memories.append(
                LongitudinalMemory(
                    person_id=person_id,
                    concept=concept,
                    context=f"Successfully built and validated practical artifact for {concept}.",
                    stage_learned=stage_id,
                    confidence="HIGH"
                )
            )
        else:
            if concept not in updated_model.weaknesses:
                updated_model.weaknesses.append(concept)
            if concept not in updated_model.recurring_misconceptions:
                updated_model.recurring_misconceptions.append(concept)
            updated_model.pace = "REINFORCED"

        updated_model.updated_at = datetime.now(timezone.utc).isoformat()
        version = await self.store.save_personal_agent_model(person_id, updated_model.model_dump(mode="json"))
        updated_model.version = version
        return updated_model

    async def retrieve_cross_stage_memory(
        self,
        person_id: str,
        current_concept: str
    ) -> Optional[Dict[str, Any]]:
        """
        Cross-stage knowledge transfer: Searches personal learning history for related concepts.
        Strictly isolated to person_id.
        """
        model = await self.get_or_create_agent_model(person_id)
        current_concept_lower = current_concept.lower()

        # Check for related foundational concepts
        for mem in model.longitudinal_memories:
            mem_concept_lower = mem.concept.lower()
            if (
                ("tree" in current_concept_lower and "recursion" in mem_concept_lower) or
                ("deep learning" in current_concept_lower and "linear algebra" in mem_concept_lower) or
                ("mlops" in current_concept_lower and "docker" in mem_concept_lower) or
                (current_concept_lower in mem_concept_lower)
            ):
                return {
                    "related_concept": mem.concept,
                    "context": mem.context,
                    "stage_learned": mem.stage_learned,
                    "connection_statement": f"This builds upon the '{mem.concept}' foundations you developed in {mem.stage_learned}."
                }
        return None
