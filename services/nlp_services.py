from sentence_transformers import SentenceTransformer, util
import re

class VectorScorer:
    def __init__(self):
        print("Loading MiniLM Vector Model...")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        # KEEP YOUR SENTENCE ANCHORS (They worked better!)
        raw_anchors = {
            # URGENCY
            "emotional_urgency": "I am under intense pressure and feel like time is running out right now",
            "temporal_urgency": "This has a strict deadline and must be finished very soon",
            "non_urgency": "This can wait indefinitely and there is absolutely no time pressure",
            # INTEREST
            # Added "gaming" explicitly to the sentence to fix the mobile game interest
            "interest": "I am genuinely excited and actively want to do this hobby gaming or project right now",
            "boredom": "This feels painfully boring and I want to escape doing it",
            # FEAR
            "fear": "I am scared this will go badly and have serious negative consequences",
            "comfort": "This feels completely safe familiar and low risk",
            # TRIVIALITY (For the "Milk" dampener)
            "trivial": "This is a quick simple errand like buying groceries or a small chore",
        }

        self.anchors = {
            k: self.model.encode(v, convert_to_numpy=True, normalize_embeddings=True)
            for k, v in raw_anchors.items()
        }

    def _calculate_axis_score(self, task_vec, pos_anchor, neg_anchor):
        pos_sim = float(util.cos_sim(task_vec, self.anchors[pos_anchor]))
        neg_sim = float(util.cos_sim(task_vec, self.anchors[neg_anchor]))

        # Adjusted sensitivity to 0.3 for a smoother curve
        diff = pos_sim - neg_sim
        normalized = (diff / 0.3 + 1) / 2
        score = max(1, min(10, normalized * 10))
        return round(score, 1)

    def _apply_regex_modifiers(self, text, urgency, fear):
        """
        AI is bad at math (e.g. '1 hour').
        This hard-codes logic for specific trigger words.
        """
        text_lower = text.lower()

        # 1. TIME TRIGGERS (Boost Urgency)
        if any(
            x in text_lower
            for x in [
                "1 hour",
                "one hour",
                "today",
                "tonight",
                "asap",
                "now!",
                "urgent",
            ]
        ):
            urgency = max(urgency, 9.5)  # Force Immediate Priority
        elif any(x in text_lower for x in ["tomorrow", "24 hours"]):
            urgency = max(urgency, 8.5)

        # 2. TRIVIAL TRIGGERS (Kill Fear)
        # If it's just buying something simple, nuking the fear score.
        if any(
            x in text_lower
            for x in ["buy milk", "buy groceries", "clean room", "wash dishes"]
        ):
            fear = min(fear, 2.0)

        return urgency, fear

    def analyze_task(self, text):
        task_vec = self.model.encode(
            text, convert_to_numpy=True, normalize_embeddings=True
        )

        # --- 1. BASE AI SCORING ---
        emotional = self._calculate_axis_score(
            task_vec, "emotional_urgency", "non_urgency"
        )
        temporal = self._calculate_axis_score(
            task_vec, "temporal_urgency", "non_urgency"
        )

        # Weighted Average for Urgency
        urgency = max(temporal, emotional * 0.8 + temporal * 0.4)
        urgency = min(10, urgency)

        fear = self._calculate_axis_score(task_vec, "fear", "comfort")

        interest = self._calculate_axis_score(task_vec, "interest", "boredom")
        interest = max(1, interest - fear * 0.2)  # Reduced fear penalty slightly

        # --- 2. TRIVIALITY CHECK (The "Milk" Fix) ---
        triviality_score = float(util.cos_sim(task_vec, self.anchors["trivial"]))

        if triviality_score > 0.45:
            # If it's a small errand, drastically lower fear
            fear = max(1, fear - (triviality_score * 8))
            # Errands are usually not "Interest" driven, but they aren't "Boring" like taxes
            # So we leave interest alone or slightly boost it

        # --- 3. REGEX OVERRIDE (The "1 Hour" Fix) ---
        # This runs LAST to ensure human logic overrides AI guesses
        urgency, fear = self._apply_regex_modifiers(text, urgency, fear)

        return {
            "urgency": round(urgency, 1),
            "interest": round(interest, 1),
            "fear": round(fear, 1),
        }

# Singleton instance
nlp_engine = VectorScorer()
