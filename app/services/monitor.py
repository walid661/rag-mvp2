import time
import json
import logging
from typing import List, Dict, Optional

class RAGMonitor:
    """Simple monitor to log retrieval and generation metrics."""

    def __init__(self, logger_name: str = "rag_monitor"):
        self.logger = logging.getLogger(logger_name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.start_time: Optional[float] = None

    def start_timer(self) -> None:
        self.start_time = time.time()

    def measure_latency(self) -> float:
        if self.start_time is None:
            return 0.0
        return (time.time() - self.start_time) * 1000

    def log_query(self, query: str, retrieved_docs: List[Dict], user_feedback: Optional[int] = None) -> None:
        log_entry = {
            "timestamp": time.time(),
            "query": query,
            "num_results": len(retrieved_docs),
            "top_score": retrieved_docs[0]['score'] if retrieved_docs else 0,
            "latency_ms": self.measure_latency(),
            "user_feedback": user_feedback,
        }
        self.logger.info(json.dumps(log_entry))

    def update_metrics(self, log_entry: Dict) -> None:
        # Placeholder for metrics update logic; integrate with your monitoring system.
        pass