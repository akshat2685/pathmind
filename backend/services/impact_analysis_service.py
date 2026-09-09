from typing import Dict, Any, List, Optional
from backend.core.adaptation_schemas import StateChangeEvent, ImpactAnalysis

class ImpactAnalysisService:
    def analyze_change(
        self,
        event: StateChangeEvent,
        current_roadmap: Optional[Dict[str, Any]] = None,
        completed_stage_ids: Optional[List[str]] = None
    ) -> ImpactAnalysis:
        completed = completed_stage_ids or []
        
        if event.change_type == "GOAL_CHANGE":
            prev_role = event.trigger_data.get("previous_role", "Applied ML Engineer")
            new_role = event.trigger_data.get("new_target_role", "Robotics Systems Engineer")
            
            # Check domain divergence
            is_major = ("Robotics" in new_role and "Web" in prev_role) or ("Product" in new_role and "Engineer" in prev_role)
            level = "CRITICAL_CHANGE" if is_major else "HIGH_IMPACT"
            
            return ImpactAnalysis(
                impact_level=level,
                what_changed=f"Target outcome transitioned from {prev_role} to {new_role}.",
                why="You selected a new career outcome requiring different advanced domain milestones and industry competencies.",
                affected_roadmap_stages=["phase_02_deep_learning", "phase_03_systems_engineering", "phase_04_capstone"],
                affected_career_requirements=[f"Core {new_role} Competencies", "Specialized System Artifacts"],
                invalidated_assumptions=[f"Previous specialization track for {prev_role}"],
                preserved_assets=["Stage 01: Python Foundations", "Stage 02: Mathematics & Linear Algebra", "Existing Code Repositories"],
                reconsidered_areas=[f"Domain-specific frameworks for {new_role}", "Target Project Portfolio"],
                requires_user_approval=True,
                approval_type="APPROVAL_REQUIRED",
                next_action_recommendation=f"Review the proposed {new_role} roadmap sequence and approve the transition to activate Version {((current_roadmap.get('version', 1) if current_roadmap else 1) + 1)}."
            )

        elif event.change_type == "CONSTRAINT_CHANGE":
            weekly_hours = event.trigger_data.get("weekly_hours", 10)
            prev_hours = event.trigger_data.get("previous_hours", 20)
            
            if weekly_hours < 8:
                level = "MODERATE_IMPACT"
                approval_type = "REVIEW"
            else:
                level = "LOW_IMPACT"
                approval_type = "AUTO_ADAPT"

            return ImpactAnalysis(
                impact_level=level,
                what_changed=f"Study pacing adjusted from {prev_hours}h/wk to {weekly_hours}h/wk.",
                why=f"Accommodating your new time commitment of {weekly_hours} hours per week.",
                affected_roadmap_stages=[],
                affected_career_requirements=[],
                invalidated_assumptions=[f"Original {prev_hours}h/week completion timeline"],
                preserved_assets=["All completed stages", "Current active stage progress", "All evidence submissions"],
                reconsidered_areas=["Estimated stage duration and weekly milestone checkpoints"],
                requires_user_approval=False,
                approval_type=approval_type,
                next_action_recommendation=f"Roadmap pacing recalibrated smoothly to {weekly_hours} hrs/week. Continue with your active stage mission."
            )

        elif event.change_type == "MASTERY_RISK":
            stage_id = event.trigger_data.get("stage_id", "current_stage")
            struggling = event.trigger_data.get("struggling_concepts", ["core concept"])
            
            return ImpactAnalysis(
                impact_level="MODERATE_IMPACT",
                what_changed=f"Reinforcement mission injected for Stage {stage_id}.",
                why=f"Detected friction across: {', '.join(struggling)}. Solidifying foundations before unlocking downstream dependencies.",
                affected_roadmap_stages=[stage_id],
                affected_career_requirements=[],
                invalidated_assumptions=["Immediate readiness for next advanced stage"],
                preserved_assets=["All prior completed stages", "Passing test evidence from earlier steps"],
                reconsidered_areas=[f"Foundational concepts in {stage_id}"],
                requires_user_approval=False,
                approval_type="AUTO_ADAPT",
                next_action_recommendation="Complete the targeted reinforcement exercise with guided code examples to lock in mastery."
            )

        elif event.change_type == "OPPORTUNITY_CHANGE":
            opp_title = event.trigger_data.get("opportunity_title", "Verified Program")
            req_milestones = event.trigger_data.get("required_milestones", ["Portfolio Project"])
            
            return ImpactAnalysis(
                impact_level="MODERATE_IMPACT",
                what_changed=f"Roadmap re-sequenced to prioritize {opp_title} prerequisites.",
                why=f"A verified opportunity matching your profile was detected. Building required projects early unlocks timely application.",
                affected_roadmap_stages=req_milestones,
                affected_career_requirements=["Verified Portfolio Evidence"],
                invalidated_assumptions=["Strict linear milestone ordering"],
                preserved_assets=["All completed foundations", "Core roadmap sequence"],
                reconsidered_areas=["Milestone project prioritization"],
                requires_user_approval=True,
                approval_type="REVIEW",
                next_action_recommendation=f"Review the suggested re-sequencing to build {req_milestones[0]} in parallel with current studies."
            )

        elif event.change_type == "EVIDENCE_CHANGE":
            skills = event.trigger_data.get("demonstrated_skills", [])
            return ImpactAnalysis(
                impact_level="LOW_IMPACT",
                what_changed=f"Verified competencies recorded: {', '.join(skills)}.",
                why="Evidence submission passed automated evaluation criteria.",
                affected_roadmap_stages=[],
                affected_career_requirements=skills,
                invalidated_assumptions=[],
                preserved_assets=["All existing profile skills", "Roadmap milestones"],
                reconsidered_areas=[],
                requires_user_approval=False,
                approval_type="AUTO_ADAPT",
                next_action_recommendation="Next milestone stage has been unlocked. Proceed to the next mission."
            )

        # Default fallback
        return ImpactAnalysis(
            impact_level="LOW_IMPACT",
            what_changed=event.description,
            why="Routine state update detected.",
            affected_roadmap_stages=[],
            affected_career_requirements=[],
            invalidated_assumptions=[],
            preserved_assets=["All completed progress"],
            reconsidered_areas=[],
            requires_user_approval=False,
            approval_type="AUTO_ADAPT",
            next_action_recommendation="Continue your active learning plan."
        )
