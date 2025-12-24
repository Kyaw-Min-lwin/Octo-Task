from sentence_transformers import SentenceTransformer, util
import re


class VectorScorer:
    # --- TUNING CONFIGURATION (The "Psychology" Constants) ---

    # SENSITIVITY: Controls how responsive the 1-10 score is to vector similarity.
    # Lower (0.2) = Small differences create huge score jumps (Hyper-sensitive).
    # Higher (0.4) = Needs massive semantic difference to change score.
    SIMILARITY_SENSITIVITY = 0.3

    # TRIVIALITY: How we handle small errands (e.g., "Buy Milk").
    # If similarity to "trivial task" > 0.45, we nuke the fear score.
    TRIVIALITY_THRESHOLD = 0.45
    TRIVIALITY_FEAR_DAMPENER = 8.0  # Massive reduction (e.g., Fear 6 -> Fear 1)

    # URGENCY WEIGHTS: How we blend "Time Pressure" vs "Emotional Panic".
    # We weight emotional panic higher (0.8) because ADHD brains react to stress more than time.
    WEIGHT_EMOTIONAL_URGENCY = 0.8
    WEIGHT_TEMPORAL_URGENCY = 0.4

    # INTEREST DAMPENER: Fear kills dopamine.
    # We subtract 20% of the Fear score from Interest.
    INTEREST_FEAR_PENALTY = 0.2

    # HARDCODED OVERRIDES: Values for Regex hits.
    OVERRIDE_URGENCY_IMMEDIATE = 9.5  # "1 hour", "ASAP"
    OVERRIDE_URGENCY_SOON = 8.5  # "Tomorrow"
    OVERRIDE_FEAR_MIN = 2.0  # Cap fear for trivial tasks

    def __init__(self):
        print("Loading MiniLM Vector Model...")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        # ANCHORS (No changes here, kept for context)
        raw_anchors = {
            "emotional_urgency": "I am under intense pressure and feel like time is running out right now",
            "temporal_urgency": "This has a strict deadline and must be finished very soon",
            "non_urgency": "This can wait indefinitely and there is absolutely no time pressure",
            "interest": "I am genuinely excited and actively want to do this hobby gaming or project right now",
            "boredom": "This feels painfully boring and I want to escape doing it",
            "fear": "I am scared this will go badly and have serious negative consequences",
            "comfort": "This feels completely safe familiar and low risk",
            "trivial": "This is a quick simple errand like buying groceries or a small chore",
        }

        self.anchors = {
            k: self.model.encode(v, convert_to_numpy=True, normalize_embeddings=True)
            for k, v in raw_anchors.items()
        }

    def _calculate_axis_score(self, task_vec, pos_anchor, neg_anchor):
        pos_sim = float(util.cos_sim(task_vec, self.anchors[pos_anchor]))
        neg_sim = float(util.cos_sim(task_vec, self.anchors[neg_anchor]))

        # Use the class constant for sensitivity
        diff = pos_sim - neg_sim
        normalized = (diff / self.SIMILARITY_SENSITIVITY + 1) / 2
        score = max(1, min(10, normalized * 10))
        return round(score, 1)

    def _apply_regex_modifiers(self, text, urgency, fear):
        text_lower = text.lower()

        # 1. TIME TRIGGERS (Boost Urgency)
        # Fixed logic: Check Regex separately from string list
        has_time_pattern = re.search(r"\b\d+\s*(hour|hr|hrs|min|mins)\b", text_lower)
        has_urgent_keyword = any(
            kw in text_lower for kw in ["today", "tonight", "asap", "now!", "urgent"]
        )

        if has_time_pattern or has_urgent_keyword:
            urgency = max(urgency, self.OVERRIDE_URGENCY_IMMEDIATE)

        elif any(x in text_lower for x in ["tomorrow", "24 hours"]):
            urgency = max(urgency, self.OVERRIDE_URGENCY_SOON)

        # 2. TRIVIAL TRIGGERS (Kill Fear)
        if any(
            x in text_lower
            for x in [
                "buy milk",
                "buy groceries",
                "clean room",
                "wash dishes",
                "laundry",
            ]
        ):
            fear = min(fear, self.OVERRIDE_FEAR_MIN)

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

        # Weighted Average
        urgency = max(
            temporal,
            emotional * self.WEIGHT_EMOTIONAL_URGENCY
            + temporal * self.WEIGHT_TEMPORAL_URGENCY,
        )
        urgency = min(10, urgency)

        fear = self._calculate_axis_score(task_vec, "fear", "comfort")
        interest = self._calculate_axis_score(task_vec, "interest", "boredom")

        # Apply Interest Penalty
        interest = max(1, interest - fear * self.INTEREST_FEAR_PENALTY)

        # --- 2. TRIVIALITY CHECK ---
        triviality_score = float(util.cos_sim(task_vec, self.anchors["trivial"]))

        if triviality_score > self.TRIVIALITY_THRESHOLD:
            # Drastically lower fear for simple tasks
            fear = max(1, fear - (triviality_score * self.TRIVIALITY_FEAR_DAMPENER))

        # --- 3. REGEX OVERRIDE ---
        urgency, fear = self._apply_regex_modifiers(text, urgency, fear)

        return {
            "urgency": round(urgency, 1),
            "interest": round(interest, 1),
            "fear": round(fear, 1),
            "triviality": round(triviality_score, 2),
        }


# Singleton instance
nlp_engine = VectorScorer()
