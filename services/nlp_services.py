from sentence_transformers import SentenceTransformer, util
import numpy as np


class VectorScorer:
    def __init__(self):
        print("Loading MiniLM Vector Model...")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        # FIX 1: CONCEPT CLUSTERS
        # Instead of sentences, we use dense lists of strongly correlated keywords.
        # This reduces "noise" and gives the model clearer targets.
        raw_anchors = {
            # URGENCY
            "emotional_urgency": "I am under intense pressure and feel like time is running out right now",
            "temporal_urgency": "This has a strict deadline and must be finished very soon",
            "non_urgency": "This can wait indefinitely and there is absolutely no time pressure",
            # INTEREST
            "interest": "I am genuinely excited and actively want to do this right now",
            "boredom": "This feels painfully boring and I want to escape doing it",
            # FEAR
            "fear": "I am scared this will go badly and have serious negative consequences",
            "comfort": "This feels completely safe familiar and low risk",
            "trivial": "This is a tiny simple errand that requires almost no effort",
        }

        self.anchors = {
            k: self.model.encode(v, convert_to_numpy=True, normalize_embeddings=True)
            for k, v in raw_anchors.items()
        }

    def _calculate_axis_score(self, task_vec, pos_anchor, neg_anchor):
        pos_sim = float(util.cos_sim(task_vec, self.anchors[pos_anchor]))
        neg_sim = float(util.cos_sim(task_vec, self.anchors[neg_anchor]))

        # Sensitivity tuning:
        # A lower divisor (0.25) makes the model MORE sensitive to small differences.
        diff = pos_sim - neg_sim
        normalized = (diff / 0.25 + 1) / 2
        score = max(1, min(10, normalized * 10))

        return round(score, 1)

    def analyze_task(self, text):
        task_vec = self.model.encode(
            text, convert_to_numpy=True, normalize_embeddings=True
        )

        # 1. Calculate Base Scores
        emotional = self._calculate_axis_score(
            task_vec, "emotional_urgency", "non_urgency"
        )

        temporal = self._calculate_axis_score(
            task_vec, "temporal_urgency", "non_urgency"
        )

        urgency = max(temporal, emotional * 0.8 + temporal * 0.4)
        urgency = min(10, urgency)

        fear = self._calculate_axis_score(task_vec, "fear", "comfort")

        interest = self._calculate_axis_score(task_vec, "interest", "boredom")
        interest = max(1, interest - fear * 0.3)

        # 2. Calculate Context Modifiers
        # Check if the task is "trivial" (like buying milk)
        # We compare "trivial" vs "urgency_high" to see if it's just a small errand
        triviality_score = float(util.cos_sim(task_vec, self.anchors["trivial"]))

        # FIX 2: APPLY TRIVIALITY DAMPENER
        # If a task is very trivial (score > 0.4), it shouldn't be scary.
        if triviality_score > 0.4:
            # Massive reduction to Fear for simple errands
            fear = max(1, fear - (triviality_score * 8))
            # Slight reduction to Urgency (unless it really is due now)
            urgency = max(1, urgency - (triviality_score * 2))

        return {
            "urgency": round(urgency, 1),
            "interest": round(interest, 1),
            "fear": round(fear, 1),
        }


# Singleton instance
nlp_engine = VectorScorer()
